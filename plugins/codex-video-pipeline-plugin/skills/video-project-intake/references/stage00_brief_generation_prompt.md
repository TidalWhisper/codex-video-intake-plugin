你正在处理 `Stage 00-B` 的 brief 汇总任务。

目标：

- 基于已经完成的 `Stage 00-A` intake state
- 产出一个完整、可写盘的 `Stage 00 draft brief structured output`
- 供后续 writer 写成 `project_brief.draft.json`

硬规则：

1. 这是 `draft brief`，不是 locked brief。
2. 不得把 `confirmed_by_user` 设成 true，也不得暗示已经锁定。
3. 不得发明新的故事设定来替换 intake 中已经确认的内容。
4. `normalized` 必须完整，且与 intake state 已经确定的值保持稳定。
5. `required_fields_complete` 应与当前 intake 完成状态一致。
6. `missing_required_fields` 应与当前 intake 完成状态一致。
7. `brief_confirmation_summary` 必须是面向用户确认的 9 项摘要，中文表达清楚，不要工程腔。
8. 只返回一个 JSON 对象，不要输出解释。
