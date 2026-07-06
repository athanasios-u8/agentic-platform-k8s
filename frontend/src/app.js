const config = window.BOOKSTORE_CONFIG || {
  gatewayUrl: "http://localhost:8300",
  chatkitPath: "/chatkit",
};

const STORAGE_KEY = "bookstoreAssistant.chats.v1";
const MAX_STORED_CHATS = 25;
const DEFAULT_AGENT = "customer_concierge";

const agents = [
  {
    key: "customer_concierge",
    name: "Customer Concierge",
    description: "Recommendations, availability, and reservations.",
    prompts: [
      "Find a mystery novel under $20 for my dad and reserve it for customer 1.",
      "Recommend three warm, thoughtful books for a weekend gift.",
      "Can you help me find a book similar to The Thursday Murder Club?",
      "Find a staff pick for a first-time fantasy reader.",
    ],
  },
  {
    key: "store_manager",
    name: "Store Manager",
    description: "Daily operations, sales, stock, and pickups.",
    prompts: [
      "What should I pay attention to before opening today?",
      "List today's pickups.",
      "Which low-stock books should I check before the afternoon rush?",
      "Summarize the store operations that need approval.",
    ],
  },
  {
    key: "catalog_specialist",
    name: "Catalog Specialist",
    description: "Searches and recommends from the catalog.",
    prompts: [
      "Find three science fiction books under $25 for a first-time reader.",
      "Show me cozy mysteries that are currently available.",
      "Which paperback literary fiction titles are good for book clubs?",
      "Find books by Stephen King in the catalog.",
    ],
  },
  {
    key: "reservation_specialist",
    name: "Reservation Specialist",
    description: "Checks stock and prepares reservations.",
    prompts: [
      "Reserve a mystery novel for customer 1.",
      "Check whether today's pickups are ready.",
      "Find available copies of popular gift books and prepare reservations.",
      "Can customer 1 pick up their reserved books today?",
    ],
  },
  {
    key: "message_drafter",
    name: "Message Drafter",
    description: "Drafts customer and staff messages from context.",
    prompts: [
      "Draft a friendly pickup reminder for a reserved book.",
      "Write a concise staff note about low-stock gift books.",
      "Draft a customer message explaining that a requested title is unavailable.",
      "Write a warm recommendation note for a cozy fantasy reader.",
    ],
  },
  {
    key: "release_scout",
    name: "Release Scout",
    description: "Finds upcoming releases by author, theme, or genre.",
    prompts: [
      "Find upcoming cozy fantasy releases.",
      "What new books by Stephen King are coming soon?",
      "Find upcoming romance releases for a front-table display.",
      "Which upcoming science fiction titles should I watch?",
    ],
  },
  {
    key: "review_summarizer",
    name: "Review Summarizer",
    description: "Summarizes indexed reader reviews for a book.",
    prompts: [
      "What do people like and dislike about The Lantern Cipher?",
      "Summarize the reviews for Signal from Glass Moon.",
      "What are readers saying about The Glass Forest?",
      "Are reviews for Dead Drop at Dawn mostly positive or negative?",
    ],
  },
];

const agentByKey = Object.fromEntries(agents.map((agent) => [agent.key, agent]));

const form = document.querySelector("#chat-form");
const input = document.querySelector("#message-input");
const sendButton = document.querySelector("#send-button");
const messages = document.querySelector("#messages");
const approvals = document.querySelector("#approval-list");
const agentList = document.querySelector("#agent-list");
const chatList = document.querySelector("#chat-list");
const newChatButton = document.querySelector("#new-chat");
const recommendationTrack = document.querySelector("#recommendation-track");
const recommendationPrev = document.querySelector("#recommendation-prev");
const recommendationNext = document.querySelector("#recommendation-next");

let latestTimeline = null;
let state = {
  chats: [],
  activeChatId: null,
  activeAgent: DEFAULT_AGENT,
};

function nowIso() {
  return new Date().toISOString();
}

function createId(prefix) {
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

function getAgent(key) {
  return agentByKey[key] || agentByKey[DEFAULT_AGENT];
}

function getActiveChat() {
  return state.chats.find((chat) => chat.id === state.activeChatId) || null;
}

function hasTurns(chat) {
  return Boolean(chat?.turns?.length);
}

function sortChats(chats) {
  return [...chats].sort((a, b) => new Date(b.updatedAt) - new Date(a.updatedAt));
}

function trimStoredChats() {
  const activeChat = getActiveChat();
  let keep = sortChats(state.chats).slice(0, MAX_STORED_CHATS);

  if (activeChat && !keep.some((chat) => chat.id === activeChat.id)) {
    keep = keep.slice(0, MAX_STORED_CHATS - 1);
    keep.push(activeChat);
  }

  state.chats = keep;
}

function serializeState() {
  return JSON.stringify({
    version: 1,
    activeChatId: state.activeChatId,
    activeAgent: state.activeAgent,
    chats: state.chats,
  });
}

function saveState() {
  trimStoredChats();

  while (true) {
    try {
      localStorage.setItem(STORAGE_KEY, serializeState());
      return;
    } catch (error) {
      if (state.chats.length <= 1) return;

      const oldestRemovable = [...state.chats]
        .sort((a, b) => new Date(a.updatedAt) - new Date(b.updatedAt))
        .find((chat) => chat.id !== state.activeChatId);

      if (!oldestRemovable) return;
      state.chats = state.chats.filter((chat) => chat.id !== oldestRemovable.id);
    }
  }
}

function normalizeChat(rawChat) {
  if (!rawChat || typeof rawChat !== "object") return null;
  const agent = agentByKey[rawChat.agent] ? rawChat.agent : DEFAULT_AGENT;
  const createdAt = rawChat.createdAt || nowIso();
  const updatedAt = rawChat.updatedAt || createdAt;
  const turns = Array.isArray(rawChat.turns)
    ? rawChat.turns
        .filter((turn) => turn && typeof turn.prompt === "string")
        .map((turn) => ({
          id: turn.id || createId("turn"),
          prompt: turn.prompt,
          answer: typeof turn.answer === "string" ? turn.answer : "",
          events: Array.isArray(turn.events) ? turn.events : [],
          createdAt: turn.createdAt || createdAt,
        }))
    : [];

  return {
    id: rawChat.id || createId("chat"),
    agent,
    title: rawChat.title || "New chat",
    createdAt,
    updatedAt,
    turns,
  };
}

function loadState() {
  try {
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
    const chats = Array.isArray(stored.chats)
      ? stored.chats.map(normalizeChat).filter(Boolean)
      : [];

    state.chats = chats;
    state.activeChatId = chats.some((chat) => chat.id === stored.activeChatId)
      ? stored.activeChatId
      : sortChats(chats)[0]?.id || null;

    const activeChat = getActiveChat();
    state.activeAgent = activeChat?.agent || (agentByKey[stored.activeAgent] ? stored.activeAgent : DEFAULT_AGENT);
  } catch (error) {
    state = {
      chats: [],
      activeChatId: null,
      activeAgent: DEFAULT_AGENT,
    };
  }
}

function createChat(agentKey = state.activeAgent) {
  const timestamp = nowIso();
  return {
    id: createId("chat"),
    agent: agentByKey[agentKey] ? agentKey : DEFAULT_AGENT,
    title: "New chat",
    createdAt: timestamp,
    updatedAt: timestamp,
    turns: [],
  };
}

function setActiveChat(chat) {
  state.activeChatId = chat.id;
  state.activeAgent = chat.agent;
}

function updateSendButtonState() {
  sendButton.disabled = input.value.trim().length === 0;
}

function startNewChat(agentKey = state.activeAgent) {
  const chat = createChat(agentKey);
  state.chats.unshift(chat);
  setActiveChat(chat);
  latestTimeline = null;
  input.value = "";
  updateSendButtonState();
  saveState();
  renderAll();
}

function ensureActiveChat() {
  let chat = getActiveChat();
  if (chat) return chat;

  chat = createChat(state.activeAgent);
  state.chats.unshift(chat);
  setActiveChat(chat);
  saveState();
  return chat;
}

function deriveTitle(prompt) {
  const collapsed = prompt.replace(/\s+/g, " ").trim();
  if (collapsed.length <= 44) return collapsed;
  return `${collapsed.slice(0, 41).trim()}...`;
}

function scrollMessagesToBottom() {
  messages.scrollTop = messages.scrollHeight;
}

function createMessage(role, text) {
  const item = document.createElement("div");
  item.className = `message ${role}`;
  item.textContent = text;
  return item;
}

function summarizePayload(payload) {
  const bits = [];
  if (payload.agent) bits.push(payload.agent);
  if (payload.subagent) bits.push(payload.subagent);
  if (payload.tool) bits.push(payload.tool);
  if (payload.approval_id) bits.push(payload.approval_id);
  return bits.join(" · ");
}

function createEventElement(event) {
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
  return item;
}

function appendEvent(event, targetTimeline = latestTimeline) {
  if (!targetTimeline) return;
  targetTimeline.appendChild(createEventElement(event));
  scrollMessagesToBottom();
}

function createTurnElement(turn) {
  const turnElement = document.createElement("article");
  turnElement.className = "turn";
  const userMessage = createMessage("user", turn.prompt);
  const timeline = document.createElement("div");
  timeline.className = "run-timeline";
  const timelineHeader = document.createElement("div");
  timelineHeader.className = "run-timeline-header";
  timelineHeader.textContent = "Run timeline";
  const steps = document.createElement("div");
  steps.className = "run-steps";

  for (const event of turn.events) {
    steps.appendChild(createEventElement(event));
  }

  timeline.append(timelineHeader, steps);
  turnElement.append(userMessage, timeline);

  if (turn.answer) {
    turnElement.appendChild(createMessage("assistant", turn.answer));
  }

  return { turnElement, timeline: steps };
}

function appendTurn(turn) {
  const { turnElement, timeline } = createTurnElement(turn);
  messages.appendChild(turnElement);
  latestTimeline = timeline;
  scrollMessagesToBottom();
  return { turnElement, timeline };
}

function appendAssistantMessage(turnElement, text) {
  turnElement.appendChild(createMessage("assistant", text));
  scrollMessagesToBottom();
}

function renderLanding(chat) {
  messages.innerHTML = "";
  latestTimeline = null;

  const landing = document.createElement("section");
  landing.className = "landing";
  landing.setAttribute("aria-live", "polite");

  const agent = document.createElement("p");
  agent.className = "landing-agent";
  agent.textContent = getAgent(chat.agent).name;

  const title = document.createElement("h2");
  title.textContent = "Bookstore Assistant";

  landing.append(agent, title);
  messages.appendChild(landing);
}

function renderMessages() {
  const chat = ensureActiveChat();

  if (!hasTurns(chat)) {
    renderLanding(chat);
    return;
  }

  messages.innerHTML = "";
  latestTimeline = null;

  for (const turn of chat.turns) {
    appendTurn(turn);
  }
}

function renderAgents() {
  agentList.innerHTML = "";

  for (const agent of agents) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "agent-option";
    if (agent.key === state.activeAgent) button.classList.add("active");
    button.addEventListener("click", () => selectAgent(agent.key));

    const name = document.createElement("span");
    name.className = "agent-name";
    name.textContent = agent.name;

    const description = document.createElement("span");
    description.className = "agent-description";
    description.textContent = agent.description;

    button.append(name, description);
    agentList.appendChild(button);
  }
}

function renderChats() {
  chatList.innerHTML = "";
  const chats = sortChats(state.chats);

  if (!chats.length) {
    const empty = document.createElement("p");
    empty.className = "empty-state";
    empty.textContent = "No chats yet";
    chatList.appendChild(empty);
    return;
  }

  for (const chat of chats) {
    const row = document.createElement("div");
    row.className = "chat-row";
    if (chat.id === state.activeChatId) row.classList.add("active");

    const openButton = document.createElement("button");
    openButton.type = "button";
    openButton.className = "chat-open";
    openButton.addEventListener("click", () => selectChat(chat.id));

    const title = document.createElement("span");
    title.className = "chat-title";
    title.textContent = chat.title || "New chat";

    const meta = document.createElement("span");
    meta.className = "chat-meta";
    meta.textContent = getAgent(chat.agent).name;

    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.className = "chat-delete";
    deleteButton.title = "Delete chat";
    deleteButton.setAttribute("aria-label", `Delete ${chat.title || "chat"}`);
    deleteButton.textContent = "x";
    deleteButton.addEventListener("click", (event) => {
      event.stopPropagation();
      deleteChat(chat.id);
    });

    openButton.append(title, meta);
    row.append(openButton, deleteButton);
    chatList.appendChild(row);
  }
}

function renderRecommendations() {
  recommendationTrack.innerHTML = "";
  const agent = getAgent(state.activeAgent);

  for (const prompt of agent.prompts) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "recommendation-card";
    button.textContent = prompt;
    button.addEventListener("click", () => {
      input.value = prompt;
      updateSendButtonState();
      input.focus();
    });
    recommendationTrack.appendChild(button);
  }
}

function renderAll() {
  renderAgents();
  renderChats();
  renderRecommendations();
  renderMessages();
}

function selectAgent(agentKey) {
  const chat = ensureActiveChat();
  state.activeAgent = agentKey;

  if (!hasTurns(chat)) {
    chat.agent = agentKey;
    chat.updatedAt = nowIso();
    setActiveChat(chat);
    input.value = "";
    updateSendButtonState();
    saveState();
    renderAll();
    loadApprovals();
    return;
  }

  startNewChat(agentKey);
  loadApprovals();
}

function selectChat(chatId) {
  const chat = state.chats.find((candidate) => candidate.id === chatId);
  if (!chat) return;

  setActiveChat(chat);
  latestTimeline = null;
  input.value = "";
  updateSendButtonState();
  saveState();
  renderAll();
  loadApprovals();
}

function deleteChat(chatId) {
  const wasActive = state.activeChatId === chatId;
  state.chats = state.chats.filter((chat) => chat.id !== chatId);

  if (!state.chats.length) {
    const chat = createChat(state.activeAgent);
    state.chats.push(chat);
    setActiveChat(chat);
  } else if (wasActive) {
    setActiveChat(sortChats(state.chats)[0]);
  }

  latestTimeline = null;
  input.value = "";
  updateSendButtonState();
  saveState();
  renderAll();
  loadApprovals();
}

function recordEvent(chat, turn, event, targetTimeline = latestTimeline) {
  turn.events.push(event);
  chat.updatedAt = nowIso();
  saveState();
  appendEvent(event, targetTimeline);
}

function recordApprovalEvent(event) {
  const chat = getActiveChat();
  const turn = chat?.turns?.at(-1);
  if (chat && turn) {
    recordEvent(chat, turn, event);
    renderChats();
    return;
  }

  appendEvent(event);
}

async function sendMessage(prompt) {
  const chat = ensureActiveChat();
  const agent = chat.agent;
  const timestamp = nowIso();
  const turn = {
    id: createId("turn"),
    prompt,
    answer: "",
    events: [],
    createdAt: timestamp,
  };

  if (!hasTurns(chat)) {
    messages.innerHTML = "";
    chat.title = deriveTitle(prompt);
  }

  chat.turns.push(turn);
  chat.updatedAt = timestamp;
  state.activeAgent = agent;
  input.value = "";
  updateSendButtonState();
  saveState();
  renderChats();
  renderAgents();
  renderRecommendations();

  const { turnElement, timeline } = appendTurn(turn);
  latestTimeline = timeline;

  try {
    const response = await fetch(`${config.gatewayUrl}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ agent, message: prompt, context: { agent } }),
    });

    if (!response.ok || !response.body) {
      turn.answer = `Request failed: ${response.status}`;
      appendAssistantMessage(turnElement, turn.answer);
      chat.updatedAt = nowIso();
      saveState();
      renderChats();
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
        recordEvent(chat, turn, event, timeline);
        const payload = event.params?.event || {};
        if (payload.type === "final" && payload.answer) {
          finalText = payload.answer;
        }
      }
    }

    turn.answer = finalText || "Run completed.";
    appendAssistantMessage(turnElement, turn.answer);
    chat.updatedAt = nowIso();
    saveState();
    renderChats();
    await loadApprovals();
  } catch (error) {
    turn.answer = `Request failed: ${error.message}`;
    appendAssistantMessage(turnElement, turn.answer);
    chat.updatedAt = nowIso();
    saveState();
    renderChats();
  }
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
    approve.type = "button";
    approve.textContent = "Approve";
    approve.addEventListener("click", () => resolveApproval(row.approval_id, "approve"));
    const reject = document.createElement("button");
    reject.type = "button";
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
  recordApprovalEvent({ params: { event: { type: `approval_${action}d`, ...payload } } });
  await loadApprovals();
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const prompt = input.value.trim();
  updateSendButtonState();
  if (prompt) await sendMessage(prompt);
});

input.addEventListener("input", updateSendButtonState);

newChatButton.addEventListener("click", () => startNewChat(state.activeAgent));

recommendationPrev.addEventListener("click", () => {
  recommendationTrack.scrollBy({ left: -320, behavior: "smooth" });
});

recommendationNext.addEventListener("click", () => {
  recommendationTrack.scrollBy({ left: 320, behavior: "smooth" });
});

loadState();
ensureActiveChat();
renderAll();
updateSendButtonState();
loadApprovals();
