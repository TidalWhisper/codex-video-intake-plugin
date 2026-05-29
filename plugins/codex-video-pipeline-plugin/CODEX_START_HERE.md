# CODEX_START_HERE.md

> 这是本插件给 Codex CLI 的总入口文档。后续本地开发、接入 GPT Image 2、接入 ComfyUI、接入 LTX I2V、接入 IndexTTS2、接入真实 FFmpeg 合成，都必须从这里开始读。

## 0. 给 Codex CLI 的第一条指令

在本地 Codex CLI 中，不要直接说“帮我接入 ComfyUI”。请把下面这一段复制给 Codex：

```text
你现在接手 codex-video-intake-plugin。请先读取并理解以下入口文档，不要立刻修改代码：

1. CODEX_START_HERE.md
2. docs/00_CODEX_MASTER_PLAN.md
3. docs/CURRENT_PROVIDER_STATUS.md
4. docs/DEVELOPMENT_PLAN_COMFYUI_AND_OPENAI_IMAGE.md
5. docs/PROVIDER_INTEGRATION_CONTRACTS.md
6. docs/COMFYUI_WORKFLOW_EXPORT_GUIDE.md
7. docs/CODEX_LOCAL_TASK_RUNBOOK.md

读完后，先输出：
- 当前插件已经完成到哪个阶段
- 哪些功能只是框架/placeholder
- 哪些功能还没有真实接入
- 下一步你准备改哪些文件
- 你准备执行哪些测试

在我确认之前，不要修改代码。
```

## 1. 当前插件定位

这个插件当前是：

```text
Codex CLI 专用的视频生产流水线插件
+ Stage 00-09 完整流程框架
+ 状态机
+ 每阶段 manifest / validator
+ provider 配置与健康检查
+ OpenAI GPT Image 2 / ComfyUI txt2img / LTX I2V / IndexTTS2 / Music runners
+ Stage 05-09 provider-backed 自动化测试链路
```

它当前还不是：

```text
已经在任意机器上零配置即可跑通的生产插件
仓库内自带真实可运行 ComfyUI workflow_api.json 的插件
已经完成本机 OpenAI / ComfyUI / FFmpeg 真实环境最终验收的插件
已经沉淀稳定真实项目样例并提交为仓库基线的插件
```

## 2. 当前已经完成的 Stage

```text
Stage 00：用户基础需求确认 / Brief 锁定
Stage 01：剧本生成
Stage 02：分镜脚本生成
Stage 03：人物画像 / Character Bible
Stage 04：关键帧提示词 + 过渡动作提示词
Stage 05：关键帧图片生成框架
Stage 06：视频片段生成框架
Stage 07：配音与背景音乐框架
Stage 08：粗剪合成框架
Stage 09：质量检查与交付框架
```

注意：Stage 05-09 已经有 manifest、validator、placeholder 测试，但真实 provider 还要继续接入。
注意：当前代码已经包含真实 provider runner，并有 provider-backed 自动化测试；尚未完全闭环的是本机真实环境配置、workflow 导出和最小真实 E2E 验证。

## 3. 用户正常使用入口

用户正常使用时，只应该启动：

```text
$video-production-pipeline
```

不要让用户一个阶段一个阶段手动调用：

```text
$video-project-intake
$video-script-generation
$video-storyboard-generation
$video-character-bible
$video-keyframe-prompts
$video-keyframe-images
$video-video-clips
$video-audio
$video-assembly
$video-qa-delivery
```

这些子 skill 只用于调试、恢复、单阶段重跑。

## 4. 后续本地开发总路线

后续开发按这个顺序做，不要跳步：

```text
Phase 1：补齐 provider 配置读取与健康检查
Phase 2：接入 GPT Image 2 / OpenAI Images API 作为 Stage 05 首选出图 provider
Phase 3：接入 ComfyUI 核心客户端
Phase 4：接入 ComfyUI txt2img 作为 Stage 05 fallback
Phase 5：接入 ComfyUI LTX I2V 作为 Stage 06 视频片段 provider
Phase 6：接入 IndexTTS2 / ComfyUI 音频工作流作为 Stage 07 provider
Phase 7：强化 Stage 08 真实 FFmpeg 合成
Phase 8：强化 Stage 09 QA 与交付验收
Phase 9：补齐失败恢复、重试、provider fallback、端到端测试
```

## 5. 关键硬规则

Codex 后续修改时必须遵守：

```text
1. 不允许口头说“已生成”，必须有真实文件证据。
2. 不允许跳过 manifest，所有生成结果必须写回对应 manifest。
3. 不允许跳过 validator，进入下一阶段前必须 final 校验通过。
4. 不允许把 A 项目的资源写进 B 项目目录。
5. 不允许绕过 project_manifest.json 的 current_stage / allowed_next_stage。
6. 不允许把 provider placeholder 当成真实 provider。
7. 不允许在没有工作流 JSON 的情况下声称 ComfyUI 已接入完成。
8. 不允许在没有 API client、配置项、测试和真实输出证据的情况下声称 GPT Image 2 已接入完成。
```

## 6. 本地开发前先跑自检

Windows CMD：

```cmd
cd /d E:\Codex-Plugin\codex-video-intake-plugin
run_all_tests.cmd
```

如果失败，先修测试，不要继续接 provider。

## 7. 后续让 Codex 执行的主任务文件

主任务从这里开始：

```text
prompts/codex/00-master-task-comfyui-openai-image.md
```

然后按顺序执行：

```text
01-implement-openai-image2-provider.md
02-implement-comfyui-core-client.md
03-integrate-stage05-keyframe-images.md
04-integrate-stage06-ltx-i2v.md
05-integrate-stage07-indextts2-music.md
06-hardening-tests.md
```

## 8. 每轮 Codex 修改后的交付格式

每轮 Codex 修改结束后，必须输出：

```text
1. 本轮目标
2. 修改文件清单
3. 新增文件清单
4. 删除文件清单
5. 已执行测试命令
6. 测试结果
7. 是否有真实输出文件证据
8. 当前 project_manifest / stage 状态变化
9. 下一步建议
10. 未完成项 / 风险
```

## 9. 当前最重要的下一步

当前最应该做的是：

```text
先核对并整理 provider 已接入代码、测试和文档的一致性。
再基于本机真实 workflow / providers.yaml / node mapping 做 Stage 05-09 最小真实冒烟验证。
```

不要跳过本机前置检查。先跑 provider health、local prereqs 和最小真实项目，再继续做增强或扩展。
