# AceStep Official Notes

This note condenses the official ACE-Step 1.5 and ComfyUI documentation into a Stage 07 prompt-building rule set.

## Sources

- ACE-Step 1.5 Tutorial:
  - `https://github.com/ace-step/ACE-Step-1.5/blob/main/docs/en/Tutorial.md`
- ACE-Step 1.5 Inference guide:
  - `https://github.com/ace-step/ACE-Step-1.5/blob/main/docs/en/INFERENCE.md`
- ACE-Step musicians guide:
  - `https://github.com/ace-step/ACE-Step-1.5/blob/main/docs/en/ace_step_musicians_guide.md`
- ComfyUI built-in node:
  - `https://docs.comfy.org/built-in-nodes/TextEncodeAceStepAudio1.5`
- ComfyUI AceStep tutorial:
  - `https://docs.comfy.org/tutorials/audio/ace-step/ace-step-v1-5`

## What the official docs say

### 1. The most important prompt inputs are caption plus lyrics

- The official tutorial states that the most important inputs are `caption` and `lyric`.
- The official ComfyUI node exposes parallel fields as `tags` and `lyrics`.
- For Stage 07 use, treat AceStep `tags` as the caption-style control surface. This is an inference from the two official sources combined.

### 2. Lyrics should use explicit structure tags

- Official docs show section tags like `[verse]`, `[chorus]`, and `[bridge]`.
- The musician guide also shows optional structural/performance tags such as `[Female]`, `[Guitar Solo]`, `[Fade Out]`, and similar markup.
- Practical rule:
  - always give AceStep structured lyrics
  - at minimum include `intro`, `verse`, `pre-chorus`, `chorus`, `bridge`, and `outro` when generating full songs

### 3. Metadata tags improve control

- The official inference guide recommends metadata tags and gives examples such as `genre`, `mood`, `instrument`, `singer`, and `vocal_style`.
- Practical rule:
  - start `tags` with compact metadata tags
  - then add one short caption sentence for arrangement and emotional arc

Suggested shape:

```text
[genre: mandopop, piano ballad] [mood: warm, wistful] [instrument: piano, strings, ocean ambience] [vocal: female vocal, soft vocal]
female vocal mandopop ballad, warm but wistful, polished arrangement, clear chorus hook.
```

### 4. Keep the prompt coherent

- The tutorial recommends keeping style description complexity in the caption rather than overloading lyrics.
- Official examples imply better control when genre, mood, singer, and arrangement are mutually consistent.
- Practical rule:
  - keep one primary genre, one main mood family, and a short instrument list
  - do not stack contradictory targets like `lofi orchestral metal ambient dance`

### 5. The chorus should be the hook

- The musician guide emphasizes common song structure and singable lyric sections.
- Practical rule:
  - verse carries scene and narrative
  - pre-chorus lifts tension
  - chorus contains the memorable emotional line
  - bridge changes perspective or intensity

## Stage 07 default builder contract

For `AceStep_Music_Workflow.json`, output exactly:

```text
tags:
<caption-style control text with metadata tags>

lyrics:
<section-tagged lyrics>

bpm: <int>
language: <zh|en|...>
keyscale: <e.g. C major / E minor>
timesignature: <3|4|...>
```

Duration does not belong in the prompt-builder output. Stage 07 should continue to read duration from the audio job and map it to workflow `duration` and latent `seconds`.

## Conservative heuristics for automatic generation

- `language`
  - `zh` when lyrics are Chinese
  - `en` when lyrics are English
- `timesignature`
  - `4` by default
  - `3` only when the brief clearly asks for waltz-like motion
- `bpm`
  - `70-84` for calm, sad, reflective ballads
  - `85-105` for warm mid-tempo pop
  - `106-125` for uplifting or cinematic pop
- `keyscale`
  - minor keys for melancholy, tension, or epic sadness
  - major keys for warmth, healing, or hopeful uplift

## Forbidden output behavior

- Do not return only one sentence of free-form prompt text.
- Do not leave lyrics unstructured.
- Do not write explanatory notes outside workflow fields.
- Do not translate user lyrics unless the task explicitly asks for it.
