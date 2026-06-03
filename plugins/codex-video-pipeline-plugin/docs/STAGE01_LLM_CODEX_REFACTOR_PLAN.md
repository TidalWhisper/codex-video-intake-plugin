# Stage 01 Codex-First Refactor Plan

## Status

This document defines the first-batch design landing for a Stage 01 refactor.

Current status:

- The official Stage 01 runtime now has a Codex-first executable path:
  `run_stage01_codex_flow.py` -> `new_script_template.py`.
- `$video-production-pipeline` can call that runtime through
  `skills/video-production-pipeline/scripts/run_stage01_from_locked_brief.py`.
- Stage 02 and later stages remain out of scope for this refactor track.

## Goal

Move Stage 01 from:

- Python templates writing title, logline, theme, beat summary, and visual prose

to:

- Codex generating the creative text
- Python compiling constraints, validating structure, writing files, and driving repair

## Non-goals For This Batch

- Do not replace the active Stage 01 runtime yet.
- Do not modify Stage 02 storyboard logic.
- Do not introduce a remote API dependency.
- Do not attempt full automatic md/json rendering from the new flow yet.

## Why

The existing Stage 01 path can preserve structure, but it becomes template-heavy when it tries to author:

- title
- logline
- theme
- beat summary
- visual paragraph
- story direction prose

These should come from model understanding, not hand-written Python phrase assembly.

## Target Architecture

Stage 01 should be split into four layers.

### 1. Constraint Compiler

Python reads `project_brief.locked.json` and compiles:

- hard constraints
- anchors
- beat count and beat lengths
- forbidden drift

This layer must not author creative prose.

### 2. Codex Generation Contract

Codex receives:

- prompt packet JSON
- generation prompt template
- output schema

Codex returns structured JSON only.

### 3. Writer / Renderer

Python converts Codex JSON into:

- `story_direction.md/json`
- `plot_structure.md/json`
- `script.md/json`
- `script_review.md`

### 4. Repair Loop

If validation fails:

- Python builds a repair packet
- Codex rewrites only allowed fields
- Python merges and validates again

## New Stage 01 Artifact Flow

1. `00_intake/project_brief.locked.json`
2. `build_stage01_prompt_packet.py`
3. `01_script/stage01_prompt_packet.json`
4. Codex reads:
   - `stage01_codex_generation_prompt.md`
   - `stage01_llm_output.schema.json`
   - `stage01_prompt_packet.json`
5. Codex writes:
   - `01_script/stage01_llm_output.json`
6. `write_stage01_outputs.py`
7. Official Stage 01 outputs
8. `validate_script.py --mode final`
9. If needed:
   - `build_stage01_repair_packet.py`
   - Codex repair
   - merge
   - revalidate

## Responsibilities Split

### Codex must generate

- title candidates
- selected title
- logline
- theme
- protagonist state
- narrative movement
- ending direction
- beat summary
- visual prose
- voiceover or dialogue text if the brief allows them
- music cue wording

### Python must enforce

- locked-brief compliance
- beat count and duration split
- voice mode boundaries
- music profile boundaries
- scene and subject anchor retention
- schema completeness
- file writing
- project state progression

## First-Batch File Plan

### New design references

- `skills/video-script-generation/references/stage01_llm_output.schema.json`
- `skills/video-script-generation/references/stage01_codex_generation_prompt.md`
- `skills/video-script-generation/references/stage01_codex_repair_prompt.md`
- `skills/video-script-generation/references/stage01_repair_packet.schema.json`

### New shell interfaces

- `skills/video-script-generation/scripts/build_stage01_prompt_packet.py`
- `skills/video-script-generation/scripts/write_stage01_outputs.py`
- `skills/video-script-generation/scripts/build_stage01_repair_packet.py`

### Existing files that will later be reduced in scope

- `scripts/pipeline_blueprints.py`
- `skills/video-script-generation/scripts/new_script_template.py`
- `skills/video-script-generation/scripts/validate_script.py`

## Prompt Packet Contract

The prompt packet should contain:

- project identity
- source brief path
- creative goal
- hard constraints
- anchors that must survive
- beat plan
- explicit forbidden drift
- output schema reference

It should be deterministic and fully derived from the locked brief.

## LLM Output Contract

The LLM output should be JSON-first and contain:

- title candidates
- selected title
- theme
- protagonist state
- narrative movement
- ending direction
- avoid list
- characters
- settings
- beats
- self-check

It must not contain storyboard shot lists.

## Repair Loop Rules

### Attempt 1

- only field-level fixes

### Attempt 2

- allow single-beat rewrite

### Attempt 3

- stop auto repair
- surface the remaining issues to the user

## Activation Plan

### Phase A

- land design docs
- land shell interfaces
- do not switch runtime

### Phase B

- connect Codex generation contract into Stage 01
- keep existing validator and state flow

### Phase C

- enable repair loop
- retire Python-authored creative prose

## Acceptance For This Batch

This batch is complete when:

- all design docs exist on disk
- shell scripts exist and are runnable
- prompt packet builder can emit a deterministic packet from a locked brief
- repair packet builder can emit a deterministic packet from a locked brief, current script, and structured errors
- writer shell can at least archive raw Codex output into the project folder
