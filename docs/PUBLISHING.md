# 发布说明

## 目标仓库

- 仓库名：`finance-node-openclaw`
- 推荐公开发布：`public`

## 推荐发布流程

1. 在 GitHub 创建公开仓库 `finance-node-openclaw`
2. 把当前目录推送到该仓库
3. 检查这两个入口是否可直接通过 Raw URL 下载：
   - `installer/install.sh`
   - `installer/install-openclaw.sh`
4. 在 README 中把 `<github-username>` 替换成你的真实 GitHub 用户名

## 用户安装方式

### 安装节点服务

```bash
curl -fsSL https://raw.githubusercontent.com/<github-username>/finance-node-openclaw/main/installer/install.sh | bash
```

### 绑定 OpenClaw agent

```bash
curl -fsSL https://raw.githubusercontent.com/<github-username>/finance-node-openclaw/main/installer/install-openclaw.sh | bash -s -- --agent <agent-name>
```

## 版本更新建议

- 变更 Web 资源后，重新提交 `service/web`
- 变更服务逻辑后，重新提交 `service/*.py` 与 `service/*.sh`
- 变更 OpenClaw skill 后，更新 `openclaw/templates`

## 脱敏边界

当前仓库不应提交：

- 任何真实 token
- 任何真实 Tailscale 域名
- 任何个人机器绝对路径
- `runtime/`
- `logs/`

## 调试安装器

只验证安装目录落盘，不自动注册后台服务：

```bash
FINANCE_NODE_SKIP_AUTOSTART=1 bash ./installer/install.sh
```
