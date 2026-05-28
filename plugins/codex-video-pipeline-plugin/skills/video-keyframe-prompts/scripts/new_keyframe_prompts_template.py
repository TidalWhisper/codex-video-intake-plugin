#!/usr/bin/env python3
"""Create a Stage 04 keyframe/motion prompts JSON template.

This script scaffolds one empty prompt record per storyboard shot. Codex must fill
prompt content before final validation.
"""
from __future__ import annotations
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"ERROR: file not found: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON in {path}: {exc}")


def main(argv: list[str]) -> int:
    if len(argv) != 6:
        print("Usage: python new_keyframe_prompts_template.py <locked_brief.json> <script.json> <storyboard.json> <character_bible.json> <keyframe_prompts.json>", file=sys.stderr)
        return 2
    brief_path = Path(argv[1])
    script_path = Path(argv[2])
    storyboard_path = Path(argv[3])
    character_path = Path(argv[4])
    out_path = Path(argv[5])
    brief = load_json(brief_path)
    script = load_json(script_path)
    storyboard = load_json(storyboard_path)
    character_bible = load_json(character_path)

    if brief.get("status") != "locked" or brief.get("confirmed_by_user") is not True:
        print("ERROR: brief must be locked and confirmed_by_user=true", file=sys.stderr)
        return 1
    if script.get("stage") != "STAGE_01_SCRIPT_GENERATION":
        print("ERROR: script.stage must be STAGE_01_SCRIPT_GENERATION", file=sys.stderr)
        return 1
    if storyboard.get("stage") != "STAGE_02_STORYBOARD_GENERATION":
        print("ERROR: storyboard.stage must be STAGE_02_STORYBOARD_GENERATION", file=sys.stderr)
        return 1
    if character_bible.get("stage") != "STAGE_03_CHARACTER_BIBLE":
        print("ERROR: character_bible.stage must be STAGE_03_CHARACTER_BIBLE", file=sys.stderr)
        return 1

    project_id = brief.get("project_id") or script.get("project_id") or storyboard.get("project_id") or character_bible.get("project_id") or brief_path.parents[1].name
    shots = storyboard.get("shots") if isinstance(storyboard.get("shots"), list) else []
    characters = character_bible.get("characters") if isinstance(character_bible.get("characters"), list) else []
    main_char_ids = [c.get("character_id") for c in characters if isinstance(c, dict) and c.get("role") == "main" and c.get("character_id")]
    all_char_ids = [c.get("character_id") for c in characters if isinstance(c, dict) and c.get("character_id")]
    default_chars = main_char_ids or all_char_ids

    shot_prompts = []
    for idx, shot in enumerate(shots):
        if not isinstance(shot, dict):
            continue
        shot_id = shot.get("shot_id") or f"S{idx+1:03d}"
        prev_id = shots[idx-1].get("shot_id") if idx > 0 and isinstance(shots[idx-1], dict) else None
        next_id = shots[idx+1].get("shot_id") if idx + 1 < len(shots) and isinstance(shots[idx+1], dict) else None
        shot_prompts.append({
            "shot_id": shot_id,
            "source_shot_ref": f"{str(storyboard_path).replace('\\', '/') }#{shot_id}",
            "duration_sec": shot.get("duration_sec"),
            "characters": default_chars,
            "scene_summary": shot.get("scene") or "",
            "start_keyframe_prompt": "",
            "end_keyframe_prompt": "",
            "motion_prompt": "",
            "camera_prompt": shot.get("camera") or "",
            "lighting_prompt": "",
            "style_prompt": "",
            "consistency_prompt": "",
            "negative_prompt": "",
            "image_generation_notes": "",
            "video_generation_notes": "",
            "dependencies": {
                "reference_images": [],
                "previous_shot_id": prev_id,
                "next_shot_id": next_id
            }
        })

    transition_prompts = []
    for idx in range(max(0, len(shot_prompts) - 1)):
        cur = shot_prompts[idx]
        nxt = shot_prompts[idx + 1]
        transition_prompts.append({
            "transition_id": f"T{idx+1:03d}",
            "from_shot_id": cur["shot_id"],
            "to_shot_id": nxt["shot_id"],
            "transition_type": "",
            "transition_motion_prompt": "",
            "continuity_requirements": []
        })

    template = {
        "schema_version": "0.5.0",
        "stage": "STAGE_04_KEYFRAME_PROMPTS",
        "status": "draft",
        "project_id": project_id,
        "source_brief": str(brief_path).replace("\\", "/"),
        "source_script": str(script_path).replace("\\", "/"),
        "source_storyboard": str(storyboard_path).replace("\\", "/"),
        "source_character_bible": str(character_path).replace("\\", "/"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "prompt_language": "English generation prompts with Chinese review notes",
        "visual_strategy": {
            "keyframe_mode": "start_and_end_keyframes_per_shot",
            "video_mode": "image_to_video_per_shot",
            "continuity_strategy": "reuse character consistency prompts and adjacent-shot transition requirements"
        },
        "shot_prompts": shot_prompts,
        "transition_prompts": transition_prompts,
        "global_negative_prompt": "",
        "self_check": {
            "matches_locked_brief": None,
            "matches_script": None,
            "matches_storyboard": None,
            "uses_character_consistency": None,
            "covers_all_storyboard_shots": None,
            "ready_for_image_generation": None,
            "notes": []
        },
        "allowed_next_stage": None
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(template, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"KEYFRAME PROMPTS TEMPLATE CREATED: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
