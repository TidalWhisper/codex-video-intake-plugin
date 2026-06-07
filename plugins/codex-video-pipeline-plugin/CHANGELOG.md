# CHANGELOG

## 1.1.4

- 删除历史计划、状态、反馈类文档，入口文档改为指向仓库级 `.codex/current-task-contract.md`。
- 收紧本地开发与测试规则，避免继续依赖过期计划口径。

## 1.1.2

- Added root-level `CODEX_START_HERE.md` as the master entry document for local Codex CLI follow-up development.
- Added plugin-level entry and roadmap materials for local Codex CLI follow-up development.
- Added `prompts/codex/README_START_HERE.md` to prevent Codex from starting from scattered task files.
- Updated self-test required file list to check the master entry documents.

## 1.1.2

- Added detailed development plan for OpenAI GPT Image 2 and ComfyUI provider integration.
- Added current provider status document clarifying GPT Image 2 and ComfyUI are not yet implemented as real calls.
- Added Codex CLI task prompts for staged local implementation.
- Added ComfyUI workflow export guide.
- Added provider config and workflow node mapping examples.
- Added root-level `run_all_tests.cmd` and `run_all_tests.py`.

## 1.0.0

- Completed Stage 00-09 pipeline framework through QA and delivery.
*** Add File: E:\Codex-Plugin\codex-video-intake-plugin\.codex\current-task-contract.md
# 当前任务契约

## 仓库定位

- 仓库根目录：`E:\Codex-Plugin\codex-video-intake-plugin`
- 真实插件本体：`plugins/codex-video-pipeline-plugin/`
- 唯一官方用户入口：`$video-production-pipeline`

## 当前总目标

把 `Stage00-Stage09` 改造成：

```text
Codex 主导语义与决策
Python 仅机械执行
```

## 当前批次

- 批次：`1`
- 名称：`清空旧体系并建立新契约`
- 目标：
  - 删除历史计划、进度、反馈类文档
  - 清理入口文档和入口校验中的旧引用
  - 建立新的仓库级任务契约与监督审计日志

## 当前硬规则

1. 不再读取或引用已删除的历史 codex-first 计划、进度文档或试跑反馈。
2. 主实施者不做任何测试。
3. 唯一允许的测试由监督者 Agent 执行，且必须从 `$video-production-pipeline` 入口开始。
4. Python 只允许做：
   - schema 校验
   - 路径解析
   - 固定模板写入
   - manifest 同步
   - provider 调用
   - workflow 字段注入
5. Python 不允许做：
   - 语义生成
   - 路线选择
   - fallback 决策
   - 修复决策
   - prompt 主体内容生成或改写

## 当前批次允许改动范围

- `CODEX_START_HERE.md`
- `README_快速开始.md`
- `verify_package.cmd`
- `CHANGELOG.md`
- `plugins/codex-video-pipeline-plugin/CODEX_START_HERE.md`
- `plugins/codex-video-pipeline-plugin/README_快速开始.md`
- `plugins/codex-video-pipeline-plugin/verify_package.cmd`
- `plugins/codex-video-pipeline-plugin/CHANGELOG.md`
- `plugins/codex-video-pipeline-plugin/prompts/**/README*.md`
- `plugins/codex-video-pipeline-plugin/prompts/codex/00-master-task-comfyui-openai-image.md`
- `plugins/codex-video-pipeline-plugin/workflows/**/README*.md`
- `plugins/codex-video-pipeline-plugin/run_all_tests.py`
- `plugins/codex-video-pipeline-plugin/docs/**`
- `.codex/**`

## 当前批次禁止改动范围

- `plugins/codex-video-pipeline-plugin/scripts/**`
- `plugins/codex-video-pipeline-plugin/skills/**`
- `plugins/codex-video-pipeline-plugin/tests/**`
- 任何 stage 业务实现脚本
- 任何 provider / workflow 运行逻辑

## 批次通过门

本批次只有在监督者 Agent 完成以下事项后才算通过：

1. 实施后审计通过
2. 从 `$video-production-pipeline` 入口执行唯一业务流程测试
3. 测试结果明确给出：
   - `entry_test_expected_terminal_stage`
   - `entry_test_actual_terminal_stage`
   - `entry_test_result`

没有监督者的 `PASS`，本批次一律视为未完成。
