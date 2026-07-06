# Bookstore Frontend

Browser-facing frontend for the Local Bookstore Assistant.

The container serves static assets and writes `config.js` at startup from:

- `FRONTEND_GATEWAY_PUBLIC_URL`
- `CHATKIT_API_PATH`

The current UI calls `frontend-gateway` through the `/chat` stream using
`FRONTEND_GATEWAY_PUBLIC_URL`. The left-pane agent list contains the seven
built-in gateway agent keys: Customer Concierge, Store Manager, Catalog
Specialist, Reservation Specialist, Message Drafter, Release Scout, and Review
Summarizer. In local Docker Compose runs, Release Scout is part of the runtime
stack because Ollama and the upcoming releases MCP server start with the
default services. Review Summarizer is part of the runtime stack and requires
the Azure AI Search review index to be populated before it can return review
summaries.
`CHATKIT_API_PATH` is still written to `config.js` for the gateway's
ChatKit-oriented adapter.

The browser does not call MCP servers, OpenAI, Ollama, Tavily, Azure AI Search,
or PostgreSQL directly. The gateway routes selected-agent chat requests and
approval actions.

The UI renders run timeline steps inline under each user message, shows pending
write approvals in the sidebar, and keeps recent chats in browser
`localStorage`. Selecting another agent starts a fresh chat when the current one
already has messages, or switches the empty draft chat to that agent.

Run through Docker Compose and open:

```text
http://localhost:3000
```
