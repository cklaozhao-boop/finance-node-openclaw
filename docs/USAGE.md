# 使用说明

## 1. 安装节点服务

```bash
curl -fsSL https://raw.githubusercontent.com/cklaozhao-boop/finance-node-openclaw/main/installer/install.sh | bash
```

安装完成后，终端会输出：

- 节点名称
- 本机地址
- Tailscale 地址
- Web 工作台地址
- Token

## 2. 绑定 OpenClaw agent

把 `hubu` 替换成你自己的 agent 名称：

```bash
curl -fsSL https://raw.githubusercontent.com/cklaozhao-boop/finance-node-openclaw/main/installer/install-openclaw.sh | bash -s -- --agent hubu
```

绑定完成后，skill 会安装到：

```text
~/.openclaw/workspace-hubu/skills/finance-node-bookkeeper
```

## 3. 打开 Web 工作台

使用安装器打印出来的地址，或查看：

```bash
cat "${HOME}/Library/Application Support/finance-node-openclaw/app/runtime/connection-info.txt"
```

首次打开工作台后，输入 Token 即可。

## 4. 如何给 agent 发送记账指令

### 支出

```text
请记一笔支出：今天午饭 32 元，账户生活账户，项目生活必要支出，类别外卖饮食，时间今天 12:30，备注工作日午餐。
```

### 收入

```text
请记一笔收入：小红书回款 2300 元，入账到经营账户，资金来源小红书，时间现在，备注 3 月回款。
```

### 内部转账

```text
请记一笔内部转账：从经营账户转 2000 元到生活账户，时间现在，备注本月生活补充。
```

## 5. 卸载

### 删除服务

```bash
launchctl bootout "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.finance-node-openclaw.plist" 2>/dev/null || true
rm -f "$HOME/Library/LaunchAgents/com.finance-node-openclaw.plist"
rm -rf "$HOME/Library/Application Support/finance-node-openclaw"
rm -rf "${XDG_CONFIG_HOME:-$HOME/.config}/finance-node-openclaw"
```

### 删除 agent 绑定

```bash
rm -rf "$HOME/.openclaw/workspace-<agent>/skills/finance-node-bookkeeper"
rm -f "$HOME/.openclaw/workspace-<agent>/docs/finance-node-bookkeeping-guide.md"
```

## 6. 常见问题

### 为什么安装成功了，但新节点没有接管端口？

因为旧节点还在占用 `31888`。先停掉旧服务，再启动新安装的节点。

### 为什么会出现 `compdef` 报错？

这是本地 zsh 补全脚本问题，不影响安装器执行。

### 可以安装到 Linux 吗？

可以。服务安装器支持 Linux 的 `systemd --user` 常驻模式；但 Web 工作台和 OpenClaw 绑定方式与 macOS 基本一致。
