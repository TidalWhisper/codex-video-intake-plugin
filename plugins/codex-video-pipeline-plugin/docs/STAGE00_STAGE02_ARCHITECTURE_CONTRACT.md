# Stage00 - Stage02 Architecture Contract

## Purpose

This document locks the real business relationship between `Stage00 -> Stage01 -> Stage02`.

It is not a brainstorming note.
It is the hard contract for:

- official entry routing
- upstream/downstream ownership
- fields that may not drift
- gate design

Before any code change touching `Stage00`, `Stage01`, or `Stage02`, the change
must be checked against this document.

## Business Roles

### Stage00

Stage00 is the project intake and locked-brief stage.

In short-video production language, Stage00 answers:

- what story we are making
- how long it should be
- what genre and style it belongs to
- what frame format it uses
- whether voice/music are needed
- how far the pipeline is allowed to go

Stage00 does **not** write the script.
Stage00 does **not** write the storyboard.
Stage00 defines the locked production brief that downstream stages must obey.

### Stage01

Stage01 is the script-structure stage.

In short-video production language, Stage01 turns the locked brief into a
shootable story skeleton:

- story direction
- plot structure
- beat timeline
- script sections
- character and scene anchors needed by later stages

Stage01 does **not** redefine the brief.
Stage01 does **not** directly author storyboard shot lists.
Stage01 produces the script package that Stage02 must consume.

### Stage02

Stage02 is the storyboard breakdown stage.

In short-video production language, Stage02 turns the approved Stage01 script
package into executable shots:

- shot count
- shot timing
- shot-by-shot action
- camera/composition
- dialogue/voiceover placement
- production notes for later image/video stages

Stage02 does **not** redefine the story.
Stage02 consumes Stage01 structure and converts it into storyboard shots.

## Official Entry Chain

The normal user-facing chain is:

```text
$video-production-pipeline
-> skills/video-production-pipeline/scripts/run_stage00_controller.py
-> skills/video-production-pipeline/scripts/run_stage00_lock_and_continue.py
-> skills/video-production-pipeline/scripts/run_stage01_from_locked_brief.py
-> skills/video-script-generation/scripts/run_stage01_codex_flow.py
-> user confirmation gate
-> skills/video-production-pipeline/scripts/run_stage02_from_confirmed_script.py
-> skills/video-storyboard-generation/scripts/run_stage02_codex_flow.py
```

Child stage skills are internal/recovery paths.
They are not the normal user entry.

## Stage00 Contract

### Stage00 input

Stage00 collects the intake answers and normalizes them into the project brief.

### Stage00 output

The authoritative downstream artifact is:

```text
<project_dir>/00_intake/project_brief.locked.json
```

### Stage00 hard contract fields

These fields are owned by Stage00 and must not drift in downstream stages:

- `project_id`
- `project_dir`
- `status=locked`
- `confirmed_by_user=true`
- `allowed_next_stage=STAGE_01_SCRIPT_GENERATION`
- `normalized.idea`
- `normalized.target_duration_sec`
- `normalized.target_duration_label`
- `normalized.genre`
- `normalized.style`
- `normalized.aspect_ratio`
- `normalized.aspect_ratio_label`
- `normalized.resolution`
- `normalized.resolution_label`
- `normalized.characters_mode`
- `normalized.characters_required`
- `normalized.voice_mode`
- `normalized.voice_required`
- `normalized.music_mode`
- `normalized.music_profile`
- `normalized.music_required`
- `normalized.final_output`
- `routing.*`
- `compiled_requirements.*`
- `quality_contract.*`

### Stage00 ownership boundary

Stage00 may:

- collect and normalize intake data
- validate the brief
- lock the brief
- update manifest state for Stage00 completion

Stage00 may not:

- invent Stage01 script beats
- invent Stage02 shots
- silently change downstream-ready business requirements after lock

## Stage01 Contract

### Stage01 input

Stage01 reads only the locked brief as its business source of truth:

```text
<project_dir>/00_intake/project_brief.locked.json
```

### Stage01 output

The authoritative downstream artifact is:

```text
<project_dir>/01_script/script.json
```

Related official outputs include:

- `story_direction.md/json`
- `plot_structure.md/json`
- `script.md`
- `script_review.md`

### Stage01 hard contract to Stage02

These fields are the formal Stage01 -> Stage02 consumption contract:

- `title`
- `logline`
- `theme`
- `characters`
- `settings`
- `story_anchors`
- `duration_plan.target_duration_sec`
- `duration_plan.beats`
- `script.voice_mode`
- `script.music_mode`
- `script.music_profile`
- `script.sections`
- `self_check.matches_locked_brief`
- `self_check.ready_for_storyboard`

### Stage01 ownership boundary

Stage01 may:

- compile prompt-packet constraints from the locked brief
- ask Codex/LLM for structured script output
- render official Stage01 artifacts
- validate and repair Stage01 output

Stage01 may not:

- change Stage00 locked-brief facts
- emit storyboard shot lists as its formal output
- bypass the formal validator and still claim success

### Stage01 formal runtime rule

The formal Stage01 runtime is the official chain rooted at:

```text
skills/video-production-pipeline/scripts/run_stage01_from_locked_brief.py
-> skills/video-script-generation/scripts/run_stage01_codex_flow.py
```

That formal runtime must generate `stage01_llm_output.json` through Codex/LLM.

`stage01_local_semantics.py` is not part of the formal runtime.
It may exist only for explicitly named non-formal roles such as:

- tests
- fixtures
- manual emergency fallback that is separately labeled

It must not silently re-enter the formal Stage01 path.

## Stage02 Contract

### Stage02 input

Stage02 consumes:

```text
<project_dir>/00_intake/project_brief.locked.json
<project_dir>/01_script/script.json
```

### Stage02 output

The authoritative Stage02 artifact is:

```text
<project_dir>/02_storyboard/storyboard.json
```

### Stage02 consumption rules

Stage02 must consume Stage01 structure as follows:

- `len(duration_plan.beats)` defines the target shot count baseline
- `script.sections` define the story coverage that shots must preserve
- `story_anchors` carry forward recurring story facts
- `characters` and `settings` remain available as continuity anchors

### Stage02 ownership boundary

Stage02 may:

- decide shot timing
- decide shot ordering detail
- decide camera/composition wording
- add production notes

Stage02 may not:

- rewrite the core story away from Stage01
- drop Stage01 anchors without explicit regeneration logic
- claim success if the storyboard validator fails

## Hard Gates

The following gates are mandatory before a change touching this chain may be
considered complete.

### Gate 1: Official blank-project path

Must prove the official entry can still reach Stage01:

```text
$video-production-pipeline
-> Stage00
-> lock brief
-> Stage01 dispatch
```

### Gate 2: Stage01 formal source gate

Must prove the formal Stage01 runner source does not silently route through:

- `stage01_local_semantics`
- `build_stage01_llm_output`
- `STAGE01_LOCAL_EXECUTION_MODE`
- `STAGE01_LOCAL_REPAIR_MODE`

### Gate 3: Stage01 -> Stage02 contract gate

Must prove that Stage02 prompt-packet construction preserves:

- `story_anchors`
- `duration_plan.beats`
- `script.sections`
- `target_shot_count == len(duration_plan.beats)`

### Gate 4: Repository change gate

Every repository modification must pass the executable gate stack.

At minimum, the gate stack must block:

- generated/temp files
- syntax-broken Python
- Stage00 -> Stage01 official-entry regressions
- Stage01 formal-source regressions
- Stage01 -> Stage02 contract regressions

## Change Policy

Before modifying any file related to this chain, the implementer must answer:

1. Which stage owns the field being changed
2. Which downstream stage consumes it
3. Which hard gate proves the change did not break the chain

If those three answers are not clear, code changes must stop until the impact
scope is understood.
