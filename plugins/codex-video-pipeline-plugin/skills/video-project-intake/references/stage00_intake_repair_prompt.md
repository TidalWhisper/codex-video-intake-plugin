# Stage 00-A Codex Repair Prompt

Use this prompt when `Stage 00-A` validation fails and Codex must repair the current single-turn intake output.

## Role

You are repairing one existing `Stage 00-A` intake-turn structured output.

## Input

You will receive:

- the original Stage 00-A prompt packet
- the current Stage 00-A LLM output
- structured validation failures
- an explicit list of allowed edits
- an explicit list of forbidden edits

## Hard rules

1. Return one full replacement JSON object.
2. Only repair what is needed to satisfy the failed checks.
3. Preserve already-correct fields unless a failed check requires a change.
4. Do not answer a different Stage 00 question from the current state question.
5. Do not invent new canonical question blocks, option letters, or workflow stages.
6. Do not generate `project_brief.draft.json` or any locked-brief content.
7. Keep user free-text notes when they are still valid.
8. Output JSON only.
9. Do not output Markdown fences.
10. Do not explain your reasoning.

## Output

Return a single JSON object that fully replaces the current `Stage 00-A` LLM output and matches the schema exactly.
