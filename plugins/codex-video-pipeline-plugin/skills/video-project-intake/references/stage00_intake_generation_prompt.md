你正在处理 `Stage 00-A` 的单轮 intake 理解任务。

目标：

- 只理解当前这一轮用户回复
- 只更新当前 Stage 00 intake state
- 不要生成 `project_brief.draft.json`
- 不要锁定 brief

硬规则：

1. 只能处理当前问题，除非用户明确在本轮同时修正了某个已填写答案。
2. `next_prompt_text` 必须是 canonical block：
   - 如果继续提问，必须等于下一个问题的完整 canonical 文本
   - 如果当前问题信息不足，需要追问或重复，必须继续输出当前问题的完整 canonical 文本
   - 如果 9 个问题都已满足，必须输出 canonical `Final Confirmation` block
3. 不得改写 option letters，不得自创菜单。
4. 保留用户的自由文本备注，不要丢失短句补充。
5. `user_answers_patch` 只写本轮实际确定的字段。
6. `normalized_patch` 只写本轮实际归一化成功的字段。
7. 如果当前问题仍不充分：
   - `needs_followup = true`
   - `status = collecting`
   - `next_question_key` 保持当前问题
8. 如果 9 项都已齐备：
   - `required_fields_complete = true`
   - `status = draft_ready`
   - `next_question_key = ""`

只返回一个 JSON 对象，不要输出任何解释。
