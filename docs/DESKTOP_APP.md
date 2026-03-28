# mac 桌面版说明

## 目标

给不熟悉终端的用户一个可双击使用的 `mac App`：

- 打开应用
- 自动完成本地节点安装
- 自动启动本地服务
- 直接进入 Web 财务工作台
- 可输入 agent 名后一键绑定 OpenClaw

## 当前实现

当前桌面版位于：

```text
desktop-app/
```

技术路线：

- Electron 桌面外壳
- 内嵌现有安装器与服务目录
- 启动时调用：
  - `installer/install.sh`
  - `installer/install-openclaw.sh`
- Web 工作台通过本地 `iframe` 加载：
  - `http://127.0.0.1:31888/dashboard?token=...`

## 本地打包

```bash
cd desktop-app
npm install
npm run pack:mac
```

产物路径：

```text
desktop-app/release/mac-arm64/Finance Node.app
```

如果要进一步生成分发包：

```bash
cd desktop-app
npm run dist:mac
```

这会尝试输出：

- `.dmg`
- `.zip`

## 当前边界

这是第一版桌面启动器，已经能承担“点击即部署”的骨架工作，但还有边界：

1. 目前默认是 `arm64` 本机构建
2. 当前仍依赖宿主机上可用的 `python3`
3. 还没有做 Apple Developer 签名与 notarization
4. 还没有做真正的内置 Python 二进制封装

## 下一步建议

如果要面向普通用户发布，建议继续做：

1. 用 `PyInstaller` 或等效方式把服务端打成独立可执行文件
2. 再由桌面壳应用调用该二进制，而不是调用系统 Python
3. 补签名和 notarization
4. 输出正式 `.dmg`
