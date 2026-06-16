# Bookstore Frontend

Browser-facing frontend for the Local Bookstore Assistant.

The container serves static assets and writes `config.js` at startup from:

- `FRONTEND_GATEWAY_PUBLIC_URL`
- `CHATKIT_API_PATH`

The current UI calls `frontend-gateway` through the `/chat` stream using
`FRONTEND_GATEWAY_PUBLIC_URL`. `CHATKIT_API_PATH` is still written to
`config.js` for the gateway's ChatKit-oriented adapter. The UI renders run
timeline steps inline under each user message and shows pending write approvals
in the sidebar. Changing the selected agent clears the visible chat transcript.

Run through Docker Compose and open:

```text
http://localhost:3000
```
