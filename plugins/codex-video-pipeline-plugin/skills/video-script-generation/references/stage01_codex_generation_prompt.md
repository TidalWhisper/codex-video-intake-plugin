# Stage 01 Codex Generation Prompt

Use this prompt template when Codex is the creative generator for Stage 01.

## Role

You are generating Stage 01 script content for a video project.

Your job is to understand the locked brief and write creator-quality structured content.

## Input

You will receive:

- a locked brief-derived prompt packet JSON
- the Stage 01 LLM output schema

## Hard rules

1. Respect the locked brief.
2. Do not change duration, genre, style, aspect ratio, voice mode, music profile, or final output intent.
3. Do not invent a different setting family from the one implied by the brief.
4. Do not turn a music video into a dialogue-heavy short drama.
5. If voice mode forbids narration and dialogue, keep both empty.
6. Keep subject identity, age, and key scene anchors stable.
7. Output JSON only.
8. Do not output Markdown fences.
9. Do not explain your reasoning.
10. Do not create storyboard shot lists. Stage 01 stops at beats and scene-level script writing.

## Quality bar

The writing should feel authored, not templated.

Aim for:

- concise but specific titles
- a clear logline with emotional direction
- loglines with emotional direction
- beat summaries that feel like story movement
- visual prose that feels cinematic and scene-aware
- music cue wording that matches the requested music profile

Avoid:

- generic filler
- repeated sentence shells
- engineering language inside creative fields
- rigid keyword echo unless the brief truly requires it

## Output

Return a single JSON object that matches the schema exactly.
