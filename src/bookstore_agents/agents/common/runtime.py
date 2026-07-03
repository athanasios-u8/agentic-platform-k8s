import re
from collections.abc import AsyncIterator
from datetime import date
from typing import Any

from bookstore_agents.agents.common.a2a_client import A2AClient
from bookstore_agents.agents.common.agent_cards import AgentSpec
from bookstore_agents.agents.common.mcp_client import MCPClient
from bookstore_agents.agents.common.ollama_runtime import OllamaTextRuntime
from bookstore_agents.agents.common.openai_runtime import OpenAITextRuntime
from bookstore_agents.common.approvals import WRITE_TOOLS, create_approval
from bookstore_agents.common.observability import (
    mark_span_error,
    set_span_attributes,
    set_span_output,
    start_span,
    tool_attributes,
    workflow_attributes,
)
from bookstore_agents.mcp_servers.catalog.repository import CatalogRepository
from bookstore_agents.mcp_servers.customer.repository import CustomerRepository
from bookstore_agents.mcp_servers.store_operations.repository import StoreOperationsRepository


class AgentRuntime:
    def __init__(self, spec: AgentSpec):
        self.spec = spec
        self.mcp_client = MCPClient(spec.mcp_servers)
        self.a2a_client = A2AClient()
        self.openai = OpenAITextRuntime()
        self.text_runtime = (
            OllamaTextRuntime() if spec.model_provider == "ollama" else self.openai
        )
        self.catalog_repo = CatalogRepository()
        self.customer_repo = CustomerRepository()
        self.store_repo = StoreOperationsRepository()

    async def run(
        self, message: str, context: dict[str, Any] | None = None
    ) -> AsyncIterator[dict[str, Any]]:
        context = context or {}
        session_id = context.get("session_id")
        attributes = workflow_attributes(
            agent=self.spec.slug,
            event="agent.run",
            input_value=message,
            session_id=str(session_id) if session_id else None,
            extra={
                "bookstore.agent.name": self.spec.name,
                "bookstore.agent.role": self.spec.role,
            },
        )
        with start_span("agent.run", attributes) as span:
            yield {"type": "run_started", "agent": self.spec.name, "message": message}
            tools = await self.mcp_client.list_tools()
            yield {"type": "tool_discovery", "agent": self.spec.name, "tools": tools}

            async for event in self._run_for_spec(message, context):
                if event.get("type") == "final":
                    set_span_output(span, event.get("answer") or event, trace_output=True)
                yield event

    async def _run_for_spec(
        self,
        message: str,
        context: dict[str, Any],
    ) -> AsyncIterator[dict[str, Any]]:
        if self.spec.slug == "catalog-specialist":
            async for event in self._run_catalog_specialist(message, context):
                yield event
        elif self.spec.slug == "reservation-specialist":
            async for event in self._run_reservation_specialist(message, context):
                yield event
        elif self.spec.slug == "message-drafter":
            async for event in self._run_message_drafter(message, context):
                yield event
        elif self.spec.slug == "customer-concierge":
            async for event in self._run_customer_concierge(message, context):
                yield event
        elif self.spec.slug == "store-manager":
            async for event in self._run_store_manager(message, context):
                yield event
        elif self.spec.slug == "release-scout":
            async for event in self._run_release_scout(message, context):
                yield event
        else:
            yield {"type": "final", "agent": self.spec.name, "answer": "Unknown agent."}

    async def _call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: dict[str, Any],
        requires_approval: bool = False,
    ) -> dict[str, Any]:
        attributes = tool_attributes(
            server=server_name,
            tool=tool_name,
            arguments=arguments,
            extra={"bookstore.agent": self.spec.slug},
        )
        with start_span("tool.call", attributes) as span:
            if requires_approval or tool_name in WRITE_TOOLS:
                approval = create_approval(
                    agent_name=self.spec.name,
                    tool_name=tool_name,
                    arguments=arguments,
                    summary=self._approval_summary(tool_name, arguments),
                    run_state={"agent": self.spec.slug, "server": server_name},
                )
                set_span_attributes(
                    span,
                    {
                        "bookstore.approval.required": True,
                        "bookstore.approval.id": approval["approval_id"],
                        "bookstore.approval.summary": approval["summary"],
                    },
                )
                with start_span(
                    "approval.requested",
                    {
                        "bookstore.agent": self.spec.slug,
                        "bookstore.tool.name": tool_name,
                        "bookstore.approval.id": approval["approval_id"],
                        "bookstore.approval.summary": approval["summary"],
                    },
                ) as approval_span:
                    set_span_output(approval_span, approval)
                return {"approval_required": True, "approval": approval}
            try:
                result = await self.mcp_client.call_tool(server_name, tool_name, arguments)
                set_span_output(span, result)
                return {"result": result}
            except Exception as exc:
                mark_span_error(span, exc)
                fallback_result = self._direct_tool_call(tool_name, arguments)
                set_span_attributes(span, {"bookstore.tool.fallback": True})
                set_span_output(span, fallback_result)
                return {"result": fallback_result}

    def _direct_tool_call(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        if tool_name == "search_books":
            return self.catalog_repo.search_books(**arguments)
        if tool_name == "get_book_details":
            return self.catalog_repo.get_book_details(**arguments)
        if tool_name == "recommend_books":
            return self.catalog_repo.recommend_books(**arguments)
        if tool_name == "get_customer":
            return self.customer_repo.get_customer(**arguments)
        if tool_name == "lookup_loyalty_status":
            return self.customer_repo.lookup_loyalty_status(**arguments)
        if tool_name == "check_stock":
            return self.store_repo.check_stock(**arguments)
        if tool_name == "list_low_stock":
            return self.store_repo.list_low_stock(**arguments)
        if tool_name == "list_today_pickups":
            return self.store_repo.list_today_pickups()
        if tool_name == "daily_sales_summary":
            return self.store_repo.daily_sales_summary(**arguments)
        if tool_name == "top_selling_books":
            return self.store_repo.top_selling_books(**arguments)
        if tool_name == "search_upcoming_book_releases":
            from bookstore_agents.mcp_servers.upcoming_releases.repository import (
                UpcomingReleasesRepository,
            )

            return UpcomingReleasesRepository().search_upcoming_book_releases(**arguments)
        raise ValueError(f"No direct fallback for {tool_name}.")

    def _approval_summary(self, tool_name: str, arguments: dict[str, Any]) -> str:
        if tool_name == "create_reservation":
            return (
                f"Create reservation for customer {arguments.get('customer_id')} "
                f"and book {arguments.get('book_id')}."
            )
        if tool_name == "cancel_reservation":
            return f"Cancel reservation {arguments.get('reservation_id')}."
        if tool_name == "mark_reservation_picked_up":
            return f"Mark reservation {arguments.get('reservation_id')} as picked up."
        if tool_name == "adjust_inventory":
            return (
                f"Adjust inventory for book {arguments.get('book_id')} by "
                f"{arguments.get('quantity_delta')}."
            )
        if tool_name == "update_customer_preferences":
            return f"Update preferences for customer {arguments.get('customer_id')}."
        return f"Approve tool call {tool_name}."

    async def _run_catalog_specialist(
        self,
        message: str,
        context: dict[str, Any],
    ) -> AsyncIterator[dict[str, Any]]:
        arguments = {
            "prompt": message,
            "genre": context.get("genre") or self._extract_genre(message),
            "max_price": context.get("max_price") or self._extract_max_price(message),
            "audience": context.get("audience") or self._extract_audience(message),
            "limit": int(context.get("limit", 5)),
        }
        yield {"type": "tool_call_requested", "tool": "recommend_books", "arguments": arguments}
        tool_result = await self._call_tool("catalog", "recommend_books", arguments)
        books = tool_result["result"]
        yield {"type": "tool_call_completed", "tool": "recommend_books", "result": books}
        fallback = self._format_book_recommendations(books)
        answer = await self.text_runtime.polish(
            self.spec.name, self.spec.instructions, message, {"books": books}, fallback
        )
        yield {"type": "final", "agent": self.spec.name, "answer": answer, "data": {"books": books}}

    async def _run_reservation_specialist(
        self,
        message: str,
        context: dict[str, Any],
    ) -> AsyncIterator[dict[str, Any]]:
        lowered = message.lower()
        if self._is_cancellation_request(lowered):
            async for event in self._prepare_reservation_status_change(
                message,
                context,
                "cancel_reservation",
            ):
                yield event
            return

        if self._is_pickup_completion_request(lowered):
            async for event in self._prepare_reservation_status_change(
                message,
                context,
                "mark_reservation_picked_up",
            ):
                yield event
            return

        if "reserve" in lowered or context.get("book_id"):
            book_id = context.get("book_id") or self._extract_int(message, "book")
            customer_id = context.get("customer_id") or self._extract_int(message, "customer") or 1
            if not book_id:
                candidates = self.catalog_repo.recommend_books(message, limit=1)
                if candidates:
                    book_id = candidates[0]["id"]
            stock_args = {"book_id": book_id}
            yield {"type": "tool_call_requested", "tool": "check_stock", "arguments": stock_args}
            stock = await self._call_tool("store_operations", "check_stock", stock_args)
            yield {"type": "tool_call_completed", "tool": "check_stock", "result": stock["result"]}
            arguments = {
                "book_id": book_id,
                "customer_id": customer_id,
                "pickup_date": context.get("pickup_date") or date.today().isoformat(),
            }
            yield {
                "type": "tool_call_requested",
                "tool": "create_reservation",
                "arguments": arguments,
            }
            result = await self._call_tool(
                "store_operations", "create_reservation", arguments, True
            )
            yield {"type": "approval_required", **result["approval"]}
            answer = f"{result['approval']['summary']} Waiting for human approval."
            yield {"type": "final", "agent": self.spec.name, "answer": answer, "data": result}
            return

        pickups = await self._call_tool("store_operations", "list_today_pickups", {})
        yield {
            "type": "tool_call_completed",
            "tool": "list_today_pickups",
            "result": pickups["result"],
        }
        answer = f"There are {len(pickups['result'])} pickups scheduled today."
        yield {"type": "final", "agent": self.spec.name, "answer": answer, "data": pickups}

    async def _run_message_drafter(
        self,
        message: str,
        context: dict[str, Any],
    ) -> AsyncIterator[dict[str, Any]]:
        answer = self._draft_message(message, context)
        polished = await self.text_runtime.polish(
            self.spec.name, self.spec.instructions, message, context, answer
        )
        yield {
            "type": "final",
            "agent": self.spec.name,
            "answer": polished,
            "data": {"context": context},
        }

    async def _run_customer_concierge(
        self,
        message: str,
        context: dict[str, Any],
    ) -> AsyncIterator[dict[str, Any]]:
        catalog_result = await self._call_subagent("catalog_specialist", message, context)
        yield catalog_result
        reservation_result = None
        if "reserve" in message.lower():
            reservation_context = dict(context)
            books = catalog_result.get("data", {}).get("books") or []
            if books and "book_id" not in reservation_context:
                reservation_context["book_id"] = books[0].get("id")
            reservation_result = await self._call_subagent(
                "reservation_specialist",
                message,
                reservation_context,
            )
            yield reservation_result
        draft_context = {
            "catalog": catalog_result,
            "reservation": reservation_result,
        }
        draft = await self._call_subagent(
            "message_drafter", "Draft a customer response.", draft_context
        )
        yield draft
        answer = (
            draft.get("answer") or catalog_result.get("answer") or "I found some options for you."
        )
        yield {"type": "final", "agent": self.spec.name, "answer": answer, "data": draft_context}

    async def _run_store_manager(
        self,
        message: str,
        context: dict[str, Any],
    ) -> AsyncIterator[dict[str, Any]]:
        lowered = message.lower()
        if self._is_cancellation_request(lowered):
            async for event in self._prepare_reservation_status_change(
                message,
                context,
                "cancel_reservation",
            ):
                yield event
            return

        if self._is_pickup_completion_request(lowered):
            async for event in self._prepare_reservation_status_change(
                message,
                context,
                "mark_reservation_picked_up",
            ):
                yield event
            return

        if self._is_pickup_list_request(lowered):
            pickups = await self._call_tool("store_operations", "list_today_pickups", {})
            yield {
                "type": "tool_call_completed",
                "tool": "list_today_pickups",
                "result": pickups["result"],
            }
            fallback = self._format_pickup_list(pickups["result"])
            answer = await self.text_runtime.polish(
                self.spec.name,
                self.spec.instructions,
                message,
                {"pickups": pickups["result"]},
                fallback,
            )
            yield {
                "type": "final",
                "agent": self.spec.name,
                "answer": answer,
                "data": pickups,
            }
            return

        summary = await self._call_tool("store_operations", "daily_sales_summary", {})
        low_stock = await self._call_tool("store_operations", "list_low_stock", {"threshold": 2})
        pickups = await self._call_tool("store_operations", "list_today_pickups", {})
        top_books = await self._call_tool(
            "store_operations", "top_selling_books", {"days": 7, "limit": 5}
        )
        data = {
            "sales_summary": summary["result"],
            "low_stock": low_stock["result"],
            "pickups": pickups["result"],
            "top_books": top_books["result"],
        }
        yield {
            "type": "tool_call_completed",
            "tool": "daily_sales_summary",
            "result": summary["result"],
        }
        yield {
            "type": "tool_call_completed",
            "tool": "list_low_stock",
            "result": low_stock["result"],
        }
        yield {
            "type": "tool_call_completed",
            "tool": "list_today_pickups",
            "result": pickups["result"],
        }
        yield {
            "type": "tool_call_completed",
            "tool": "top_selling_books",
            "result": top_books["result"],
        }
        fallback = (
            f"Opening brief: {summary['result'].get('units_sold', 0)} units sold today, "
            f"{len(pickups['result'])} pickups scheduled, and "
            f"{len(low_stock['result'])} low-stock titles."
        )
        answer = await self.text_runtime.polish(
            self.spec.name, self.spec.instructions, message, data, fallback
        )
        yield {"type": "final", "agent": self.spec.name, "answer": answer, "data": data}

    async def _run_release_scout(
        self,
        message: str,
        context: dict[str, Any],
    ) -> AsyncIterator[dict[str, Any]]:
        arguments = {
            "query": context.get("query") or message,
            "author": context.get("author") or self._extract_author(message),
            "theme": context.get("theme") or self._extract_release_theme(message),
            "limit": int(context.get("limit", 5)),
            "months_ahead": int(context.get("months_ahead", 12)),
        }
        yield {
            "type": "tool_call_requested",
            "tool": "search_upcoming_book_releases",
            "arguments": arguments,
        }
        tool_result = await self._call_tool(
            "upcoming_releases",
            "search_upcoming_book_releases",
            arguments,
        )
        release_search = tool_result["result"]
        yield {
            "type": "tool_call_completed",
            "tool": "search_upcoming_book_releases",
            "result": release_search,
        }
        fallback = self._format_release_search(release_search)
        answer = await self.text_runtime.polish(
            self.spec.name,
            self.spec.instructions,
            message,
            {"release_search": release_search},
            fallback,
        )
        yield {
            "type": "final",
            "agent": self.spec.name,
            "answer": answer,
            "data": {"release_search": release_search},
        }

    async def _call_subagent(
        self,
        subagent_key: str,
        message: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        url = self.spec.subagents.get(subagent_key)
        if not url:
            return {
                "type": "subagent_error",
                "subagent": subagent_key,
                "message": "No URL configured.",
            }
        attributes = workflow_attributes(
            agent=self.spec.slug,
            event="subagent.call",
            input_value=message,
            extra={
                "bookstore.subagent": subagent_key,
                "bookstore.subagent.url": url,
            },
        )
        with start_span("subagent.call", attributes) as span:
            try:
                result = await self.a2a_client.final_message(url, message, context)
                response = {
                    "type": "subagent_response_received",
                    "subagent": subagent_key,
                    "answer": result.get("answer"),
                    "data": result.get("data", {}),
                }
                set_span_output(span, response)
                return response
            except Exception as exc:
                mark_span_error(span, exc)
                response = {
                    "type": "subagent_response_received",
                    "subagent": subagent_key,
                    "answer": f"Subagent {subagent_key} was unavailable: {exc}",
                    "data": {},
                }
                set_span_output(span, response)
                return response

    async def _prepare_reservation_status_change(
        self,
        message: str,
        context: dict[str, Any],
        tool_name: str,
    ) -> AsyncIterator[dict[str, Any]]:
        arguments, resolved_pickup = await self._reservation_arguments(message, context)
        if not arguments.get("reservation_id"):
            yield {
                "type": "tool_call_completed",
                "tool": "list_today_pickups",
                "result": resolved_pickup or [],
            }
            yield {
                "type": "final",
                "agent": self.spec.name,
                "answer": (
                    "I could not identify the matching active pickup. Please include the "
                    "reservation id, or both the customer name and book title."
                ),
                "data": {"resolution_failed": True},
            }
            return

        yield {
            "type": "tool_call_requested",
            "tool": tool_name,
            "arguments": arguments,
        }
        result = await self._call_tool("store_operations", tool_name, arguments, True)
        yield {"type": "approval_required", **result["approval"]}
        action = "cancellation" if tool_name == "cancel_reservation" else "pickup completion"
        matched = ""
        if resolved_pickup:
            matched = (
                f" Matched {resolved_pickup['customer_name']} - "
                f"{resolved_pickup['title']}."
            )
        answer = (
            f"I prepared the {action} for reservation {arguments['reservation_id']}."
            f"{matched} Waiting for human approval before updating the database."
        )
        yield {"type": "final", "agent": self.spec.name, "answer": answer, "data": result}

    async def _reservation_arguments(
        self,
        message: str,
        context: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any] | list[dict[str, Any]] | None]:
        reservation_id = context.get("reservation_id") or self._extract_reservation_id(message)
        if reservation_id:
            return {"reservation_id": reservation_id}, None

        pickups = await self._call_tool("store_operations", "list_today_pickups", {})
        rows = pickups["result"]
        matched = self._best_pickup_match(message, rows)
        if matched:
            return {"reservation_id": matched["reservation_id"]}, matched
        return {"reservation_id": None}, rows

    def _best_pickup_match(
        self,
        message: str,
        pickups: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        message_text = self._normalize_match_text(message)
        best_score = 0
        best: dict[str, Any] | None = None
        for pickup in pickups:
            score = self._pickup_match_score(message_text, pickup)
            if score > best_score:
                best_score = score
                best = pickup
        return best if best_score >= 5 else None

    def _pickup_match_score(self, message_text: str, pickup: dict[str, Any]) -> int:
        score = 0
        customer = self._normalize_match_text(str(pickup.get("customer_name", "")))
        title = self._normalize_match_text(str(pickup.get("title", "")))
        if customer and customer in message_text:
            score += 5
        if title and title in message_text:
            score += 5
        for token in customer.split():
            if len(token) > 2 and token in message_text:
                score += 1
        for token in title.split():
            if len(token) > 2 and token in message_text:
                score += 1
        return score

    def _normalize_match_text(self, text: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()

    def _is_cancellation_request(self, lowered: str) -> bool:
        cancel_phrases = (
            "cancel",
            "cancelled",
            "canceled",
            "not going to pick",
            "not coming to pick",
            "will not pick",
            "won't pick",
            "wont pick",
            "no longer pick",
        )
        return any(phrase in lowered for phrase in cancel_phrases)

    def _is_pickup_completion_request(self, lowered: str) -> bool:
        completion_phrases = (
            "picked up",
            "has picked",
            "came to pick",
            "came by",
            "collected",
            "completed pickup",
            "mark as picked",
        )
        return any(phrase in lowered for phrase in completion_phrases)

    def _is_pickup_list_request(self, lowered: str) -> bool:
        pickup_terms = ("pickup", "pick-up", "pickups", "pick-ups")
        list_terms = ("list", "today", "queue", "what", "show", "who")
        return any(term in lowered for term in pickup_terms) and any(
            term in lowered for term in list_terms
        )

    def _format_book_recommendations(self, books: list[dict[str, Any]]) -> str:
        if not books:
            return "I could not find matching books."
        lines = ["Here are good matches:"]
        for book in books:
            authors = ", ".join(book.get("authors", [])) or "unknown author"
            available = book.get("available_quantity", "unknown")
            lines.append(
                f"- {book['title']} by {authors}: ${book['price']:.2f}, "
                f"{book['genre']}, {available} available."
            )
        return "\n".join(lines)

    def _format_pickup_list(self, pickups: list[dict[str, Any]]) -> str:
        if not pickups:
            return "There are no active pickups scheduled for today."
        lines = [f"There are {len(pickups)} active pickups scheduled today:"]
        for pickup in pickups:
            lines.append(
                f"- {pickup['customer_name']} - {pickup['title']} "
                f"({pickup['reservation_id']})"
            )
        return "\n".join(lines)

    def _format_release_search(self, release_search: dict[str, Any]) -> str:
        status = release_search.get("status")
        if status == "missing_api_key":
            return release_search.get("message") or "Set TAVILY_API_KEY to search releases."
        if status == "search_error":
            return (
                "I could not complete the upcoming release search. "
                f"{release_search.get('error', '')}".strip()
            )
        results = release_search.get("results") or []
        if not results:
            return "I could not find upcoming release leads for that request."
        lines = ["Upcoming release leads from web sources:"]
        for result in results:
            title = result.get("title") or "Untitled source"
            url = result.get("source_url") or ""
            date_hint = result.get("possible_release_date") or result.get("published_date")
            suffix = f" ({date_hint})" if date_hint else ""
            lines.append(f"- {title}{suffix}: {url}")
        if release_search.get("answer"):
            lines.append("")
            lines.append(str(release_search["answer"]))
        return "\n".join(lines)

    def _draft_message(self, message: str, context: dict[str, Any]) -> str:
        reservation = context.get("reservation") or {}
        catalog = context.get("catalog") or {}
        if reservation.get("data", {}).get("approval_required"):
            approval = reservation["data"]["approval"]
            return (
                "I found a good option and prepared the reservation. "
                f"{approval['summary']} Please approve it to complete the pickup reservation."
            )
        if catalog.get("answer"):
            return catalog["answer"]
        return "Here is a concise update based on the supplied context."

    def _extract_genre(self, message: str) -> str | None:
        lowered = message.lower()
        genres = {
            "mystery": "Mystery",
            "science fiction": "Science Fiction",
            "sci-fi": "Science Fiction",
            "fantasy": "Fantasy",
            "romance": "Romance",
            "thriller": "Thriller",
            "nonfiction": "Nonfiction",
            "children": "Children",
        }
        for needle, genre in genres.items():
            if needle in lowered:
                return genre
        return None

    def _extract_audience(self, message: str) -> str | None:
        lowered = message.lower()
        if "dad" in lowered or "father" in lowered or "adult" in lowered:
            return "adult"
        if "young adult" in lowered or "teen" in lowered:
            return "young adult"
        if "kid" in lowered or "child" in lowered:
            return "middle grade"
        return None

    def _extract_author(self, message: str) -> str | None:
        match = re.search(r"\bby\s+([A-Z][A-Za-z'.-]+(?:\s+[A-Z][A-Za-z'.-]+){0,3})", message)
        if match:
            return match.group(1).strip()
        match = re.search(
            r"\bauthor\s+([A-Z][A-Za-z'.-]+(?:\s+[A-Z][A-Za-z'.-]+){0,3})",
            message,
        )
        return match.group(1).strip() if match else None

    def _extract_release_theme(self, message: str) -> str | None:
        lowered = message.lower()
        patterns = (
            r"upcoming\s+(.+?)\s+releases",
            r"new\s+(.+?)\s+books",
            r"(.+?)\s+book\s+releases",
        )
        for pattern in patterns:
            match = re.search(pattern, lowered)
            if match:
                theme = match.group(1).strip(" .?!")
                if theme and theme not in {"book", "books"}:
                    return theme
        return self._extract_genre(message)

    def _extract_max_price(self, message: str) -> float | None:
        match = re.search(r"(?:under|below|less than)\s*\$?(\d+(?:\.\d+)?)", message.lower())
        return float(match.group(1)) if match else None

    def _extract_reservation_id(self, message: str) -> str | None:
        match = re.search(r"(res-[a-zA-Z0-9-]+)", message)
        return match.group(1) if match else None

    def _extract_int(self, message: str, label: str) -> int | None:
        match = re.search(rf"{label}[_\s-]*id?\s*(?:=|:)?\s*(\d+)", message.lower())
        if match:
            return int(match.group(1))
        match = re.search(rf"{label}\s+(\d+)", message.lower())
        return int(match.group(1)) if match else None


def execute_approved_tool(approval: dict[str, Any]) -> dict[str, Any]:
    tool_name = approval["tool_name"]
    arguments = dict(approval["arguments"])
    arguments["approval_id"] = approval["approval_id"]
    store = StoreOperationsRepository()
    customer = CustomerRepository()
    if tool_name == "create_reservation":
        return store.create_reservation(**arguments)
    if tool_name == "cancel_reservation":
        return store.cancel_reservation(**arguments)
    if tool_name == "mark_reservation_picked_up":
        return store.mark_reservation_picked_up(**arguments)
    if tool_name == "adjust_inventory":
        return store.adjust_inventory(**arguments)
    if tool_name == "update_customer_preferences":
        return customer.update_customer_preferences(**arguments)
    raise ValueError(f"Cannot execute unknown approval tool {tool_name}.")
