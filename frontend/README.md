# Bookstore Frontend

Browser-facing frontend for the Local Bookstore Assistant.

The container serves static assets and writes `config.js` at startup from:

- `FRONTEND_GATEWAY_PUBLIC_URL`
- `CHATKIT_API_PATH`

The current UI calls `frontend-gateway` through the `/chat` stream using
`FRONTEND_GATEWAY_PUBLIC_URL`. The selector is static and contains the six
built-in gateway agent keys: Customer Concierge, Store Manager, Catalog
Specialist, Reservation Specialist, Message Drafter, and Release Scout. In local
Docker Compose runs, Release Scout requires the optional `local-llm` profile
because it depends on Ollama and the upcoming releases MCP server.
`CHATKIT_API_PATH` is still written to `config.js` for the gateway's
ChatKit-oriented adapter.

The browser does not call MCP servers, OpenAI, Ollama, Tavily, or PostgreSQL
directly. The gateway routes selected-agent chat requests and approval actions.

The UI renders run timeline steps inline under each user message and shows
pending write approvals in the sidebar. Changing the selected agent clears the
visible chat transcript.

Run through Docker Compose and open:

```text
http://localhost:3000
```
