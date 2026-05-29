---
name: acestep-prompt-builder
description: Build high-quality AceStep music prompts for `AceStep_Music_Workflow.json` and `TextEncodeAceStepAudio1.5`. Use when Codex needs to turn a story idea, music brief, or draft lyrics into AceStep-compatible `tags + lyrics + bpm/language/keyscale/timesignature`, enforce the official AceStep lyric-section conventions, or prepare Stage 07 music inputs for the default AceStep workflow.
---

# AceStep Prompt Builder

Read `references/acestep-official-notes.md` first. That file is the source of truth distilled from the official ACE-Step 1.5 docs and the official ComfyUI node docs.

## Fixed workflow

1. Determine the mode:
   - `story-to-song`: user provides a story, scene, or music brief and the target profile is `song`
   - `instrumental-score`: user needs pure instrumental generation with no vocals
   - `underscore-score`: user needs background underscore that supports picture or narration
   - `lyrics-polish`: user provides draft lyrics that need structure and production direction

2. Build `tags` first:
   - treat `tags` as a caption-style control field
   - keep the core descriptors in English unless the user explicitly requires another language
   - put the highest-signal controls first: `genre`, `mood`, `instrument`, `vocal`
   - after the metadata tags, add one short natural-language caption sentence
   - avoid prompt stuffing, conflicting genres, or long shopping lists of instruments

3. Build `lyrics` second:
   - use section tags such as `[intro]`, `[verse]`, `[pre-chorus]`, `[chorus]`, `[bridge]`, `[outro]`
   - for `song`, keep lines singable, concise, and role-specific
   - for `instrumental` and `underscore`, still emit section-tagged control text, but write instrumental cues instead of sung lyrics
   - make the chorus the clearest emotional hook for `song`
   - if the user provides unstructured prose, convert it into lyric-ready or cue-ready sections

4. Set control fields:
   - `language`: match the lyric language
   - `timesignature`: default to `4` unless the brief clearly implies waltz-like phrasing
   - `bpm`: keep conservative, mood-aligned defaults
   - `keyscale`: pick a simple major/minor key that matches the mood

5. Output only the workflow-ready fields:

```text
tags:
...

lyrics:
...

bpm: 96
language: zh
keyscale: C major
timesignature: 4
```

## Stage 07 use

When the pipeline selects `AceStep_Music_Workflow.json` through `music_generation` or `music_generation_acestep`:

- determine `music_profile` first:
  - `song`: vocal-led track with real lyrics
  - `instrumental`: pure music with no vocals
  - `underscore`: background-first score for BGM usage
- default Stage 07 `BGM_MAIN` to `underscore` unless the job explicitly asks for `song` or `instrumental`
- use this skill before constructing the workflow payload
- map `tags` into the workflow `tags` field
- map `lyrics` into the workflow `lyrics` field
- map `bpm`, `language`, `keyscale`, and `timesignature` into their same-named workflow fields
- keep duration separate: use the manifest job duration for workflow `duration` and latent `seconds`

## Hard rules

- Do not output a single loose `music_prompt` when AceStep fields are required.
- Do not leave lyrics as plain paragraphs without section tags.
- Do not mix too many genre targets in one prompt.
- Do not add explanatory prose outside the five workflow-ready fields.

## Reference

Read:

- `references/acestep-official-notes.md`
