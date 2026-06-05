# Stage 02 Codex-First Refactor Plan

## Status

This document locks the migration plan for turning Stage 02 into a true
Codex-first runtime without breaking the existing `Stage00 -> Stage01 -> Stage02`
official chain.

Current truth as of 2026-06-05:

- `Stage01` formal runtime is already Codex-first.
- `Stage02` formal runtime is **not** yet Codex-first.
- `Stage02` still uses a Codex-shaped artifact chain, but the formal runner
  still generates `stage02_llm_output.json` through
  `stage02_local_semantics.py`.

This plan is not a completion claim.
It is the locked migration plan that must be followed before code changes are
considered done.

## Goal

Move Stage 02 from:

- formal runner shell + local structured-content core

to:

- formal runner shell + Codex structured output core

while preserving:

- Stage00 locked brief ownership
- Stage01 approved script ownership
- Stage01 -> Stage02 contract stability
- official pipeline entry behavior
- Stage02 validator / writer / repair flow

## Non-goals

This migration must **not** do the following:

- rewrite Stage00 intake semantics
- rewrite Stage01 script semantics
- change the official Stage02 artifact schema just because the generation
  backend changes
- redesign Stage03 or later stages
- hide a local fallback inside the formal runner and call it “migrated”

## Current Reality

### What is already good

- `skills/video-production-pipeline/scripts/run_stage02_from_confirmed_script.py`
  is the official Stage02 dispatch wrapper.
- `skills/video-storyboard-generation/scripts/build_stage02_prompt_packet.py`
  already compiles a stable Stage01 -> Stage02 prompt packet.
- `skills/video-storyboard-generation/scripts/new_storyboard_template.py`
  already validates and writes official Stage02 outputs.
- `skills/video-storyboard-generation/scripts/write_stage02_outputs.py`
  already renders the final Stage02 files from `stage02_llm_output.json`.
- `skills/video-storyboard-generation/scripts/validate_storyboard.py`
  already enforces final storyboard structure.

### What is still false-codex-first

- `skills/video-storyboard-generation/scripts/run_stage02_codex_flow.py`
  still imports `stage02_local_semantics`.
- it still calls `build_stage02_llm_output(...)` directly in the formal path.
- it still writes `STAGE02_LOCAL_EXECUTION_MODE`.
- it still writes `STAGE02_LOCAL_REPAIR_MODE`.
- Stage02 formal tests still largely assume the local structured-output builder.
- repository source gates only explicitly lock Stage01 formal cleanliness today.

## Frozen Contracts

Before migration starts, these contract surfaces are frozen and may not drift
unless a separate explicit contract change is approved.

### Stage00 ownership that Stage02 may not change

- locked brief business facts
- routing
- compiled requirements
- quality contract
- final output scope

### Stage01 -> Stage02 consumption contract that must remain stable

- `story_anchors`
- `duration_plan.target_duration_sec`
- `duration_plan.beats`
- `script.sections`
- `script.voice_mode`
- `script.music_mode`
- `script.music_profile`
- `characters`
- `settings`

### Stage02 output contract that must remain stable

- `02_storyboard/storyboard.json`
- `02_storyboard/stage02_prompt_packet.json`
- `02_storyboard/stage02_llm_output.json`
- `02_storyboard/storyboard.md`
- `02_storyboard/storyboard_review.md`

### Files that must be treated as contract-preserving layers during this migration

- `skills/video-storyboard-generation/scripts/build_stage02_prompt_packet.py`
- `skills/video-storyboard-generation/scripts/new_storyboard_template.py`
- `skills/video-storyboard-generation/scripts/write_stage02_outputs.py`
- `skills/video-storyboard-generation/scripts/validate_storyboard.py`

The first migration pass must not casually rewrite these modules.
The primary cut must happen in the formal Stage02 runner.

## Target Architecture

Stage02 must follow the same runtime pattern already used by Stage01.

### Layer 1: Constraint Compiler

Python compiles a deterministic prompt packet from:

- `00_intake/project_brief.locked.json`
- `01_script/script.json`

This remains:

- `build_stage02_prompt_packet.py`

Python owns:

- hard constraints
- shot count baseline
- upstream story anchors
- forbidden drift

Python must not author the actual storyboard shots in the formal runtime.

### Layer 2: Codex Structured Generation

Codex must generate:

- full `stage02_llm_output.json`

through:

- `stage02_codex_generation_prompt.md`
- `stage02_llm_output.schema.json`
- `stage02_prompt_packet.json`

The formal Stage02 runner must call:

- `resolve_codex_bin`
- `run_codex_exec`
- `write_codex_output_json`

just like Stage01.

### Layer 3: Writer / Renderer

Python must continue converting `stage02_llm_output.json` into:

- `storyboard.json`
- `storyboard.md`
- `storyboard_review.md`

This remains owned by:

- `new_storyboard_template.py`
- `write_stage02_outputs.py`

### Layer 4: Repair Loop

If validation fails:

- Python writes `stage02_validation_errors.json`
- Python writes `stage02_repair_packet.json`
- Codex returns a full replacement `stage02_llm_output.json`
- Python revalidates through the same official writer path

The repair loop may not silently switch back to `stage02_local_semantics`.

## Migration Design

### Phase 0: Lock the baseline before code changes

Purpose:

- prove what currently works
- prevent accidental contract drift during migration

Required baseline truths:

1. official Stage00 blank-project path still reaches Stage01
2. Stage01 formal runner still has no local-semantics backdoor
3. Stage01 -> Stage02 contract fields still pass through prompt-packet build
4. current Stage02 formal entry still produces a valid storyboard from a
   confirmed script

No migration claim is allowed in this phase.

### Phase 1: Cut only the Stage02 formal generation core

Primary file:

- `skills/video-storyboard-generation/scripts/run_stage02_codex_flow.py`

Required changes:

1. add a `generate_stage02_llm_output(...)` helper mirroring Stage01
2. wire in:
   - `resolve_codex_bin`
   - `run_codex_exec`
   - `write_codex_output_json`
3. keep:
   - prompt-packet generation
   - writer invocation
   - validator flow
   - repair-packet flow
4. remove from the formal path:
   - `stage02_local_semantics`
   - `build_stage02_llm_output(...)`
   - `STAGE02_LOCAL_EXECUTION_MODE`
   - `STAGE02_LOCAL_REPAIR_MODE`

Important:

- this phase is allowed to change only the formal runner behavior
- it is not allowed to redesign prompt-packet shape or storyboard schema

### Phase 2: Convert Stage02 formal tests to Codex-world assumptions

Purpose:

- stop tests from certifying the old local builder path

Required test direction:

1. tests must mock `generate_stage02_llm_output(...)`
2. tests must verify:
   - prompt packet written
   - generation request written
   - Codex last message written
   - `stage02_llm_output.json` written from structured output
   - final `storyboard.json` rendered successfully
3. repair tests must verify:
   - repair request file written
   - repair last message file written
   - second Codex generation attempt occurs

Tests must no longer monkeypatch the formal runner around
`build_stage02_llm_output(...)`.

### Phase 3: Add Stage02 source-level anti-regression gates

Purpose:

- make it impossible to quietly route formal Stage02 back through local
  semantics

Required new source gate:

Formal Stage02 source files:

- `skills/video-production-pipeline/scripts/run_stage02_from_confirmed_script.py`
- `skills/video-storyboard-generation/scripts/run_stage02_codex_flow.py`

Forbidden tokens:

- `stage02_local_semantics`
- `build_stage02_llm_output`
- `STAGE02_LOCAL_EXECUTION_MODE`
- `STAGE02_LOCAL_REPAIR_MODE`

This gate must live in:

- Stage02 tests
- repository change gate

### Phase 4: Demote Stage02 local semantics to non-formal role

Purpose:

- align Stage02 with Stage01 runtime boundary rules

`stage02_local_semantics.py` may continue to exist only as:

- tests
- fixtures
- explicitly labeled manual fallback

It must no longer be described as part of the formal production path.

### Phase 5: Full chain regression after the cut

Purpose:

- prove the migrated Stage02 works inside the real official chain

Required regression proof:

1. official Stage00 gate still passes
2. Stage01 formal-source gate still passes
3. Stage01 -> Stage02 contract gate still passes
4. Stage02 formal-source gate passes
5. Stage02 formal runner generation test passes
6. Stage02 repair loop test passes
7. Stage01 formal output can still flow through the official Stage02 entry and
   produce final `storyboard.json`

## Required New Tests

At minimum, migration is blocked until these tests exist and pass.

### Test 1: Stage02 formal runner no longer imports local semantics

Equivalent to the existing Stage01 source-clean test.

Must fail if `run_stage02_codex_flow.py` contains:

- `stage02_local_semantics`
- `build_stage02_llm_output`
- `STAGE02_LOCAL_EXECUTION_MODE`
- `STAGE02_LOCAL_REPAIR_MODE`

### Test 2: Stage02 formal entry chain has no local-semantics reference

Must scan:

- `run_stage02_from_confirmed_script.py`
- `run_stage02_codex_flow.py`

### Test 3: Stage02 formal runner generates storyboard package without manual fill

Must mock Codex structured output instead of local semantics.

### Test 4: Stage02 formal runner auto-repairs failed first attempt

Must prove:

- validation failure creates repair packet
- second Codex call occurs
- repaired storyboard validates and lands

### Test 5: Stage01 formal output still flows through Stage02 formal entry

Must prove the official entry path still works after Stage02 migration.

## Required Repository Gate Changes

`scripts/repo_change_gate.py` must be extended so the hard gate covers Stage02,
not just Stage01.

At minimum it must enforce:

1. official Stage00 blank-project gate
2. Stage01 formal source gate
3. Stage01 -> Stage02 contract gate
4. Stage02 formal source gate
5. Stage02 formal flow tests

This is required so future modifications anywhere in the repo cannot silently
reintroduce a fake Stage02 codex-first path.

## Risk Register

### Risk 1: Breaking the official Stage02 wrapper chain

If `run_stage02_codex_flow.py` argument handling or file outputs drift,
`run_stage02_from_confirmed_script.py` will still dispatch but the chain will
break.

Control:

- preserve CLI signature
- preserve artifact paths
- preserve final success/failure return behavior

### Risk 2: Breaking Stage01 -> Stage02 contract shape

If prompt-packet semantics drift while migrating the runner, Stage02 may still
run but will no longer consume Stage01 faithfully.

Control:

- freeze prompt-packet module in the first pass
- keep explicit tests for `beats`, `sections`, `story_anchors`, and target shot
  count

### Risk 3: Passing tests while still using a hidden local builder

This is the highest-risk false-success mode.

Control:

- source-level forbidden-token tests
- repository gate scan
- formal runner tests that mock Codex helper rather than local builder

### Risk 4: Rewriting the story instead of breaking it into shots

If the generation prompt or repair loop lets Stage02 reinterpret the story from
the brief, the storyboard will drift away from Stage01.

Control:

- keep prompt packet anchored on approved script
- keep repair prompt explicitly limited to failed checks
- preserve `story_anchors`, `beats`, and `sections` handoff

## Completion Standard

Stage02 migration is complete only when all of the following are true:

1. the formal Stage02 runner no longer imports or calls local semantics
2. the formal repair loop no longer regenerates through local semantics
3. Stage02 formal tests use mocked Codex structured output helpers
4. Stage02 source-level anti-regression tests exist and pass
5. repository hard gate enforces Stage02 formal cleanliness
6. official Stage01 output still flows through the official Stage02 entry and
   lands valid final storyboard outputs

If any one of the above is false, the status must remain:

- `Stage02 not yet fully codex-first migrated`

## Execution Order Lock

When implementation begins, the order is locked:

1. baseline read-only verification
2. formal runner cut
3. Stage02 formal tests conversion
4. Stage02 source gate tests
5. repository gate extension
6. final official-chain regression

No claim of completion is allowed before step 6 passes.
