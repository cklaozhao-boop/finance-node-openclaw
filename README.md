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

先克隆仓库，然后执行：

```bash
bash ./installer/install.sh
```

安装完成后会输出：

- 本机地址
- Tailscale 地址
- Web 工作台地址
- Token 所在文件

## 绑定到 OpenClaw agent

选择你要绑定的 agent：

```bash
bash ./installer/install-openclaw.sh --agent <agent-name>
```

安装器会把通用记账 skill 安装到：

```text
~/.openclaw/workspace-<agent>/skills/finance-node-bookkeeper
```

并生成对应的使用说明。

## 一键安装发布

如果你把仓库发布到 GitHub，其他人可以直接：

```bash
curl -fsSL https://raw.githubusercontent.com/<github-username>/finance-node-openclaw/main/installer/install.sh | bash
```

然后按需绑定 agent：

```bash
curl -fsSL https://raw.githubusercontent.com/<github-username>/finance-node-openclaw/main/installer/install-openclaw.sh | bash -s -- --agent <agent-name>
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

## 文档

- 发布说明：[docs/PUBLISHING.md](docs/PUBLISHING.md)
- 服务说明：[service/README.md](service/README.md)
