# codex-video-intake-plugin

当前包版本：1.1.3

## 重要：目录结构已经修正

这一版外层目录是安装包 / 本地 marketplace wrapper，真正的插件本体放在：

```text
codex-video-intake-plugin/
├─ .agents/plugins/marketplace.json
├─ plugins/
│  └─ codex-video-pipeline-plugin/     ← 真正的 Codex plugin
│     ├─ .codex-plugin/plugin.json
│     ├─ skills/
│     ├─ docs/
│     ├─ config/
│     └─ workflows/
├─ CODEX_START_HERE.md
├─ install_personal_plugin.cmd
├─ verify_package.cmd
└─ run_all_tests.cmd
```

已经移除旧版容易混淆的：

```text
plugins/codex-video-intake-plugin/
```

## 安装

Windows CMD：

```cmd
cd /d E:\Codex-Plugin\codex-video-intake-plugin
install_personal_plugin.cmd
```

然后关闭所有 Codex CLI 窗口，重新打开：

```cmd
codex
```

在 Codex 里打开：

```text
/plugins
```

找到并安装/启用：

```text
Codex Video Pipeline
```

正常入口：

```text
$video-production-pipeline
```

## 后续本地开发

让 Codex CLI 先读：

```text
CODEX_START_HERE.md
.codex/current-task-contract.md
```
