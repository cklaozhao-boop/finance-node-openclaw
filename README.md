# finance-node-openclaw

一个面向 OpenClaw 的本地财务节点服务。

它提供三部分能力：

- 本地 `Finance Node` API 服务
- 可通过 Tailscale 访问的 Web 财务工作台
- 可绑定到任意 OpenClaw agent 的记账 skill

## 特性

- 本地 SQLite 存储
- 自生成访问 Token
- Web 工作台
- Tailscale 远程访问
- macOS `launchd` 常驻
- Linux `systemd --user` 常驻
- OpenClaw 按 agent 选择性绑定

## 快速安装

本地仓库安装：

```bash
bash ./installer/install.sh
```

一键安装：

```bash
curl -fsSL https://raw.githubusercontent.com/cklaozhao-boop/finance-node-openclaw/main/installer/install.sh | bash
```

安装完成后会输出：

- 本机地址
- Tailscale 地址
- Web 工作台地址
- Token 所在文件

## 绑定到 OpenClaw agent

选择你要绑定的 agent：

```bash
bash ./installer/install-openclaw.sh --agent hubu
```

一键绑定：

```bash
curl -fsSL https://raw.githubusercontent.com/cklaozhao-boop/finance-node-openclaw/main/installer/install-openclaw.sh | bash -s -- --agent hubu
```

注意：

- `hubu` 只是示例名字
- 这里要替换成你的真实 agent 名称
- 不要把 `<agent-name>` 这类尖括号原样输入到终端

安装器会把通用记账 skill 安装到：

```text
~/.openclaw/workspace-<agent>/skills/finance-node-bookkeeper
```

并生成对应的使用说明。

## mac 桌面版

仓库内现在包含一个 Electron 版 macOS 启动器，目标是让新手用户通过双击应用完成：

- 本地安装 `Finance Node`
- 自动启动本地服务
- 直接打开 Web 工作台
- 一键绑定 OpenClaw agent

桌面启动器源码在：

```text
desktop-app/
```

本地构建：

```bash
cd desktop-app
npm install
npm run pack:mac
```

打包完成后，会得到：

```text
desktop-app/release/mac-arm64/Finance Node.app
```

当前桌面版会复用本仓库现有的安装器：

- `installer/install.sh`
- `installer/install-openclaw.sh`

也就是说，桌面版不是单独维护第二套逻辑，而是把“点击即安装/启动/绑定”的体验包在一个 mac App 里。

注意：

- 这是桌面启动器第一版
- 当前仍然依赖用户机器上可用的 `bash` 与 `python3`
- 如果要做到真正零依赖分发，下一步要把 Python 服务端再打成独立二进制

## 安装后怎么用

服务安装完成后，安装器会打印：

- 节点名称
- 本机地址
- Tailscale 地址
- Web 工作台地址
- Token

你也可以随时查看：

```bash
cat "${XDG_CONFIG_HOME:-$HOME/.config}/finance-node-openclaw/install.json"
cat "${HOME}/Library/Application Support/finance-node-openclaw/app/runtime/connection-info.txt"
```

典型使用方式：

1. 在浏览器打开安装器输出的 Web 工作台地址
2. 首次输入 Token
3. 绑定一个 OpenClaw agent
4. 对该 agent 发送结构化记账指令

示例：

```text
请记一笔支出：今天午饭 32 元，账户生活账户，项目生活必要支出，类别外卖饮食，时间今天 12:30，备注工作日午餐。
```

```text
请记一笔收入：小红书回款 2300 元，入账到经营账户，资金来源小红书，时间现在，备注 3 月回款。
```

```text
请记一笔内部转账：从经营账户转 2000 元到生活账户，时间现在，备注本月生活补充。
```

## 一键安装发布

如果你把仓库发布到 GitHub，其他人可以直接：

```bash
curl -fsSL https://raw.githubusercontent.com/cklaozhao-boop/finance-node-openclaw/main/installer/install.sh | bash
```

然后按需绑定 agent：

```bash
curl -fsSL https://raw.githubusercontent.com/cklaozhao-boop/finance-node-openclaw/main/installer/install-openclaw.sh | bash -s -- --agent hubu
```

## 安装后的默认目录

macOS:

```text
~/Library/Application Support/finance-node-openclaw/app
```

Linux:

```text
${XDG_DATA_HOME:-~/.local/share}/finance-node-openclaw/app
```

公共安装信息指针：

```text
${XDG_CONFIG_HOME:-~/.config}/finance-node-openclaw/install.json
```

## 卸载

如果只是测试安装，手动删除以下内容即可。

macOS:

```bash
launchctl bootout "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.finance-node-openclaw.plist" 2>/dev/null || true
rm -f "$HOME/Library/LaunchAgents/com.finance-node-openclaw.plist"
rm -rf "$HOME/Library/Application Support/finance-node-openclaw"
rm -rf "${XDG_CONFIG_HOME:-$HOME/.config}/finance-node-openclaw"
```

如果已经绑定了 OpenClaw agent，还可以按需删除：

```bash
rm -rf "$HOME/.openclaw/workspace-<agent>/skills/finance-node-bookkeeper"
rm -f "$HOME/.openclaw/workspace-<agent>/docs/finance-node-bookkeeping-guide.md"
```

## 常见问题

### `command not found: compdef`

这是你本地 `openclaw.zsh` 补全脚本的提示，和本仓库安装器无关，可以先忽略。

### `Address already in use`

说明 `31888` 端口已经被另一套节点占用了。先停掉旧服务，再启动新的 `finance-node-openclaw`。

### `bash: BASH_SOURCE[0]: unbound variable`

这个历史问题已经修复。当前 `curl | bash` 安装方式已兼容 GitHub Raw 下载执行。

## 文档

- 使用说明：[docs/USAGE.md](docs/USAGE.md)
- 桌面版说明：[docs/DESKTOP_APP.md](docs/DESKTOP_APP.md)
- 发布说明：[docs/PUBLISHING.md](docs/PUBLISHING.md)
- 服务说明：[service/README.md](service/README.md)
