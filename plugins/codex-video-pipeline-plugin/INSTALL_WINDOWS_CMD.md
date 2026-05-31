# Windows CMD 安装说明

解压后目录示例：

```cmd
E:\Codex-Plugin\codex-video-intake-plugin
```

安装：

```cmd
cd /d E:\Codex-Plugin\codex-video-intake-plugin
install_personal_plugin.cmd
```

关闭所有 Codex CLI 窗口，重新打开：

```cmd
codex
```

进入：

```text
/plugins
```

安装或启用：

```text
Codex Video Intake
```

推荐测试：

```text
$video-production-pipeline
```

不要在正常流程里手动调用 `$video-script-generation` 或 `$video-storyboard-generation`；总控 pipeline 会在用户确认后自动继续。

如果你只是想看“当前项目卡在哪、下一步该打开什么”，运行：

```cmd
python skills\video-production-pipeline\scripts\show_creator_home.py
```

这个入口会自动把你带到最新项目的创作者主页，而不是先让你读 manifest。
