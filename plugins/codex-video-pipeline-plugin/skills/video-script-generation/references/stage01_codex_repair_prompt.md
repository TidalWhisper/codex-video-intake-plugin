# Stage 01 Codex Repair Prompt

Use this prompt template when Stage 01 validation fails and Codex needs to repair the draft.

## Role

You are repairing an existing Stage 01 script draft.

## Input

You will receive:

- the locked brief-derived repair packet
- the current draft
- structured validation failures
- an explicit list of allowed edits
- an explicit list of forbidden edits

## Hard rules

1. Only repair the requested fields.
2. Do not rewrite the entire draft unless the repair packet explicitly allows it.
3. Preserve unchanged good content.
4. Respect the locked brief.
5. Do not introduce new voiceover or dialogue when the brief forbids it.
6. Keep music cues consistent with the requested music profile.
7. Keep subject identity and setting anchors stable.
8. Output JSON only.
9. Do not output Markdown fences.
10. Do not explain your reasoning.

## Repair strategy

- If the error is field-local, return only the corrected field payload.
- If the error is beat-local, return only the corrected beat payload.
- If the error is global and the packet allows broader edits, rewrite only the minimum required scope.

## Output

Return a single JSON object containing only the repaired fields or repaired beats requested by the repair packet.

