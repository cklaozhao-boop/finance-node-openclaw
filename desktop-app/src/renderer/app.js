const state = {
  dashboardUrl: "",
  unsubscribe: null
};

const elements = {
  statusPill: document.getElementById("status-pill"),
  nodeName: document.getElementById("node-name"),
  localUrl: document.getElementById("local-url"),
  publicUrl: document.getElementById("public-url"),
  tokenValue: document.getElementById("token-value"),
  logBox: document.getElementById("log-box"),
  loadingState: document.getElementById("loading-state"),
  dashboardFrame: document.getElementById("dashboard-frame"),
  refreshButton: document.getElementById("refresh-button"),
  browserButton: document.getElementById("browser-button"),
  bindButton: document.getElementById("bind-button"),
  bindResult: document.getElementById("bind-result"),
  agentInput: document.getElementById("agent-input")
};

function setStatus(label, statusClass) {
  elements.statusPill.textContent = label;
  elements.statusPill.className = `status-pill ${statusClass}`;
}

function appendLog(message) {
  const timestamp = new Date().toLocaleTimeString("zh-CN", { hour12: false });
  const line = document.createElement("div");
  line.textContent = `[${timestamp}] ${message}`;
  elements.logBox.appendChild(line);
  elements.logBox.scrollTop = elements.logBox.scrollHeight;
}

function renderInfo(info) {
  state.dashboardUrl = info.dashboardUrl;
  elements.nodeName.textContent = info.nodeName;
  elements.localUrl.textContent = info.localBaseUrl;
  elements.publicUrl.textContent = info.publicBaseUrl;
  elements.tokenValue.textContent = info.token;
  elements.dashboardFrame.src = info.dashboardUrl;
  elements.dashboardFrame.classList.remove("hidden");
  elements.loadingState.classList.add("hidden");
  elements.browserButton.disabled = false;
  setStatus("节点在线", "status-online");
}

async function bootstrap() {
  setStatus("初始化中", "status-pending");
  appendLog("正在初始化桌面工作台...");
  try {
    const info = await window.financeDesktop.bootstrap();
    appendLog("本地节点已就绪。");
    renderInfo(info);
  } catch (error) {
    setStatus("启动失败", "status-error");
    appendLog(error.message || String(error));
  }
}

async function refresh() {
  setStatus("刷新中", "status-pending");
  appendLog("正在刷新本地节点状态...");
  try {
    const info = await window.financeDesktop.refresh();
    appendLog("状态刷新成功。");
    renderInfo(info);
  } catch (error) {
    setStatus("刷新失败", "status-error");
    appendLog(error.message || String(error));
  }
}

async function bindAgent() {
  const agentName = elements.agentInput.value.trim();
  if (!agentName) {
    elements.bindResult.textContent = "请输入 agent 名称。";
    return;
  }

  elements.bindResult.textContent = "正在绑定...";
  appendLog(`正在绑定 OpenClaw agent: ${agentName}`);
  try {
    const result = await window.financeDesktop.bindAgent(agentName);
    elements.bindResult.textContent = `已绑定到 ${result.agentName}：${result.workspaceDir}`;
    appendLog(`绑定完成：${result.workspaceDir}`);
  } catch (error) {
    elements.bindResult.textContent = error.message || String(error);
    appendLog(error.message || String(error));
  }
}

elements.refreshButton.addEventListener("click", refresh);
elements.browserButton.addEventListener("click", () => {
  if (state.dashboardUrl) {
    window.financeDesktop.openExternal(state.dashboardUrl);
  }
});
elements.bindButton.addEventListener("click", bindAgent);
elements.agentInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    bindAgent();
  }
});

state.unsubscribe = window.financeDesktop.onBootstrapLog((message) => appendLog(message));
bootstrap();
