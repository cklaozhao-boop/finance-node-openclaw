# Finance Node Service

这是 `finance-node-openclaw` 的服务端实现目录。

目标：

- 本地启动 `Finance Node`
- 提供 Web 财务工作台
- 给 OpenClaw 提供统一账本 API

## 1. 直接本地启动

在当前目录执行：

```bash
chmod +x ./install_and_start_finance_node.sh
./install_and_start_finance_node.sh
```

执行后会自动完成：

- 生成本地配置
- 生成访问 Token
- 创建 SQLite 数据库
- 后台启动财务节点
- 生成 `runtime/connection-info.txt`
- 生成 `runtime/openclaw_finance_tools.json`

## 2. 停止与查看状态

```bash
./status_finance_node.sh
./stop_finance_node.sh
```

## 3. 给手机浏览器使用

如果你的手机和节点机器都在同一个 Tailscale 网络下，可以直接在手机浏览器里打开：

- `http://你的节点地址:31888/dashboard`

首次打开时输入 `runtime/connection-info.txt` 里的 Token，后续会缓存在当前浏览器。

当前网页支持：

- 按月份查看账单
- 搜索标题、分类、商户、标签、备注
- 查看收入、支出、结余、待报销汇总
- 查看分类支出占比
- 查看最近流水明细
- 查看统一资产看板与账户分布

## 4. 给 OpenClaw 使用

看这两个文件：

- `openclaw/finance_write_skill.md`
- `runtime/openclaw_finance_tools.json`

建议做法：

- 把 `finance_write_skill.md` 作为财务记账 Agent 的行为说明
- 把 `openclaw_finance_tools.json` 作为 HTTP 工具定义

## 5. 当前接口

- `GET /v1/health`
- `GET /v1/transactions`
- `POST /v1/transactions`
- `PATCH /v1/transactions/{id}/reimbursement`
- `GET /v1/summary/month`
- `GET /v1/configuration`
- `GET /v1/dashboard/overview`

## 6. 当前限制

这是一个可演示、可联通的原型节点，不是生产版。

当前未做：

- 复杂权限管理
- 多用户
- HTTPS
- 完整审计
- 真正的 OpenClaw 自动注册

但它已经足够用来打通：

`OpenClaw -> Finance Node -> Web Dashboard`
