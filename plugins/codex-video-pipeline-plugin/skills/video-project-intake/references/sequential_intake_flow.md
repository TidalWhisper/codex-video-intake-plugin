# Sequential Stage 00 Intake Flow

This plugin must ask the first-layer required intake questions one at a time.

## Why

A long 9-item form is unfriendly in Codex CLI. The expected UX is a guided wizard:

1. Ask one question.
2. Let the user choose.
3. Store the answer.
4. Ask the next question.
5. After question 9, summarize and ask for confirmation.

## Hard rules

- Never print all 9 questions in the first message.
- Never ask more than one intake question per assistant turn.
- Never start script generation during Stage 00.
- Never lock a project without explicit user confirmation.

## Progress format

Use:

```text
进度：第 X / 9 项
```

## Final confirmation

After all 9 answers are collected, show the summary and ask:

```text
A. 确认，锁定需求并允许进入剧本生成
B. 修改某一项
C. 重新填写
```
