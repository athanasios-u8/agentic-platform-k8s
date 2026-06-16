const config = window.BOOKSTORE_CONFIG || {
  gatewayUrl: "http://localhost:8300",
  chatkitPath: "/chatkit",
};

const agentSelect = document.querySelector("#agent-select");
const form = document.querySelector("#chat-form");
const input = document.querySelector("#message-input");
const messages = document.querySelector("#messages");
const approvals = document.querySelector("#approval-list");
let latestTimeline = null;

function scrollMessagesToBottom() {
  messages.scrollTop = messages.scrollHeight;
}

function createMessage(role, text) {
  const item = document.createElement("div");
  item.className = `message ${role}`;
  item.textContent = text;
  return item;
}

function createTurn(prompt) {
  const turn = document.createElement("article");
  turn.className = "turn";
  const userMessage = createMessage("user", prompt);
  const timeline = document.createElement("div");
  timeline.className = "run-timeline";
  const timelineHeader = document.createElement("div");
  timelineHeader.className = "run-timeline-header";
  timelineHeader.textContent = "Run timeline";
  const steps = document.createElement("div");
  steps.className = "run-steps";
  timeline.append(timelineHeader, steps);
  turn.append(userMessage, timeline);
  messages.appendChild(turn);
  latestTimeline = steps;
  scrollMessagesToBottom();
  return { turn, timeline: steps };
}

function appendAssistantMessage(turn, text) {
  turn.appendChild(createMessage("assistant", text));
  scrollMessagesToBottom();
}

function summarizePayload(payload) {
  const bits = [];
  if (payload.agent) bits.push(payload.agent);
  if (payload.subagent) bits.push(payload.subagent);
  if (payload.tool) bits.push(payload.tool);
  if (payload.approval_id) bits.push(payload.approval_id);
  return bits.join(" · ");
}

function appendEvent(event, targetTimeline = latestTimeline) {
  if (!targetTimeline) return;
  const payload = event.params?.event || event;
  const item = document.createElement("details");
  item.className = "run-step";
  const summary = document.createElement("summary");
  const title = document.createElement("span");
  title.className = "run-step-title";
  title.textContent = payload.type || "event";
  const metaText = summarizePayload(payload);
  if (metaText) {
    const meta = document.createElement("span");
    meta.className = "run-step-meta";
    meta.textContent = metaText;
    summary.append(title, meta);
  } else {
    summary.appendChild(title);
  }
  const detail = document.createElement("pre");
  detail.textContent = JSON.stringify(payload, null, 2);
  item.append(summary, detail);
  targetTimeline.appendChild(item);
  scrollMessagesToBottom();
}

async function sendMessage(prompt) {
  const agent = agentSelect.value;
  const { turn, timeline } = createTurn(prompt);
  input.value = "";
  const response = await fetch(`${config.gatewayUrl}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ agent, message: prompt, context: { agent } }),
  });

  if (!response.ok || !response.body) {
    appendAssistantMessage(turn, `Request failed: ${response.status}`);
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finalText = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";
    for (const line of lines) {
      if (!line.trim()) continue;
      const event = JSON.parse(line);
      appendEvent(event, timeline);
      const payload = event.params?.event || {};
      if (payload.type === "final" && payload.answer) {
        finalText = payload.answer;
      }
    }
  }

  appendAssistantMessage(turn, finalText || "Run completed.");
  await loadApprovals();
}

async function loadApprovals() {
  const response = await fetch(`${config.gatewayUrl}/approvals`);
  if (!response.ok) return;
  const rows = await response.json();
  approvals.innerHTML = "";
  if (!rows.length) {
    const empty = document.createElement("p");
    empty.className = "empty-state";
    empty.textContent = "No pending approvals";
    approvals.appendChild(empty);
    return;
  }
  for (const row of rows) {
    const card = document.createElement("article");
    card.className = "approval-card";
    const title = document.createElement("strong");
    title.textContent = row.tool_name;
    const summary = document.createElement("p");
    summary.textContent = row.summary;
    const actions = document.createElement("div");
    actions.className = "approval-actions";
    const approve = document.createElement("button");
    approve.textContent = "Approve";
    approve.addEventListener("click", () => resolveApproval(row.approval_id, "approve"));
    const reject = document.createElement("button");
    reject.textContent = "Reject";
    reject.className = "secondary";
    reject.addEventListener("click", () => resolveApproval(row.approval_id, "reject"));
    actions.append(approve, reject);
    card.append(title, summary, actions);
    approvals.appendChild(card);
  }
}

async function resolveApproval(id, action) {
  const response = await fetch(`${config.gatewayUrl}/approvals/${id}/${action}`, { method: "POST" });
  const payload = await response.json();
  appendEvent({ params: { event: { type: `approval_${action}d`, ...payload } } });
  await loadApprovals();
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const prompt = input.value.trim();
  if (prompt) await sendMessage(prompt);
});

agentSelect.addEventListener("change", () => {
  messages.innerHTML = "";
  latestTimeline = null;
  input.value = "";
  loadApprovals();
});

document.querySelectorAll("[data-prompt]").forEach((button) => {
  button.addEventListener("click", () => {
    input.value = button.dataset.prompt || "";
    input.focus();
  });
});

document.querySelector("#refresh-approvals").addEventListener("click", loadApprovals);

loadApprovals();
