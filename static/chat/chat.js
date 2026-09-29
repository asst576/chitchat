(() => {
  const providerSelect = document.querySelector("#provider-select");
  const modelSelect = document.querySelector("#model-select");
  const historyList = document.querySelector("#history-list");
  const historyEmpty = document.querySelector("#history-empty");
  const historyCount = document.querySelector("#history-count");
  const messageList = document.querySelector("#message-list");
  const welcomeCard = document.querySelector("#welcome-card");
  const promptForm = document.querySelector("#prompt-form");
  const promptInput = document.querySelector("#prompt-input");
  const sendButton = document.querySelector("#send-button");
  const statusLine = document.querySelector("#status-line");
  const proxyDisclosure = document.querySelector("#proxy-disclosure");
  const csrfToken = document.querySelector("[name=csrfmiddlewaretoken]").value;
  const apiRoot = new URL("api", document.baseURI).pathname.replace(/\/$/, "");
  const loginUrl = document.documentElement.dataset.loginUrl;

  let modelOptions = [];
  let conversations = [];
  let activeConversationId = null;
  let pendingRow = null;
  let optimisticUserRow = null;
  let busy = false;

  async function request(url, options = {}) {
    const headers = new Headers(options.headers || {});
    if (options.body) {
      headers.set("Content-Type", "application/json");
      headers.set("X-CSRFToken", csrfToken);
    }
    const response = await fetch(url, { ...options, headers, credentials: "same-origin" });
    if (response.status === 401) {
      window.location.assign(new URL(loginUrl, document.baseURI));
      throw new Error("Your session has expired. Redirecting to sign in.");
    }
    let data;
    try {
      data = await response.json();
    } catch {
      throw new Error("The server returned an unreadable response.");
    }
    if (!response.ok) {
      const error = new Error(data.error?.message || "The request could not be completed.");
      error.data = data;
      throw error;
    }
    return data;
  }

  function uniqueProviders() {
    const seen = new Set();
    return modelOptions.filter((option) => {
      if (seen.has(option.provider_id)) return false;
      seen.add(option.provider_id);
      return true;
    });
  }

  function renderModelOptions(preferredProvider = "", preferredModel = "") {
    const availableProviders = uniqueProviders();
    providerSelect.replaceChildren();
    for (const provider of availableProviders) {
      const option = document.createElement("option");
      option.value = provider.provider_id;
      option.textContent = provider.provider_label;
      option.disabled = !provider.configured;
      providerSelect.append(option);
    }

    const configuredProviders = availableProviders.filter((provider) => provider.configured);
    const providerId = configuredProviders.some((provider) => provider.provider_id === preferredProvider)
      ? preferredProvider
      : configuredProviders[0]?.provider_id || availableProviders[0]?.provider_id || "";
    providerSelect.value = providerId;
    providerSelect.disabled = configuredProviders.length === 0;

    const choices = modelOptions.filter((option) => option.provider_id === providerId);
    modelSelect.replaceChildren();
    for (const model of choices) {
      const option = document.createElement("option");
      option.value = model.model_id;
      option.textContent = model.model_label;
      option.disabled = !model.configured;
      modelSelect.append(option);
    }
    const selectedModel = choices.some((model) => model.model_id === preferredModel && model.configured)
      ? preferredModel
      : choices.find((model) => model.configured)?.model_id || choices[0]?.model_id || "";
    modelSelect.value = selectedModel;
    modelSelect.disabled = !selectedModel || !configuredProviders.some((provider) => provider.provider_id === providerId);
    updateSendButton();
  }

  function updateSendButton() {
    const configuredProviders = uniqueProviders().filter((provider) => provider.configured);
    const selectedModel = modelOptions.find(
      (option) => option.provider_id === providerSelect.value && option.model_id === modelSelect.value,
    );
    providerSelect.disabled = busy || configuredProviders.length === 0;
    modelSelect.disabled = busy || !selectedModel?.configured;
    sendButton.disabled = busy || providerSelect.disabled || modelSelect.disabled;
    sendButton.querySelector("span:first-child").textContent = busy ? "Working" : "Send";
  }

  function formatDate(value) {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "";
    return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" }).format(date);
  }

  function renderHistory() {
    historyList.replaceChildren();
    historyCount.textContent = String(conversations.length);
    historyEmpty.hidden = conversations.length > 0;
    for (const conversation of conversations) {
      const item = document.createElement("li");
      const button = document.createElement("button");
      button.type = "button";
      button.className = "history-item";
      button.dataset.conversationId = conversation.id;
      button.disabled = busy;
      if (conversation.id === activeConversationId) button.setAttribute("aria-current", "page");
      const title = document.createElement("span");
      title.className = "history-title";
      title.textContent = conversation.title;
      const date = document.createElement("span");
      date.className = "history-date";
      date.textContent = formatDate(conversation.updated_at);
      button.append(title, date);
      button.addEventListener("click", () => openConversation(conversation.id));
      item.append(button);
      historyList.append(item);
    }
  }

  function makeMessageRow(message) {
    const row = document.createElement("article");
    row.className = `message-row ${message.role}${message.status === "failed" ? " failed" : ""}`;
    row.dataset.messageId = message.id;

    const marker = document.createElement("span");
    marker.className = "message-marker";
    marker.setAttribute("aria-hidden", "true");
    marker.textContent = message.role === "assistant" ? "L" : "Y";

    const content = document.createElement("div");
    content.className = "message-content";
    const meta = document.createElement("div");
    meta.className = "message-meta";
    meta.textContent = message.role === "assistant" ? "LiteChat" : "You";
    const bubble = document.createElement("div");
    bubble.className = "message-bubble";

    if (message.status === "pending") {
      const pending = document.createElement("span");
      pending.className = "message-pending";
      const pulse = document.createElement("span");
      pulse.className = "pulse";
      pulse.setAttribute("aria-hidden", "true");
      pending.append(pulse, document.createTextNode("Preparing a response..."));
      bubble.append(pending);
    } else if (message.status === "failed") {
      const error = document.createElement("div");
      error.className = "message-error";
      const text = document.createElement("span");
      text.textContent = message.failure_message || "The response failed.";
      error.append(text);
      if (message.id && activeConversationId) {
        const retry = document.createElement("button");
        retry.type = "button";
        retry.className = "retry-button";
        retry.textContent = "Retry response";
        retry.addEventListener("click", () => retryResponse(message.id));
        error.append(retry);
      }
      bubble.append(error);
    } else {
      bubble.textContent = message.content;
    }

    content.append(meta, bubble);
    row.append(marker, content);
    return row;
  }

  function renderMessages(messages) {
    messageList.replaceChildren();
    pendingRow = null;
    optimisticUserRow = null;
    welcomeCard.hidden = messages.length > 0;
    if (!messages.length) {
      messageList.append(welcomeCard);
      return;
    }
    for (const message of messages) messageList.append(makeMessageRow(message));
    messageList.scrollTop = messageList.scrollHeight;
  }

  function showPending(prompt = null) {
    removePending();
    if (prompt !== null) {
      optimisticUserRow = makeMessageRow({ role: "user", status: "completed", content: prompt });
    }
    pendingRow = makeMessageRow({ role: "assistant", status: "pending" });
    welcomeCard.hidden = true;
    if (optimisticUserRow) messageList.append(optimisticUserRow);
    messageList.append(pendingRow);
    messageList.scrollTop = messageList.scrollHeight;
  }

  function removePending() {
    pendingRow?.remove();
    optimisticUserRow?.remove();
    pendingRow = null;
    optimisticUserRow = null;
  }

  async function refreshHistory() {
    const data = await request(`${apiRoot}/conversations/`);
    conversations = data.conversations;
    renderHistory();
  }

  async function openConversation(id) {
    try {
      const data = await request(`${apiRoot}/conversations/${id}/`);
      activeConversationId = data.conversation.id;
      renderModelOptions(data.conversation.provider_id, data.conversation.model_id);
      renderMessages(data.messages);
      renderHistory();
      statusLine.textContent = "";
    } catch (error) {
      statusLine.textContent = error.message;
    }
  }

  function startNewConversation() {
    if (busy) return;
    activeConversationId = null;
    renderModelOptions();
    renderMessages([]);
    renderHistory();
    statusLine.textContent = "";
    promptInput.focus();
  }

  function setBusy(value) {
    busy = value;
    promptInput.disabled = value;
    document.querySelector("#new-chat").disabled = value;
    updateSendButton();
    for (const button of historyList.querySelectorAll("button")) button.disabled = value;
  }

  async function sendPrompt(prompt) {
    setBusy(true);
    statusLine.textContent = "";
    showPending(prompt);
    const path = activeConversationId
      ? `${apiRoot}/conversations/${activeConversationId}/messages/`
      : `${apiRoot}/messages/`;
    try {
      const data = await request(path, {
        method: "POST",
        body: JSON.stringify({
          prompt,
          provider_id: providerSelect.value,
          model_id: modelSelect.value,
        }),
      });
      activeConversationId = data.conversation.id;
      promptInput.value = "";
      await openConversation(activeConversationId);
      await refreshHistory().catch((error) => {
        statusLine.textContent = error.message;
      });
    } catch (error) {
      removePending();
      if (error.data?.conversation_id) {
        activeConversationId = error.data.conversation_id;
        await refreshHistory().catch(() => {});
        await openConversation(activeConversationId);
      } else if (!activeConversationId) {
        renderMessages([]);
      }
      statusLine.textContent = error.message;
    } finally {
      setBusy(false);
      promptInput.focus();
    }
  }

  async function retryResponse(assistantMessageId) {
    if (!activeConversationId || busy) return;
    setBusy(true);
    statusLine.textContent = "";
    showPending();
    try {
      await request(`${apiRoot}/conversations/${activeConversationId}/retry/`, {
        method: "POST",
        body: JSON.stringify({ assistant_message_id: assistantMessageId }),
      });
      await refreshHistory();
      await openConversation(activeConversationId);
    } catch (error) {
      removePending();
      statusLine.textContent = error.message;
      await openConversation(activeConversationId);
    } finally {
      setBusy(false);
    }
  }

  providerSelect.addEventListener("change", () => renderModelOptions(providerSelect.value));
  document.querySelector("#new-chat").addEventListener("click", startNewConversation);
  promptForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const prompt = promptInput.value.trim();
    if (!prompt || busy) return;
    if (providerSelect.disabled || modelSelect.disabled) {
      statusLine.textContent = "Configure a provider key on the server before sending a message.";
      return;
    }
    sendPrompt(prompt);
  });
  promptInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      promptForm.requestSubmit();
    }
  });

  async function initialize() {
    try {
      const [providerData, historyData] = await Promise.all([
        request(`${apiRoot}/providers/`),
        request(`${apiRoot}/conversations/`),
      ]);
      modelOptions = providerData.providers;
      proxyDisclosure.textContent = providerData.notice;
      conversations = historyData.conversations;
      renderModelOptions();
      renderHistory();
      if (conversations.length) await openConversation(conversations[0].id);
      if (!modelOptions.some((option) => option.configured)) {
        statusLine.textContent = "No provider key is configured for this server yet.";
      }
    } catch (error) {
      statusLine.textContent = error.message;
    }
  }

  initialize();
})();
