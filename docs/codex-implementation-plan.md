# Codex Implementation Plan

## Goal

Implement the Local Bookstore Assistant as a modular, Dockerized Python project. The system should include independently callable agents, independently runnable MCP servers, PostgreSQL-backed sample data, fake data loading scripts, and clear command documentation for local development.

## Current Implementation Note

This document began as the implementation plan. The current repository extends
that plan with six independently callable agents, four MCP servers, a Tavily-
backed Upcoming Releases MCP server, a Release Scout subagent, and KAOS
manifests in `k8s/kaos` for the full Kubernetes deployment.

The active runtime is a custom Python agent runtime with A2A-style endpoints,
FastMCP clients, OpenAI Responses final-answer polishing for the existing
bookstore agents, and Ollama `/api/chat` final-answer polishing for Release
Scout. The `openai-agents` dependency remains available, but the current code
does not use the OpenAI Agents SDK as the primary runtime.

## Technical Direction

Use:

- Python for all application code
- FastMCP for MCP servers and tools
- A2A for agent-to-agent communication
- A2A JSON-RPC streaming for agent-to-agent calls
- OpenAI Python SDK for OpenAI-backed final answer polishing
- Ollama native `/api/chat` for Release Scout final answer polishing
- ChatKit custom server integration for the browser-facing frontend
- PostgreSQL for sample bookstore data
- `uv` for virtual environments, dependency management, locking, and command execution
- Docker and Docker Compose for local multi-service execution
- A separately dockerized frontend component
- Empty `__init__.py` files
- `.env.example` for required environment variables
- Health and readiness endpoints for all HTTP services

Documentation references that informed the original plan:

- FastMCP supports defining tools with `@mcp.tool` and running servers over HTTP with `mcp.run(transport="http", host="0.0.0.0", port=...)`.
- FastMCP clients can connect to HTTP MCP servers, list available tools, and call tools with `Client(...).list_tools()` and `Client(...).call_tool(...)`.
- A2A Python SDK supports agent servers, agent cards, and clients that can connect to another agent URL and send messages. The current code exposes A2A-style endpoints through shared FastAPI helpers.
- OpenAI Agents SDK was evaluated for orchestration, streamed runs, approval interruptions, and MCP connectivity. The dependency remains available, but the current implementation uses the custom Python runtime described above.
- ChatKit supports custom server integrations that can run on our own infrastructure and connect to a server-owned agent backend.
- ChatKit is the selected frontend path for this project.
- `uv` supports project management with `uv add`, `uv lock`, `uv sync`, and `uv run`; Docker builds can install locked dependencies with `uv sync --locked` or `uv sync --frozen`.

## Target Repository Structure

```text
.
+-- README.md
+-- COMMANDS.md
+-- Dockerfile
+-- docker-compose.yml
+-- .env.example
+-- pyproject.toml
+-- uv.lock
+-- docs/
|   +-- bookstore-agent-scenario.md
|   +-- codex-implementation-plan.md
|   +-- frontend-options.md
+-- scripts/
|   +-- init_db.py
|   +-- seed_fake_data.py
|   +-- reset_demo_data.py
+-- src/
|   +-- bookstore_agents/
|       +-- __init__.py
|       +-- common/
|       |   +-- __init__.py
|       |   +-- approvals.py
|       |   +-- config.py
|       |   +-- database.py
|       |   +-- logging.py
|       |   +-- schemas.py
|       +-- frontend_gateway/
|       |   +-- __init__.py
|       |   +-- approvals.py
|       |   +-- chatkit_server.py
|       |   +-- server.py
|       |   +-- streaming.py
|       +-- mcp_servers/
|       |   +-- __init__.py
|       |   +-- catalog/
|       |   |   +-- __init__.py
|       |   |   +-- server.py
|       |   |   +-- repository.py
|       |   |   +-- tools.py
|       |   +-- customer/
|       |   |   +-- __init__.py
|       |   |   +-- server.py
|       |   |   +-- repository.py
|       |   |   +-- tools.py
|       |   +-- store_operations/
|       |   |   +-- __init__.py
|       |   |   +-- server.py
|       |   |   +-- repository.py
|       |   |   +-- tools.py
|       |   +-- upcoming_releases/
|       |       +-- __init__.py
|       |       +-- server.py
|       |       +-- repository.py
|       |       +-- tools.py
|       +-- agents/
|           +-- __init__.py
|           +-- common/
|           |   +-- __init__.py
|           |   +-- a2a_client.py
|           |   +-- agent_cards.py
|           |   +-- mcp_client.py
|           |   +-- ollama_runtime.py
|           |   +-- openai_runtime.py
|           |   +-- prompts.py
|           |   +-- runtime.py
|           |   +-- server.py
|           |   +-- streaming.py
|           +-- customer_concierge/
|           |   +-- __init__.py
|           |   +-- agent.py
|           |   +-- executor.py
|           |   +-- server.py
|           +-- store_manager/
|           |   +-- __init__.py
|           |   +-- agent.py
|           |   +-- executor.py
|           |   +-- server.py
|           +-- catalog_specialist/
|           |   +-- __init__.py
|           |   +-- agent.py
|           |   +-- executor.py
|           |   +-- server.py
|           +-- reservation_specialist/
|           |   +-- __init__.py
|           |   +-- agent.py
|           |   +-- executor.py
|           |   +-- server.py
|           +-- message_drafter/
|           |   +-- __init__.py
|           |   +-- agent.py
|           |   +-- executor.py
|           |   +-- server.py
|           +-- release_scout/
|               +-- __init__.py
|               +-- agent.py
|               +-- executor.py
|               +-- server.py
+-- frontend/
|   +-- README.md
|   +-- Dockerfile
|   +-- index.html
|   +-- src/
|       +-- app.js
|       +-- styles.css
+-- tests/
    +-- __init__.py
    +-- test_catalog_tools.py
    +-- test_customer_tools.py
    +-- test_store_operations_tools.py
    +-- test_agent_routing.py
    +-- test_agent_server_kaos_compat.py
    +-- test_openai_runtime.py
    +-- test_release_scout.py
    +-- test_upcoming_releases_tools.py
```

All `__init__.py` files should be intentionally empty.

## Phase 1: Project Foundation

1. Initialize the Python project with `uv`.
2. Add runtime dependencies:
   - FastMCP
   - A2A Python SDK
   - OpenAI Python SDK
   - OpenAI Agents SDK
   - PostgreSQL database client or ORM
   - Pydantic settings support
   - HTTP client library
   - FastAPI and an ASGI server for service endpoints
   - ChatKit Python SDK if the ChatKit frontend path is selected
3. Add development dependencies:
   - pytest
   - ruff
   - mypy or pyright if desired
4. Create `.env.example`.
5. Create `README.md` with project overview.
6. Create `COMMANDS.md` for repeatable local commands.
7. Add base Docker and Docker Compose files.

`.env.example` should include placeholders for:

```text
OPENAI_API_KEY=
OPENAI_MODEL=
OPENAI_TRACING_ENABLED=

OLLAMA_MODEL=
OLLAMA_BASE_URL=
OLLAMA_API_KEY=
OLLAMA_HOST_PORT=
OLLAMA_IMAGE_TAG=

TAVILY_API_KEY=
TAVILY_SEARCH_URL=

POSTGRES_PORT=
POSTGRES_DB=
POSTGRES_USER=
POSTGRES_PASSWORD=
DATABASE_URL=

CATALOG_MCP_PORT=
CATALOG_MCP_HOST_PORT=
CATALOG_MCP_URL=
CUSTOMER_MCP_PORT=
CUSTOMER_MCP_HOST_PORT=
CUSTOMER_MCP_URL=
STORE_OPERATIONS_MCP_PORT=
STORE_OPERATIONS_MCP_HOST_PORT=
STORE_OPERATIONS_MCP_URL=
UPCOMING_RELEASES_MCP_PORT=
UPCOMING_RELEASES_MCP_HOST_PORT=
UPCOMING_RELEASES_MCP_URL=

CUSTOMER_CONCIERGE_AGENT_PORT=
CUSTOMER_CONCIERGE_AGENT_HOST_PORT=
CUSTOMER_CONCIERGE_AGENT_URL=
STORE_MANAGER_AGENT_PORT=
STORE_MANAGER_AGENT_HOST_PORT=
STORE_MANAGER_AGENT_URL=
CATALOG_SPECIALIST_AGENT_PORT=
CATALOG_SPECIALIST_AGENT_HOST_PORT=
CATALOG_SPECIALIST_AGENT_URL=
RESERVATION_SPECIALIST_AGENT_PORT=
RESERVATION_SPECIALIST_AGENT_HOST_PORT=
RESERVATION_SPECIALIST_AGENT_URL=
MESSAGE_DRAFTER_AGENT_PORT=
MESSAGE_DRAFTER_AGENT_HOST_PORT=
MESSAGE_DRAFTER_AGENT_URL=
RELEASE_SCOUT_AGENT_PORT=
RELEASE_SCOUT_AGENT_HOST_PORT=
RELEASE_SCOUT_AGENT_URL=

FRONTEND_GATEWAY_PORT=
FRONTEND_GATEWAY_HOST_PORT=
CHATKIT_API_PATH=
FRONTEND_HOST_PORT=
FRONTEND_GATEWAY_PUBLIC_URL=

APPROVAL_REQUIRED_FOR_WRITES=
APPROVAL_STATE_STORE=

LOG_LEVEL=

BACKEND_IMAGE_PREFIX=
FRONTEND_IMAGE_PREFIX=
IMAGE_TAG=
```

## Phase 2: Database And Fake Data

Create PostgreSQL tables for:

- `books`
- `authors`
- `book_authors`
- `inventory`
- `customers`
- `customer_preferences`
- `reservations`
- `sales`

Create scripts:

- `scripts/init_db.py`: creates schema and indexes.
- `scripts/seed_fake_data.py`: inserts deterministic fake data for demos.
- `scripts/reset_demo_data.py`: clears and reloads demo data.

Fake data should include:

- 30 to 50 books across common genres
- Multiple authors
- Inventory levels with some low-stock examples
- 10 to 20 customers
- Customer loyalty tiers and reading preferences
- Several active, canceled, and picked-up reservations
- Several days of sales history

Keep fake data deterministic by using a fixed random seed.

## Phase 3: MCP Servers

Implement each MCP server as a separate package with its own `server.py`, `tools.py`, and `repository.py`.

### Catalog MCP

Tools:

- `search_books`
- `get_book_details`
- `recommend_books`

Responsibilities:

- Read catalog and author data
- Filter by genre, price, audience, author, and keyword
- Return structured recommendation candidates

### Customer MCP

Tools:

- `get_customer`
- `lookup_loyalty_status`
- `update_customer_preferences`

Responsibilities:

- Read customer profile data
- Read loyalty status
- Write preference updates

### Store Operations MCP

Tools:

- `check_stock`
- `list_low_stock`
- `create_reservation`
- `cancel_reservation`
- `mark_reservation_picked_up`
- `adjust_inventory`
- `list_today_pickups`
- `daily_sales_summary`
- `top_selling_books`

Responsibilities:

- Read and write inventory state
- Create and update reservations
- Summarize sales
- Enforce simple stock constraints for reservations

### Upcoming Releases MCP

Tools:

- `search_upcoming_book_releases`

Responsibilities:

- Search for upcoming releases by author, theme, genre, or audience
- Use Tavily as the external internet search provider
- Return structured status values such as `ok`, `missing_api_key`, and `search_error`
- Keep internet-search credentials out of frontend and browser containers

Each MCP server should:

- Use FastMCP tool definitions
- Run over HTTP for Docker Compose
- Read configuration from environment variables
- Return structured JSON-compatible data
- Keep SQL or repository logic outside tool registration code
- Expose health and readiness checks through the surrounding HTTP service

Mutating MCP tools should write to PostgreSQL. The normal agent flow must pause for human approval before calling any mutating tool. For extra safety, write tools should accept approval metadata such as `approval_id` so direct internal calls can be audited.

## Phase 4: Agents

Implement each agent as an independently runnable A2A server.

### Agent Runtime Design

Each agent runs as an independently callable FastAPI service. A2A-style
endpoints are the external service protocol, while the current internal runtime
uses explicit Python orchestration, FastMCP tool discovery and calls,
deterministic direct repository fallbacks for core demo flows, approval gates
for write tools, and provider-specific final-answer polishing.

Tool behavior:

- Agents should be connected to their assigned MCP servers.
- At startup, each agent should discover available MCP tools for its assigned servers.
- The runtime chooses the supported demo tool flow from the selected agent and
  user request. Final-answer polishing may use OpenAI or Ollama depending on
  the agent's configured `model_provider`.
- Keep deterministic routing focused on demo flows, safety checks, approval
  gates, and fallbacks. Future model-driven tool selection can still be added
  behind the same A2A and MCP boundaries.

Master agents may use their own MCP tools and may also call subagents over A2A.
For presentation flows, the runtime delegates to the relevant subagent when the
requested workflow calls for it, while keeping direct tool use available for
simple master-agent scenarios.

Streaming behavior:

- Forward useful runtime events through `/a2a/stream` as NDJSON and through
  `/v1/chat/completions` as SSE chunks when OpenAI-compatible streaming is
  requested.
- Preserve tool-call, subagent-call, approval, and final-output events in the trace where possible.

### Customer Concierge

Type: master agent

Connections:

- Catalog MCP
- Store Operations MCP
- Customer MCP
- A2A to Catalog Specialist
- A2A to Reservation Specialist
- A2A to Message Drafter

Responsibilities:

- Interpret customer requests
- Delegate catalog discovery
- Delegate reservation operations
- Use customer context when available
- Produce final customer-facing answers

### Store Manager

Type: master agent

Connections:

- Catalog MCP
- Store Operations MCP
- A2A to Catalog Specialist
- A2A to Reservation Specialist
- A2A to Message Drafter

Responsibilities:

- Summarize opening or closing priorities
- Identify operational issues
- Review sales, low stock, and reservations
- Produce staff-facing briefings

### Catalog Specialist

Type: subagent

Connections:

- Catalog MCP

Responsibilities:

- Search books
- Recommend books
- Explain catalog matches

### Reservation Specialist

Type: subagent

Connections:

- Store Operations MCP
- Customer MCP

Responsibilities:

- Check stock
- Create reservations
- Cancel reservations
- Mark reservations as picked up
- Use customer context when helpful

### Message Drafter

Type: subagent

Connections:

- No MCP tools

Responsibilities:

- Draft customer confirmations
- Draft cancellation messages
- Draft apology notes
- Draft staff briefings

### Release Scout

Type: subagent

Connections:

- Upcoming Releases MCP
- Ollama model runtime

Responsibilities:

- Search the internet for upcoming book releases by theme, genre, or author
- Use Tavily-backed source results from the Upcoming Releases MCP server
- Use Ollama `llama3.2:3b` for source-backed final-answer polishing
- Stay independent from existing OpenAI-backed agents unless a user selects it directly

## Phase 5: A2A Wiring

1. Expose an A2A JSON-RPC streaming endpoint for every agent.
2. Give every agent an agent card with:
   - Name
   - Description
   - Capabilities
   - URL
3. Implement a shared A2A client helper.
4. Configure master agents with URLs for their subagents.
5. Keep subagents callable directly by users or by master agents.
6. Stream intermediate events where possible:
   - Run started
   - Tool discovery
   - Tool call requested
   - Tool call completed
   - Subagent call requested
   - Subagent response received
   - Approval required
   - Final answer
7. Use request and response payloads that include:
   - Original request
   - Structured context
   - Tool results
   - Approval state if the run is paused
   - Final answer or draft
8. Expose a health endpoint for each agent service.

## Phase 6: Human Approval Flow

Write actions should mutate PostgreSQL, but the normal agent flow must pause for human approval before side effects happen.

Approval-gated actions:

- `create_reservation`
- `cancel_reservation`
- `mark_reservation_picked_up`
- `adjust_inventory`
- `update_customer_preferences`

Current implementation:

1. Detect or select the mutating operation during the agent run.
2. Return an approval interruption instead of calling the MCP write tool immediately.
3. Persist a pending approval record in PostgreSQL.
4. Surface the pending action to the user or operator with:
   - Agent name
   - Tool name
   - Proposed arguments
   - Human-readable summary
   - Run state metadata
5. On approval, call the underlying write operation and include approval metadata such as `approval_id`.
6. On rejection, mark the approval rejected and perform no database mutation.

For this demo, the original agent run ends with a "waiting for human approval"
answer after creating the pending approval. After the operator approves or
rejects the request, the user can ask a follow-up question and the agent reads
the updated database state.

## Phase 7: ChatKit Frontend

The frontend should let a user:

- Choose which agent to talk to
- Send messages to any agent independently
- See streamed responses
- See tool calls and subagent calls as they happen
- Approve or reject write actions
- Inspect final results and relevant structured data

Use a ChatKit-oriented custom Python server and connect it to the Python A2A
services. This keeps orchestration in Python while giving the demo a polished
streaming chat UI.

Frontend components:

- `frontend-gateway`: Python service that exposes `/chat`, `/chatkit`, agent discovery, and approval routes.
- `frontend`: browser-facing static app served from its own Docker container.

`frontend-gateway` responsibilities:

- Expose the `/chat` endpoint for the current browser UI.
- Expose the `/chatkit` endpoint as the ChatKit-oriented SSE adapter.
- Accept the selected agent from frontend context or thread metadata.
- Route user messages to the selected A2A agent.
- Stream agent responses, tool activity, subagent activity, and approval events back to the browser UI and ChatKit adapter.
- Receive approval or rejection actions and execute or reject the pending write.
- Store approval state using PostgreSQL.
- Expose health and readiness endpoints.

`frontend` responsibilities:

- Provide a simple browser UI for the demo.
- Let the user select any of the six agents.
- Display starter prompts for customer and staff scenarios.
- Connect to `frontend-gateway` using `FRONTEND_GATEWAY_PUBLIC_URL`; keep `CHATKIT_API_PATH` available for the ChatKit adapter.
- Show streamed responses, inline run timelines, and approval cards.
- Clear the visible chat transcript when the selected agent changes.
- Be built and run as a separate Docker service.

Implementation notes:

- Keep all orchestration, agent, MCP, approval, and persistence logic in Python.
- Keep browser code minimal and focused on gateway streaming, agent selection, approvals, and visual shell.
- Avoid Agent Builder-hosted workflows for new work. Agent Builder is in a transition window and is scheduled to shut down on November 30, 2026. ChatKit custom server integrations remain the selected path for this project.
- Keep the event adapter modular so AG-UI can be added later if a vendor-neutral event protocol becomes useful.

## Phase 8: Dockerization

Use Docker Compose services for:

- `postgres`
- `catalog-mcp`
- `customer-mcp`
- `store-operations-mcp`
- `upcoming-releases-mcp` in the optional `local-llm` profile
- `customer-concierge-agent`
- `store-manager-agent`
- `catalog-specialist-agent`
- `reservation-specialist-agent`
- `message-drafter-agent`
- `release-scout-agent` in the optional `local-llm` profile
- `frontend-gateway`
- `frontend`
- `bookstore-cli` for one-off database scripts
- `ollama` and `ollama-pull` in the optional `local-llm` profile

Use one reusable Python application Dockerfile for MCP servers, agents, `frontend-gateway`, and `bookstore-cli`. Each long-running Python service sets `BOOKSTORE_SERVICE_MODULE` so the same image layout can run a different module entrypoint; one-off CLI jobs can override the container args with `python -m ...`.

Use `frontend/Dockerfile` for the browser-facing frontend component. It can serve static assets directly or run a minimal static web server. The frontend container should not contain OpenAI credentials or database credentials.

Docker requirements:

- Install Python dependencies with `uv sync --locked` or `uv sync --frozen`.
- Run Python services from the locked virtual environment through the container entrypoint.
- Expose ports for each MCP server, A2A agent, the frontend gateway, and the frontend.
- Use environment variables from `.env`.
- Mount source code in development if live editing is desired.
- Add health checks for all long-running services.
- Set `frontend` to depend on `frontend-gateway`.
- Set `frontend-gateway` to depend on the default OpenAI-backed agent services.
  In Docker Compose, Release Scout is part of the optional `local-llm` profile.
- Make `release-scout-agent` depend on healthy `ollama`, completed `ollama-pull`,
  and healthy `upcoming-releases-mcp`.
- Keep `OPENAI_API_KEY` available only to backend services that need model access, not to the browser-facing frontend container.
- Build deployable agent and MCP images with service-specific image tags such as `bookstore/catalog-mcp:local` and `bookstore/customer-concierge-agent:local`.
- Keep plain Kubernetes manifests under `k8s/base` for the original core stack.
  Use `k8s/kaos` for the current full stack with KAOS `ModelAPI`,
  `MCPServer`, and `Agent` resources.

## Phase 9: Command Documentation

Create `COMMANDS.md` with commands for:

```text
uv sync
uv run ruff check .
uv run pytest
docker compose build
docker compose up postgres
docker compose run --rm bookstore-cli python -m scripts.init_db
docker compose run --rm bookstore-cli python -m scripts.seed_fake_data
docker compose run --rm bookstore-cli python -m scripts.reset_demo_data
docker compose up
docker compose logs -f catalog-mcp
docker compose logs -f customer-concierge-agent
docker compose logs -f release-scout-agent
docker compose logs -f frontend-gateway
docker compose logs -f frontend
make docker-build-agent-mcp-images
bash deploy-secret.sh
kubectl kustomize k8s/kaos | yq 'select(.kind != "Secret" or .metadata.name != "bookstore-secrets")' | kubectl apply -f -
```

Also include direct local commands for starting each server without Docker:

```text
uv run python -m bookstore_agents.mcp_servers.catalog.server
uv run python -m bookstore_agents.mcp_servers.customer.server
uv run python -m bookstore_agents.mcp_servers.store_operations.server
uv run python -m bookstore_agents.mcp_servers.upcoming_releases.server
uv run python -m bookstore_agents.agents.customer_concierge.server
uv run python -m bookstore_agents.agents.store_manager.server
uv run python -m bookstore_agents.agents.catalog_specialist.server
uv run python -m bookstore_agents.agents.reservation_specialist.server
uv run python -m bookstore_agents.agents.message_drafter.server
uv run python -m bookstore_agents.agents.release_scout.server
uv run python -m bookstore_agents.frontend_gateway.server
```

Include sample API calls for:

- Calling each agent directly
- Calling a master agent and watching subagent calls
- Approving a pending write action
- Rejecting a pending write action
- Resetting demo data
- Opening the frontend at its local URL

## Phase 10: Tests

Add focused tests for:

- Catalog search behavior
- Recommendation filtering
- Customer lookup and preference updates
- Reservation creation and stock checks
- Reservation cancellation with approval
- Inventory adjustment with approval
- Approval creation and approved/rejected execution behavior
- A2A JSON-RPC streaming event shape
- Master agent routing decisions
- Message Drafter output formatting with supplied context
- Frontend gateway streaming adapter
- Ollama runtime request construction and fallback behavior
- Release Scout routing and provider isolation
- Upcoming Releases MCP missing-key and Tavily-response handling
- Frontend static selector coverage for Release Scout

Prefer repository and tool-level tests first. Add end-to-end Docker Compose smoke tests after the basic system works locally.

## Phase 11: Documentation

Update or create:

- `README.md`: overview, architecture, quick start
- `COMMANDS.md`: local and Docker commands
- `docs/bookstore-agent-scenario.md`: business scenario
- `docs/architecture.md`: optional deeper architecture notes
- `docs/demo-script.md`: optional presenter script with example prompts
- `docs/frontend-options.md`: frontend recommendation and alternatives

## Decision Log

1. Agents should have access to their assigned MCP servers and discover available tools. Supported demo workflows use explicit runtime routing, with room to add model-driven tool choice later.
2. Write actions should mutate PostgreSQL, but the agent flow should pause and wait for human approval before executing them.
3. A2A should use JSON-RPC streaming for agent-to-agent communication.
4. Every long-running service should expose health and readiness endpoints for Docker Compose.
5. OpenAI backs the existing agents, while Ollama backs Release Scout. API keys, model names, and service URLs should come from the environment or KAOS model APIs.
6. Use the OpenAI Python SDK for existing-agent final answer polishing and Ollama's native `/api/chat` endpoint for Release Scout. Keep the OpenAI Agents SDK dependency available, but the custom Python runtime is the current primary runtime.
7. Use ChatKit custom server integration for the frontend.
8. Build the frontend as a separate dockerized component.
9. Use `*_HOST_PORT` variables for Docker host port overrides while keeping internal service ports stable.
10. The current frontend uses the gateway `/chat` stream directly and keeps `/chatkit` available as a ChatKit-oriented adapter.
