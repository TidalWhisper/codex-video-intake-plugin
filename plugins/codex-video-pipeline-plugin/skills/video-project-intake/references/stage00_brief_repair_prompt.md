你正在修复 `Stage 00-B` 的 draft brief structured output。

目标：

- 根据 repair packet 中的 failed checks
- 返回一个完整替换版 JSON
- 通过 `project_brief.draft.json` 的最终验证

硬规则：

1. 返回完整 JSON，不要只返回局部 patch。
2. 保留已经正确的字段，除非 failed checks 明确要求改动。
3. 不得改变项目核心创意或重写为另一种题材。
4. 不得把 draft 改成 locked。
5. 只返回一个 JSON 对象，不要输出解释。
