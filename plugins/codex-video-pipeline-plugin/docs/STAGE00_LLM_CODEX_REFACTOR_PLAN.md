# Stage 00 LLM Codex-First Refactor Plan

## Current Truth

As of the current repository state:

- `Stage 00` is still Python-first.
- The active path is:
  - create project folder
  - write `intake_state.json`
  - write `project_brief.draft.json`
  - validate draft
  - user confirmation
  - lock `project_brief.locked.json`
- `Stage 01-04` already use the Codex-first pattern:
  - prompt packet
  - Codex structured output
  - writer
  - validator
  - repair loop

This mismatch is now the main architecture gap in the pipeline entry.

## Migration Goal

Move `Stage 00` onto the same Codex-first backbone while keeping the current downstream brief contract stable.

That means:

- Codex becomes the primary semantic engine for intake understanding.
- Python remains the deterministic support layer for:
  - state persistence
  - canonical option enforcement
  - structure validation
  - folder / manifest / lock side effects
- `project_brief.draft.json` and `project_brief.locked.json` keep their current official shapes so `Stage 01-09` do not need to change just because `Stage 00` changed generation strategy.

## Why Stage 00 Must Be Split

`Stage 00` cannot be migrated cleanly as one flat script, because it is not a single generation stage.

It has two different jobs:

1. `Stage 00-A`
   - multi-turn intake dialogue
   - one-question routing
   - canonical option parsing
   - free-text note preservation
   - intake state persistence
2. `Stage 00-B`
   - final brief synthesis
   - draft brief generation
   - brief validation
   - confirmation / modify / refill branching
   - lock side effects

If these two jobs stay merged, the code will drift back into template-heavy Python branching.

## Target Architecture

### Stage 00-A

Target chain:

```text
intake_state.json
-> build_stage00_intake_prompt_packet.py
-> Codex structured output
-> write_stage00_intake_state.py
-> validate_stage00_intake_state.py
```

Primary responsibility:

- understand the user reply for the current question only
- preserve user wording and short notes
- update normalized partial fields
- decide whether to:
  - ask the next canonical question
  - repeat the same question because the answer is incomplete
  - mark intake ready for brief synthesis

### Stage 00-B

Target chain:

```text
intake_state.json
-> build_stage00_brief_prompt_packet.py
-> Codex structured output
-> write_stage00_brief_outputs.py
-> validate_project_brief.py
-> build_stage00_brief_repair_packet.py
-> Codex repair
-> lock_project_brief.py
```

Primary responsibility:

- transform completed intake state into the official draft brief
- keep the brief creator-facing instead of script-assembled
- validate and repair before lock
- hand off to existing Stage 01 official entry

## Canonical Rules That Must Not Drift

These files remain the single source of truth:

- `skills/video-project-intake/references/first_layer_options.md`
- `skills/video-project-intake/references/stage00_question_blocks.md`

Hard rules:

- user-facing option letters must stay identical
- question wording must be reproduced exactly
- the pipeline entry must not invent alternate Stage 00 menus
- Codex may interpret replies, but may not rewrite the canonical question blocks

## File Plan

### Keep

- `skills/video-project-intake/scripts/create_project_folder.py`
- `skills/video-project-intake/scripts/validate_project_brief.py`
- `skills/video-project-intake/scripts/validate_project_structure.py`
- `skills/video-project-intake/scripts/lock_project_brief.py`
- `skills/video-project-intake/references/project_brief.schema.json`
- `skills/video-project-intake/references/intake_state.schema.json`

### Reduce to Legacy / Test Helper Status

- `skills/video-project-intake/scripts/new_project_brief_template.py`

It can stay for isolated debugging, but should no longer be the primary Stage 00 generator.

### Add in First Batch

- `skills/video-project-intake/scripts/stage00_intake_common.py`
- `skills/video-project-intake/scripts/build_stage00_intake_prompt_packet.py`
- `skills/video-project-intake/scripts/write_stage00_intake_state.py`
- `skills/video-project-intake/scripts/validate_stage00_intake_state.py`
- `skills/video-project-intake/scripts/run_stage00_intake_turn_codex_flow.py`
- `skills/video-project-intake/references/stage00_intake_turn_output.schema.json`
- `skills/video-project-intake/references/stage00_intake_generation_prompt.md`

### Add in Second Batch

- `skills/video-project-intake/scripts/build_stage00_brief_prompt_packet.py`
- `skills/video-project-intake/scripts/write_stage00_brief_outputs.py`
- `skills/video-project-intake/scripts/build_stage00_brief_repair_packet.py`
- `skills/video-project-intake/scripts/run_stage00_brief_codex_flow.py`
- `skills/video-project-intake/references/stage00_brief_llm_output.schema.json`
- `skills/video-project-intake/references/stage00_brief_generation_prompt.md`
- `skills/video-project-intake/references/stage00_brief_repair_prompt.md`

## Stage 00-A State Contract

The Stage 00-A state should represent the live wizard position, not just accumulated raw answers.

Recommended persisted fields:

- `schema_version`
- `stage`
- `status`
- `project_id`
- `project_dir`
- `current_question`
- `current_question_key`
- `answers`
- `user_answers`
- `normalized`
- `missing_required_fields`
- `required_fields_complete`
- `next_question_key`
- `next_prompt_text`
- `ready_for_brief_generation`
- `last_user_reply`
- `updated_at`

Status meaning:

- `collecting`: still asking Stage 00 questions
- `draft_ready`: all 9 questions answered well enough to synthesize draft brief
- `locked`: brief already locked

## Stage 00-A LLM Output Contract

For each intake turn, Codex should return one structured object containing:

- which question it believes it answered
- the raw/selected/free-text interpretation
- user answer patch
- normalized partial patch
- missing field list
- required field completeness
- next question key
- next prompt text
- whether a follow-up is needed
- a short completion summary

This contract lets Python remain small and deterministic while moving semantic understanding to Codex.

## Official Entry Integration

`$video-production-pipeline` should stop hardcoding Stage 00 logic directly.

The target runtime path becomes:

1. use `run_stage00_intake_turn_codex_flow.py` during one-question intake
2. once `draft_ready=true`, run Stage 00-B brief synthesis
3. after lock, keep using the existing Stage 01 official entry:
   - `skills/video-production-pipeline/scripts/run_stage01_from_locked_brief.py`

## First Batch Scope

This first batch only lands:

- the design document
- Stage 00-A prompt packet builder
- Stage 00-A LLM output schema
- Stage 00-A generation prompt
- Stage 00-A state writer
- Stage 00-A state validator
- Stage 00-A Codex runner
- minimal tests proving the skeleton is executable

This batch does not yet:

- generate `project_brief.draft.json` from Codex
- add Stage 00 repair loop
- rewire the full pipeline entry
- remove the legacy Python-first Stage 00 path

## Acceptance for This Batch

The first batch is considered correctly landed when:

1. the new files exist with stable CLI interfaces
2. a missing `intake_state.json` can be treated as a new Stage 00 session
3. a single user reply can produce:
   - `stage00_intake_prompt_packet.json`
   - `stage00_intake_turn_llm_output.json`
   - updated `intake_state.json`
4. `validate_stage00_intake_state.py` passes on the updated state
5. tests cover at least:
   - canonical opening block in prompt packet
   - one-turn state advance from `idea` to `target_duration`
   - runner wiring through fake Codex execution
