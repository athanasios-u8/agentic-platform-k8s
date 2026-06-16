# Frontend Options

## Context

The Local Bookstore Assistant needs a frontend for interacting with five independently callable agents. The frontend should support streaming responses, visible tool and subagent activity, and human approval before write actions mutate PostgreSQL.

As of June 16, 2026, the recommended OpenAI-native path is to use the OpenAI Agents SDK for the backend agent runtime and ChatKit with a custom server for the frontend experience.

## Recommendation

Use a ChatKit-oriented custom Python server with a lightweight browser UI.

Decision: selected for implementation.

This means:

- Backend agents use the OpenAI Agents SDK.
- Agents remain independently callable over A2A.
- The frontend gateway routes user messages to the selected A2A agent.
- The current browser UI consumes the gateway's `/chat` NDJSON stream.
- The gateway also exposes `/chatkit` as an SSE adapter for ChatKit-style integrations.
- Approval requests appear as sidebar cards in the current UI.
- The browser-facing frontend is built and run as its own Docker service.

This path gives the demo a polished chat interface without moving orchestration out of our Python backend.

## Selected Architecture

Use two frontend-related services:

- `frontend-gateway`: Python service that exposes `/chat`, `/chatkit`, agent discovery, and approval routes.
- `frontend`: browser-facing static app, served from its own Docker container.

The `frontend` service should not receive `OPENAI_API_KEY`, database credentials, or direct MCP credentials. It should only know the public URL/path of `frontend-gateway`.

Current UI behavior:

- Agent selection is independent and clears the visible chat transcript when changed.
- Run timeline steps render inline below the user message that started the run.
- Long conversations scroll inside the conversation pane.
- Pending approvals are shown in the sidebar and can be approved or rejected from there.

## AgentKit Clarification

AgentKit can be useful as an umbrella for OpenAI agent-building capabilities, especially Agents SDK, ChatKit, and eval workflows.

For this project:

- Use the OpenAI Agents SDK for agent logic, model calls, tool choice, streaming, and approvals.
- Use the ChatKit-oriented custom server integration path for the frontend gateway.
- Avoid Agent Builder-hosted workflows for new implementation work. OpenAI documentation says Agent Builder is in a transition window and is scheduled to shut down on November 30, 2026.

## Option A: ChatKit Custom Server

Recommended.

Best when:

- We want the most OpenAI-native frontend path.
- We want a polished streaming chat UI.
- We want widgets or actions for approval flows.
- We want the backend to stay Python and server-owned.

Pros:

- Works with OpenAI Agents SDK backends.
- Supports streaming from a custom server.
- Supports widgets, forms, actions, and progress events.
- Good fit for approval cards.
- Easier to present than a fully custom frontend.

Cons:

- Adds a ChatKit server protocol to the project.
- Requires some frontend HTML and JavaScript.
- Less vendor-neutral than AG-UI.

## Option B: AG-UI Protocol

Best when:

- We want a vendor-neutral event protocol.
- We want detailed control over visible event streams.
- We want to design custom visualizations for A2A calls, MCP calls, approvals, and traces.

Pros:

- Open event-based protocol.
- Explicit event types for streaming text, tool calls, state, and errors.
- Good fit for custom agent UI surfaces.

Cons:

- More frontend work.
- More adapter code between OpenAI Agents SDK events, A2A events, and AG-UI events.
- Approval UI must be designed and implemented by us.

## Option C: Simple FastAPI Streaming UI

Best when:

- We want the fastest custom demo.
- We want minimal dependencies.
- We want total control over the event protocol.

Pros:

- Simple to implement.
- Easy to Dockerize.
- Can be plain HTML and JavaScript.

Cons:

- We would invent and maintain our own event protocol.
- Approval UI and trace rendering would be custom work.
- Less reusable than ChatKit or AG-UI.

## Option D: Streamlit Or Gradio

Best when:

- We want a Python-first internal demo.
- We want to minimize frontend engineering.

Pros:

- Mostly Python.
- Fast to build.
- Good for simple demos.

Cons:

- Less suitable for production-like streaming agent UX.
- Approval and resume flows may feel bolted on.
- Harder to show rich tool-call and subagent-call timelines.

## Proposed Decision

Start with Option A: ChatKit custom server.

Status: accepted.

Implementation status: the repository currently ships a static frontend that uses
the gateway's `/chat` stream directly, plus a `/chatkit` SSE adapter that keeps
the gateway aligned with the selected ChatKit direction.

Keep the event adapter modular so AG-UI can be added later if we decide the demo needs a more explicit protocol-level visualization of A2A and MCP activity.

## References

- OpenAI Agents SDK: https://developers.openai.com/api/docs/guides/agents
- OpenAI ChatKit: https://developers.openai.com/api/docs/guides/chatkit
- OpenAI custom ChatKit integrations: https://developers.openai.com/api/docs/guides/custom-chatkit
- OpenAI tools and MCP guidance: https://developers.openai.com/api/docs/guides/tools
- AG-UI protocol: https://github.com/ag-ui-protocol/ag-ui
