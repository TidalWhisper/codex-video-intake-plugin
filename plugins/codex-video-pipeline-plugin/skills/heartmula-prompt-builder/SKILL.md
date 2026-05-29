---
name: heartmula-prompt-builder
description: Build fixed-format HeartMuLa music prompts from a story, a style description, or existing lyrics. Use when Codex needs to prepare inputs for `HeartMuLa_workflow_fixed_importable.json`, convert a free-form music idea into HeartMuLa-compatible `Global Tags + Lyrics`, normalize user lyrics into HeartMuLa structure tags, or enforce the strict HeartMuLa output format before calling the local ComfyUI HeartMuLa workflow.
---

# HeartMuLa Prompt Builder

## Overview

Use this skill to transform free-form user input into a HeartMuLa-compatible prompt with exactly two sections:

- `Global Tags`
- `Lyrics`

Read `references/heartmula-usage-spec.md` first. That file is the source of truth for format, section rules, allowed structure, and forbidden output behavior.

## Fixed Workflow

1. Determine the mode:
   - `story-to-song`: user provides a story, optionally with a desired song style
   - `lyrics-normalization`: user provides lyrics plus a style description

2. Build `Global Tags` first:
   - use English tags
   - keep them comma-separated
   - include high-priority tags for `Genre`, `Gender`, and `Mood`
   - append optional `Instrument`, `Scene`, and `Topic` when supported by the input
   - ensure the line ends with `/`

3. Build `Lyrics` second:
   - write Chinese lyrics
   - preserve or create a full structure with:
     - `Intro`
     - `Verse`
     - `Pre-Chorus`
     - `Chorus`
     - `Bridge`
     - `Outro`
   - merge structure and style as `[Structure: English style description]`
   - keep the style description in English

4. Enforce strict output:
   - output only `Global Tags` and `Lyrics`
   - do not add any explanation, greeting, or confirmation text
   - do not retell the story outside the lyrics
   - do not emit a plain one-line `music_prompt`

## Output Contract

Always return exactly this shape:

```text
Global Tags: ...
Lyrics:
[Intro: ...]
...
```

If any required structure is missing from the user input, insert it.

If the user provides only a story, convert it into song-ready material without explaining the story back to the user.

If the user provides lyrics that are unstructured, normalize them into HeartMuLa section blocks.

## Stage 07 Use

When the pipeline selects `HeartMuLa_workflow_fixed_importable.json` for Stage 07 music generation:

- use this skill before constructing the workflow payload
- map the final `Global Tags` body into the workflow `tags` field
- map the final `Lyrics` body into the workflow `lyrics` field
- do not collapse them into a single sentence prompt

## Reference

Read:

- `references/heartmula-usage-spec.md`
