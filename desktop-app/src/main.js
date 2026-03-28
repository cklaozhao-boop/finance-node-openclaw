const { app, BrowserWindow, ipcMain, shell } = require("electron");
const path = require("path");
const os = require("os");
const fs = require("fs/promises");
const net = require("net");
const { spawn } = require("child_process");

const APP_NAME = "Finance Node";
const DEFAULT_PORT = 31888;

let mainWindow = null;

function isMac() {
  return process.platform === "darwin";
}

function configHome() {
  return process.env.XDG_CONFIG_HOME || path.join(os.homedir(), ".config");
}

function dataHome() {
  return process.env.XDG_DATA_HOME || path.join(os.homedir(), ".local", "share");
}

function installPointerPath() {
  return path.join(configHome(), "finance-node-openclaw", "install.json");
}

function defaultInstallRoot() {
  if (isMac()) {
    return path.join(os.homedir(), "Library", "Application Support", "finance-node-openclaw");
  }
  return path.join(dataHome(), "finance-node-openclaw");
}

function repoBundleRoot() {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, "bundle");
  }
  return path.resolve(__dirname, "../..");
}

function bundledInstaller(name) {
  return path.join(repoBundleRoot(), "installer", name);
}

async function pathExists(targetPath) {
  try {
    await fs.access(targetPath);
    return true;
  } catch {
    return false;
  }
}

async function readJson(filePath) {
  return JSON.parse(await fs.readFile(filePath, "utf-8"));
}

async function writeJson(filePath, data) {
  await fs.writeFile(filePath, `${JSON.stringify(data, null, 2)}\n`, "utf-8");
}

async function runScript(scriptPath, args = [], extraEnv = {}, onLine) {
  return await new Promise((resolve, reject) => {
    const child = spawn("/bin/bash", [scriptPath, ...args], {
      cwd: repoBundleRoot(),
      env: {
        ...process.env,
        ...extraEnv
      }
    });

    let stdout = "";
    let stderr = "";

    const emit = (chunk, type) => {
      const text = chunk.toString();
      if (type === "stdout") {
        stdout += text;
      } else {
        stderr += text;
      }
      if (onLine) {
        text
          .split(/\r?\n/)
          .map((line) => line.trimEnd())
          .filter(Boolean)
          .forEach((line) => onLine(line, type));
      }
    };

    child.stdout.on("data", (chunk) => emit(chunk, "stdout"));
    child.stderr.on("data", (chunk) => emit(chunk, "stderr"));
    child.on("error", reject);
    child.on("close", (code) => {
      if (code === 0) {
        resolve({ stdout, stderr });
      } else {
        const error = new Error(stderr || stdout || `Script failed with code ${code}`);
        error.code = code;
        error.stdout = stdout;
        error.stderr = stderr;
        reject(error);
      }
    });
  });
}

async function loadInstallInfo() {
  const pointerPath = installPointerPath();
  if (!(await pathExists(pointerPath))) {
    return null;
  }
  const info = await readJson(pointerPath);
  return {
    pointerPath,
    ...info
  };
}

async function loadRuntimeInfo() {
  const installInfo = await loadInstallInfo();
  if (!installInfo?.configPath) {
    return null;
  }
  const config = await readJson(installInfo.configPath);
  const runtimeDir = path.dirname(installInfo.configPath);
  const connectionInfoPath = path.join(runtimeDir, "connection-info.txt");

  return {
    installInfo,
    runtimeDir,
    connectionInfoPath,
    config,
    token: config.accessToken || config.token,
    nodeName: config.nodeName || APP_NAME,
    port: Number(config.port || DEFAULT_PORT),
    localBaseUrl: `http://127.0.0.1:${Number(config.port || DEFAULT_PORT)}`,
    publicBaseUrl:
      config.tailscaleHostname || config.tailscaleIP
        ? `http://${config.tailscaleHostname || config.tailscaleIP}:${Number(config.port || DEFAULT_PORT)}`
        : `http://127.0.0.1:${Number(config.port || DEFAULT_PORT)}`
  };
}

function isUnauthorizedError(error) {
  return String(error?.message || error || "").includes("Unauthorized");
}

function isAddressInUseError(error) {
  return String(error?.message || error || "").includes("Address already in use");
}

async function isPortAvailable(port) {
  return await new Promise((resolve) => {
    const server = net.createServer();
    server.unref();
    server.on("error", () => resolve(false));
    server.listen({ host: "127.0.0.1", port }, () => {
      server.close(() => resolve(true));
    });
  });
}

async function findAvailablePort(startPort = DEFAULT_PORT + 1, attempts = 50) {
  for (let port = startPort; port < startPort + attempts; port += 1) {
    // eslint-disable-next-line no-await-in-loop
    if (await isPortAvailable(port)) {
      return port;
    }
  }
  throw new Error("未找到可用端口，无法启动 Finance Node。");
}

async function updateRuntimePort(runtime, port, onLine) {
  const configPath = runtime.installInfo.configPath;
  const config = await readJson(configPath);
  config.port = port;
  await writeJson(configPath, config);

  const prepareScript = path.join(runtime.installInfo.appDir, "prepare_finance_node_runtime.sh");
  await runScript(prepareScript, [], {}, (line) => onLine?.(line));
  return await loadRuntimeInfo();
}

async function relocateRuntimePort(runtime, onLine, reason = "") {
  const nextPort = await findAvailablePort(runtime.port + 1);
  if (reason) {
    onLine?.(reason);
  }
  onLine?.(`检测到端口 ${runtime.port} 已被其他服务占用，已切换到 ${nextPort}。`);
  return await updateRuntimePort(runtime, nextPort, onLine);
}

async function fetchHealth(info) {
  const response = await fetch(`${info.localBaseUrl}/v1/health`, {
    headers: {
      Authorization: `Bearer ${info.token}`,
      Accept: "application/json"
    }
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `Health check failed: ${response.status}`);
  }

  return await response.json();
}

async function waitForHealth(info, onLine) {
  const startedAt = Date.now();
  let lastError = null;
  while (Date.now() - startedAt < 25000) {
    try {
      const health = await fetchHealth(info);
      return health;
    } catch (error) {
      lastError = error;
      onLine?.("正在等待本地节点响应...");
      await new Promise((resolve) => setTimeout(resolve, 1000));
    }
  }
  throw lastError || new Error("Timed out waiting for Finance Node");
}

async function ensureInstalled(onLine) {
  const existing = await loadRuntimeInfo();
  if (existing?.installInfo?.appDir && (await pathExists(existing.installInfo.appDir))) {
    return existing;
  }

  onLine?.("正在安装本地节点服务...");
  const installRoot = defaultInstallRoot();
  await runScript(
    bundledInstaller("install.sh"),
    [],
    {
      FINANCE_NODE_INSTALL_ROOT: installRoot
    },
    (line) => onLine?.(line)
  );
  return await loadRuntimeInfo();
}

async function ensureRunning(onLine) {
  let runtime = await ensureInstalled(onLine);
  try {
    await fetchHealth(runtime);
    return runtime;
  } catch (error) {
    if (isUnauthorizedError(error)) {
      runtime = await relocateRuntimePort(runtime, onLine, "检测到当前端口已有另一套财务节点在运行。");
    } else {
      onLine?.("正在启动本地节点...");
    }
  }

  const appDir = runtime.installInfo.appDir;
  const startScript = isMac()
    ? path.join(appDir, "install_launch_agent.sh")
    : path.join(appDir, "install_and_start_finance_node.sh");

  try {
    await runScript(
      startScript,
      [],
      {
        FINANCE_NODE_INSTALL_DIR: appDir,
        FINANCE_NODE_CONFIG_POINTER: installPointerPath()
      },
      (line) => onLine?.(line)
    );
  } catch (error) {
    if (isAddressInUseError(error)) {
      runtime = await relocateRuntimePort(runtime, onLine, "启动时发现端口冲突。");
      await runScript(
        startScript,
        [],
        {
          FINANCE_NODE_INSTALL_DIR: runtime.installInfo.appDir,
          FINANCE_NODE_CONFIG_POINTER: installPointerPath()
        },
        (line) => onLine?.(line)
      );
    } else {
      throw error;
    }
  }

  await waitForHealth(runtime, onLine);
  return await loadRuntimeInfo();
}

async function bootstrap(onLine) {
  const runtime = await ensureRunning(onLine);
  await waitForHealth(runtime, onLine);

  return {
    nodeName: runtime.nodeName,
    token: runtime.token,
    port: runtime.port,
    localBaseUrl: runtime.localBaseUrl,
    publicBaseUrl: runtime.publicBaseUrl,
    dashboardUrl: `${runtime.localBaseUrl}/dashboard?token=${encodeURIComponent(runtime.token)}`,
    pointerPath: runtime.installInfo.pointerPath,
    installRoot: runtime.installInfo.installRoot,
    appDir: runtime.installInfo.appDir,
    configPath: runtime.installInfo.configPath,
    connectionInfoPath: runtime.connectionInfoPath
  };
}

async function bindAgent(agentName, onLine) {
  const cleaned = String(agentName || "").trim();
  if (!/^[a-zA-Z0-9_-]+$/.test(cleaned)) {
    throw new Error("Agent 名称只能包含字母、数字、下划线和短横线。");
  }

  onLine?.(`正在绑定 OpenClaw agent: ${cleaned}`);
  await runScript(bundledInstaller("install-openclaw.sh"), ["--agent", cleaned], {}, (line) => onLine?.(line));

  const workspaceDir = path.join(os.homedir(), ".openclaw", `workspace-${cleaned}`);
  return {
    agentName: cleaned,
    workspaceDir,
    skillPath: path.join(workspaceDir, "skills", "finance-node-bookkeeper", "SKILL.md"),
    guidePath: path.join(workspaceDir, "docs", "finance-node-bookkeeping-guide.md")
  };
}

function emitLog(message) {
  mainWindow?.webContents.send("bootstrap-log", message);
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1480,
    height: 960,
    minWidth: 1180,
    minHeight: 760,
    title: APP_NAME,
    backgroundColor: "#0f1115",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  mainWindow.loadFile(path.join(__dirname, "renderer", "index.html"));
}

ipcMain.handle("desktop:bootstrap", async () => {
  emitLog("正在准备 Finance Node...");
  return await bootstrap((line) => emitLog(line));
});

ipcMain.handle("desktop:refresh", async () => {
  const runtime = await loadRuntimeInfo();
  if (!runtime) {
    throw new Error("未发现安装信息，请先执行初始化。");
  }
  await waitForHealth(runtime, (line) => emitLog(line));
  return {
    nodeName: runtime.nodeName,
    token: runtime.token,
    localBaseUrl: runtime.localBaseUrl,
    publicBaseUrl: runtime.publicBaseUrl,
    dashboardUrl: `${runtime.localBaseUrl}/dashboard?token=${encodeURIComponent(runtime.token)}`,
    pointerPath: runtime.installInfo.pointerPath,
    installRoot: runtime.installInfo.installRoot,
    appDir: runtime.installInfo.appDir,
    configPath: runtime.installInfo.configPath,
    connectionInfoPath: runtime.connectionInfoPath
  };
});

ipcMain.handle("desktop:bind-agent", async (_event, agentName) => {
  return await bindAgent(agentName, (line) => emitLog(line));
});

ipcMain.handle("desktop:open-external", async (_event, url) => {
  await shell.openExternal(url);
  return true;
});

app.whenReady().then(() => {
  createWindow();
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (!isMac()) {
    app.quit();
  }
});
