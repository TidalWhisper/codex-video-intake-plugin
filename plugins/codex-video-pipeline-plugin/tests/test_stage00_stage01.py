#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
import threading
from pathlib import Path
from types import ModuleType
from urllib.parse import quote
from urllib import request

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
INTAKE = ROOT / "skills" / "video-project-intake" / "scripts"
SCRIPT = ROOT / "skills" / "video-script-generation" / "scripts"
STORYBOARD = ROOT / "skills" / "video-storyboard-generation" / "scripts"
PIPELINE = ROOT / "skills" / "video-production-pipeline" / "scripts"
CHARACTER = ROOT / "skills" / "video-character-bible" / "scripts"
KEYFRAME = ROOT / "skills" / "video-keyframe-prompts" / "scripts"
IMAGES = ROOT / "skills" / "video-keyframe-images" / "scripts"
VIDEOCLIPS = ROOT / "skills" / "video-video-clips" / "scripts"
AUDIO = ROOT / "skills" / "video-audio" / "scripts"
ASSEMBLY = ROOT / "skills" / "video-assembly" / "scripts"
QA = ROOT / "skills" / "video-qa-delivery" / "scripts"
TEMPLATES = ROOT / "templates"


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


create_project_folder = load_module("create_project_folder_for_test", INTAKE / "create_project_folder.py")
new_project_brief_template = load_module("new_project_brief_template_for_test", INTAKE / "new_project_brief_template.py")
lock_project_brief = load_module("lock_project_brief_for_test", INTAKE / "lock_project_brief.py")
validate_project_brief = load_module("validate_project_brief", INTAKE / "validate_project_brief.py")
validate_project_structure = load_module("validate_project_structure_for_test", INTAKE / "validate_project_structure.py")
new_script_template = load_module("new_script_template_for_test", SCRIPT / "new_script_template.py")
validate_script = load_module("validate_script_for_test", SCRIPT / "validate_script.py")
build_stage01_prompt_packet = load_module("build_stage01_prompt_packet_for_test", SCRIPT / "build_stage01_prompt_packet.py")
write_stage01_outputs = load_module("write_stage01_outputs_for_test", SCRIPT / "write_stage01_outputs.py")
build_stage01_repair_packet = load_module("build_stage01_repair_packet_for_test", SCRIPT / "build_stage01_repair_packet.py")
run_stage01_codex_flow = load_module("run_stage01_codex_flow_for_test", SCRIPT / "run_stage01_codex_flow.py")
stage01_local_semantics = load_module("stage01_local_semantics_for_test", SCRIPT / "stage01_local_semantics.py")
build_stage02_prompt_packet = load_module("build_stage02_prompt_packet_for_test", STORYBOARD / "build_stage02_prompt_packet.py")
write_stage02_outputs = load_module("write_stage02_outputs_for_test", STORYBOARD / "write_stage02_outputs.py")
new_storyboard_template = load_module("new_storyboard_template_for_test", STORYBOARD / "new_storyboard_template.py")
run_stage02_codex_flow = load_module("run_stage02_codex_flow_for_test", STORYBOARD / "run_stage02_codex_flow.py")
validate_storyboard = load_module("validate_storyboard_for_test", STORYBOARD / "validate_storyboard.py")
build_stage03_prompt_packet = load_module("build_stage03_prompt_packet_for_test", CHARACTER / "build_stage03_prompt_packet.py")
write_stage03_outputs = load_module("write_stage03_outputs_for_test", CHARACTER / "write_stage03_outputs.py")
new_character_bible_template = load_module("new_character_bible_template_for_test", CHARACTER / "new_character_bible_template.py")
run_stage03_codex_flow = load_module("run_stage03_codex_flow_for_test", CHARACTER / "run_stage03_codex_flow.py")
validate_character_bible = load_module("validate_character_bible_for_test", CHARACTER / "validate_character_bible.py")
build_stage04_prompt_packet = load_module("build_stage04_prompt_packet_for_test", KEYFRAME / "build_stage04_prompt_packet.py")
write_stage04_outputs = load_module("write_stage04_outputs_for_test", KEYFRAME / "write_stage04_outputs.py")
new_keyframe_prompts_template = load_module("new_keyframe_prompts_template_for_test", KEYFRAME / "new_keyframe_prompts_template.py")
run_stage04_codex_flow = load_module("run_stage04_codex_flow_for_test", KEYFRAME / "run_stage04_codex_flow.py")
stage04_local_semantics = load_module("stage04_local_semantics_for_test", KEYFRAME / "stage04_local_semantics.py")
validate_keyframe_prompts = load_module("validate_keyframe_prompts_for_test", KEYFRAME / "validate_keyframe_prompts.py")
new_keyframe_image_jobs = load_module("new_keyframe_image_jobs_for_test", IMAGES / "new_keyframe_image_jobs.py")
validate_keyframe_image_manifest = load_module("validate_keyframe_image_manifest_for_test", IMAGES / "validate_keyframe_image_manifest.py")
generate_placeholder_keyframe_images = load_module("generate_placeholder_keyframe_images_for_test", IMAGES / "generate_placeholder_keyframe_images.py")
sync_keyframe_image_manifest = load_module("sync_keyframe_image_manifest_for_test", IMAGES / "sync_keyframe_image_manifest.py")
rerun_top_prompt_patches = load_module("rerun_top_prompt_patches_for_test", IMAGES / "rerun_top_prompt_patches.py")
approve_stage05_review_queue = load_module("approve_stage05_review_queue_for_test", IMAGES / "approve_stage05_review_queue.py")
serve_stage05_review_workbench = load_module("serve_stage05_review_workbench_for_test", IMAGES / "serve_stage05_review_workbench.py")
new_video_clip_jobs = load_module("new_video_clip_jobs_for_test", VIDEOCLIPS / "new_video_clip_jobs.py")
validate_video_clip_manifest = load_module("validate_video_clip_manifest_for_test", VIDEOCLIPS / "validate_video_clip_manifest.py")
generate_placeholder_video_clips = load_module("generate_placeholder_video_clips_for_test", VIDEOCLIPS / "generate_placeholder_video_clips.py")
sync_video_clip_manifest = load_module("sync_video_clip_manifest_for_test", VIDEOCLIPS / "sync_video_clip_manifest.py")
new_audio_jobs = load_module("new_audio_jobs_for_test", AUDIO / "new_audio_jobs.py")
validate_audio_manifest = load_module("validate_audio_manifest_for_test", AUDIO / "validate_audio_manifest.py")
generate_placeholder_audio = load_module("generate_placeholder_audio_for_test", AUDIO / "generate_placeholder_audio.py")
sync_audio_manifest = load_module("sync_audio_manifest_for_test", AUDIO / "sync_audio_manifest.py")
new_assembly_manifest = load_module("new_assembly_manifest_for_test", ASSEMBLY / "new_assembly_manifest.py")
validate_assembly_manifest = load_module("validate_assembly_manifest_for_test", ASSEMBLY / "validate_assembly_manifest.py")
assemble_with_ffmpeg = load_module("assemble_with_ffmpeg_for_test", ASSEMBLY / "assemble_with_ffmpeg.py")
sync_assembly_manifest = load_module("sync_assembly_manifest_for_test", ASSEMBLY / "sync_assembly_manifest.py")
new_qa_manifest = load_module("new_qa_manifest_for_test", QA / "new_qa_manifest.py")
validate_qa_manifest = load_module("validate_qa_manifest_for_test", QA / "validate_qa_manifest.py")
package_delivery = load_module("package_delivery_for_test", QA / "package_delivery.py")
update_project_manifest = load_module("update_project_manifest_for_test", PIPELINE / "update_project_manifest.py")
show_creator_home = load_module("show_creator_home_for_test", PIPELINE / "show_creator_home.py")
continue_pipeline = load_module("continue_pipeline_for_test", PIPELINE / "continue_pipeline.py")
run_stage01_from_locked_brief = load_module("run_stage01_from_locked_brief_for_test", PIPELINE / "run_stage01_from_locked_brief.py")
run_stage02_from_confirmed_script = load_module("run_stage02_from_confirmed_script_for_test", PIPELINE / "run_stage02_from_confirmed_script.py")
run_stage03_from_confirmed_storyboard = load_module("run_stage03_from_confirmed_storyboard_for_test", PIPELINE / "run_stage03_from_confirmed_storyboard.py")
run_stage04_from_confirmed_character_bible = load_module("run_stage04_from_confirmed_character_bible_for_test", PIPELINE / "run_stage04_from_confirmed_character_bible.py")
pipeline_blueprints = load_module("pipeline_blueprints_for_test", ROOT / "scripts" / "pipeline_blueprints.py")


def load_example_brief() -> dict:
    return json.loads((TEMPLATES / "project_brief.draft.example.json").read_text(encoding="utf-8"))


def _write_test_png(path: Path, *, size: tuple[int, int] = (64, 96), color: tuple[int, int, int] = (128, 120, 112)) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color=color).save(path, format="PNG")


def load_rainy_store_brief(project_dir: Path) -> dict:
    brief = load_example_brief()
    brief.update({
        "schema_version": "0.5.0",
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-30T14:20:12+08:00",
    })
    brief["user_answers"] = {
        "idea": "一位20岁出头的女孩在雨夜便利店门口把最后一把伞留给陌生人，自己淋着雨走远，回头发现门口多了一杯热可可",
        "target_duration": "12秒",
        "genre": "治愈",
        "style": "写实电影感",
        "visual_spec": "9:16 竖屏 1080P",
        "characters": "有固定主角/人物",
        "voice": "只需要旁白",
        "music": "需要 underscore",
        "final_output": "合成粗剪成片",
    }
    brief["normalized"].update({
        "idea": "一位20岁出头的女孩在雨夜便利店门口把最后一把伞留给陌生人，自己淋着雨走远，回头发现门口多了一杯热可可",
        "target_duration_sec": 12,
        "target_duration_label": "12秒",
        "genre": "治愈",
        "style": "写实电影感",
        "aspect_ratio": "9:16",
        "aspect_ratio_label": "9:16 竖屏",
        "resolution": "1080P",
        "resolution_label": "1080P",
        "characters_mode": "有固定主角/人物",
        "characters_required": True,
        "voice_mode": "只需要旁白",
        "voice_required": True,
        "music_mode": "需要",
        "music_profile": "underscore",
        "music_required": True,
        "final_output": "合成粗剪成片",
    })
    return brief


def load_music_video_plateau_brief(project_dir: Path) -> dict:
    brief = load_example_brief()
    brief.update({
        "schema_version": "0.5.0",
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-06-02T20:36:00+08:00",
    })
    idea = (
        "一位遭遇30岁职业危机与精神内耗的城市景观规划师，逃离钢筋水泥，驱车前往川西的高原旷野。"
        "在修缮一间濒临倒闭的藏式民宿过程中，她与当地的野生动物巡护员相识。"
        "在雪山、草地与星空之间，她不仅重新找到了生活的步调，也见证了人与自然最真实的羁绊。"
    )
    brief["user_answers"] = {
        "idea": idea,
        "target_duration": "B",
        "genre": "P",
        "style": "A",
        "visual_spec": "16:9 + 1080P",
        "characters": "C",
        "voice": "A",
        "music": "B1",
        "final_output": "F",
    }
    brief["normalized"].update({
        "idea": idea,
        "target_duration_sec": 30,
        "target_duration_label": "30秒",
        "genre": "音乐MV",
        "style": "写实电影感",
        "aspect_ratio": "16:9",
        "aspect_ratio_label": "16:9 横屏",
        "resolution": "1080P",
        "resolution_label": "1080P",
        "characters_mode": "由模型根据故事自动判断",
        "characters_required": "auto",
        "voice_mode": "不需要配音",
        "voice_required": False,
        "music_mode": "需要，歌曲（song）",
        "music_profile": "song",
        "music_required": True,
        "final_output": "合成粗剪成片",
    })
    return brief


def write_stage01_llm_output(script_dir: Path, llm_output: dict) -> Path:
    path = script_dir / "stage01_llm_output.json"
    path.write_text(json.dumps(llm_output, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def seed_confirmed_stage_chain(project_dir: Path) -> dict[str, Path]:
    intake_dir = project_dir / "00_intake"
    script_dir = project_dir / "01_script"
    storyboard_dir = project_dir / "02_storyboard"
    character_dir = project_dir / "03_characters"
    keyframe_dir = project_dir / "04_keyframes"
    for path in [intake_dir, script_dir, storyboard_dir, character_dir, keyframe_dir]:
        path.mkdir(parents=True, exist_ok=True)

    locked_brief = intake_dir / "project_brief.locked.json"
    brief = load_example_brief()
    brief.update({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-06-02T23:30:00+08:00",
    })
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    script_json = script_dir / "script.json"
    script = json.loads((TEMPLATES / "script.example.json").read_text(encoding="utf-8"))
    script.update({
        "project_id": project_dir.name,
        "source_brief": str(locked_brief).replace("\\", "/"),
        "status": "confirmed",
        "allowed_next_stage": "STAGE_02_STORYBOARD",
    })
    script_json.write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")

    storyboard_json = storyboard_dir / "storyboard.json"
    storyboard = json.loads((TEMPLATES / "storyboard.example.json").read_text(encoding="utf-8"))
    storyboard.update({
        "project_id": project_dir.name,
        "source_brief": str(locked_brief).replace("\\", "/"),
        "source_script": str(script_json).replace("\\", "/"),
        "status": "confirmed",
        "allowed_next_stage": "STAGE_03_CHARACTER_BIBLE",
    })
    storyboard_json.write_text(json.dumps(storyboard, ensure_ascii=False, indent=2), encoding="utf-8")

    character_json = character_dir / "character_bible.json"
    character_bible = json.loads((TEMPLATES / "character_bible.example.json").read_text(encoding="utf-8"))
    character_bible.update({
        "project_id": project_dir.name,
        "source_brief": str(locked_brief).replace("\\", "/"),
        "source_script": str(script_json).replace("\\", "/"),
        "source_storyboard": str(storyboard_json).replace("\\", "/"),
        "status": "confirmed",
        "allowed_next_stage": "STAGE_04_KEYFRAME_PROMPTS",
    })
    character_json.write_text(json.dumps(character_bible, ensure_ascii=False, indent=2), encoding="utf-8")

    keyframe_json = keyframe_dir / "keyframe_prompts.json"
    keyframe = json.loads((TEMPLATES / "keyframe_prompts.example.json").read_text(encoding="utf-8"))
    keyframe.update({
        "project_id": project_dir.name,
        "source_brief": str(locked_brief).replace("\\", "/"),
        "source_script": str(script_json).replace("\\", "/"),
        "source_storyboard": str(storyboard_json).replace("\\", "/"),
        "source_character_bible": str(character_json).replace("\\", "/"),
        "status": "confirmed",
        "allowed_next_stage": "STAGE_05_KEYFRAME_IMAGES",
    })
    keyframe_json.write_text(json.dumps(keyframe, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "locked_brief": locked_brief,
        "script_json": script_json,
        "storyboard_json": storyboard_json,
        "character_json": character_json,
        "keyframe_json": keyframe_json,
    }


def make_stage02_llm_output_from_example() -> dict:
    data = json.loads((TEMPLATES / "storyboard.example.json").read_text(encoding="utf-8"))
    for key in ["schema_version", "stage", "project_id", "source_brief", "source_script", "shot_count", "allowed_next_stage"]:
        data.pop(key, None)
    return data


def make_stage03_llm_output_from_example() -> dict:
    data = json.loads((TEMPLATES / "character_bible.example.json").read_text(encoding="utf-8"))
    for key in [
        "schema_version",
        "stage",
        "project_id",
        "source_brief",
        "source_script",
        "source_storyboard",
        "reference_image_plan",
        "reference_image_status",
        "stage05_execution_readiness",
        "allowed_next_stage",
    ]:
        data.pop(key, None)
    return data


def make_stage04_llm_output_from_example() -> dict:
    data = json.loads((TEMPLATES / "keyframe_prompts.example.json").read_text(encoding="utf-8"))
    for key in [
        "schema_version",
        "stage",
        "project_id",
        "source_brief",
        "source_script",
        "source_storyboard",
        "source_character_bible",
        "reference_image_status",
        "stage05_execution_readiness",
        "allowed_next_stage",
    ]:
        data.pop(key, None)
    return data


def make_stage02_llm_output_for_rainy_store() -> dict:
    return {
        "status": "draft",
        "target_duration_sec": 12,
        "shots": [
            {
                "shot_id": "S001",
                "start": "00:00",
                "end": "00:03",
                "duration_sec": 3,
                "scene": "雨夜便利店门口",
                "location": "便利店门口",
                "weather": "雨夜",
                "key_prop": "最后一把伞",
                "camera": "wide shot",
                "composition": "雨夜便利店门口和门廊灯牌先建立出来，20岁出头的女孩与最后一把伞同框。",
                "action": "20岁出头的女孩撑着最后一把伞站在便利店门廊边。",
                "emotion": "安静",
                "dialogue": "",
                "voiceover": "雨声先把门口的寒意铺满。",
                "sound_music": "underscore: 低温感钢琴和雨声一起进入",
                "transition_to_next": "cut",
                "production_note": "便利店门口、最后一把伞和主角服装要稳定。",
            },
            {
                "shot_id": "S002",
                "start": "00:03",
                "end": "00:06",
                "duration_sec": 3,
                "scene": "雨夜便利店门口",
                "location": "便利店门口",
                "weather": "雨夜",
                "key_prop": "最后一把伞",
                "camera": "medium shot",
                "composition": "主角抬手把最后一把伞递出去，收伞人保持次要、模糊和不抢戏。",
                "action": "她把最后一把伞递给更需要的人。",
                "emotion": "克制善意",
                "dialogue": "",
                "voiceover": "她把最后一把伞先让给别人。",
                "sound_music": "underscore: 雨滴打伞面的声音更明显",
                "transition_to_next": "cut",
                "production_note": "主角仍必须是20岁出头的女孩，收伞人只能作为次要陪体。",
            },
            {
                "shot_id": "S003",
                "start": "00:06",
                "end": "00:09",
                "duration_sec": 3,
                "scene": "雨夜街边",
                "location": "便利店门口",
                "weather": "雨夜",
                "key_prop": "无",
                "camera": "back shot",
                "composition": "她淋着雨离开门口，背影被雨幕压得更冷，便利店霓虹还留在后方。",
                "action": "她淋着雨走远，没有回头。",
                "emotion": "落寞余温",
                "dialogue": "",
                "voiceover": "她把冷意留给自己，继续往雨里走。",
                "sound_music": "underscore: 配乐压低，只留雨声和脚步",
                "transition_to_next": "cut",
                "production_note": "保持主角长相、发型和服装轮廓稳定，不要漂移成其他人。",
            },
            {
                "shot_id": "S004",
                "start": "00:09",
                "end": "00:12",
                "duration_sec": 3,
                "scene": "雨夜便利店门口",
                "location": "便利店门口",
                "weather": "雨夜",
                "key_prop": "热可可",
                "camera": "close-up",
                "composition": "她回头时，便利店门口台阶上的热可可在冷雨里冒着热气。",
                "action": "她回头看见门口多了一杯热可可。",
                "emotion": "意外回暖",
                "dialogue": "",
                "voiceover": "被送出去的温暖，又悄悄回来了。",
                "sound_music": "underscore: 配乐轻轻回暖",
                "transition_to_next": "fade out",
                "production_note": "热可可必须清楚可见，作为结尾情绪落点。",
            },
        ],
        "self_check": {
            "matches_locked_brief": True,
            "matches_script": True,
            "duration_fits": True,
            "ready_for_character_stage": True,
            "notes": [],
        },
    }


def make_stage03_llm_output_for_rainy_store() -> dict:
    return {
        "status": "draft",
        "characters": [
            {
                "character_id": "CHAR_001",
                "name": "20岁出头的女孩",
                "role": "main",
                "age": "20岁出头",
                "gender_presentation": "female",
                "appearance": {
                    "face": "清秀自然，雨夜里神情克制但柔软",
                    "hair": "被雨水和夜风打湿的黑色长发",
                    "body": "身形纤细，动作偏轻",
                    "clothing": "简单外套与长裙，雨夜下轮廓稳定",
                    "accessories": "最后一把伞、热可可纸杯"
                },
                "personality": "安静、善良、习惯把情绪留给自己",
                "emotional_arc": ["安静", "克制善意", "落寞余温", "意外回暖"],
                "voice_profile": {
                    "needed": True,
                    "suggested_voice": "年轻女性，温柔克制，略带雨夜冷感"
                },
                "visual_consistency_prompt": "same early-20s girl, same wet black hair, same simple outerwear and dress silhouette, same lonely but gentle expression, rainy convenience-store doorway",
                "negative_consistency_prompt": "different face, different hair, extra protagonist, outfit drift, deformed hands, extra limbs",
                "performance_profile": {
                    "baseline_expression": "安静",
                    "movement_style": "slow and restrained",
                    "gesture_rules": [
                        "动作幅度偏小",
                        "递伞和回头都要自然克制",
                        "不要出现夸张表演"
                    ],
                    "dialogue_delivery": "自然、轻声、可停顿",
                    "continuity_anchor": "20岁出头的女孩 / 雨夜便利店门口 / 最后一把伞 / 热可可"
                }
            }
        ],
        "reference_image_required": True,
        "self_check": {
            "matches_locked_brief": True,
            "matches_script": True,
            "matches_storyboard": True,
            "ready_for_keyframe_stage": True,
            "notes": [],
        },
    }


def make_stage04_llm_output_for_rainy_store() -> dict:
    return {
        "status": "draft",
        "prompt_language": "English generation prompts with Chinese review notes",
        "visual_strategy": {
            "keyframe_mode": "start_and_end_keyframes_per_shot",
            "video_mode": "image_to_video_per_shot",
            "continuity_strategy": "reuse character consistency prompts and adjacent-shot transition requirements"
        },
        "shot_prompts": [
            {
                "shot_id": "S001",
                "duration_sec": 3,
                "characters": ["CHAR_001"],
                "scene_summary": "地点：便利店门口 / 天气：雨夜 / 动作：20岁出头的女孩撑着最后一把伞站在便利店门廊边。 / 道具：最后一把伞 / 情绪：安静 / 构图重点：便利店门口和雨夜门廊先建立出来。",
                "intent_summary": "这个镜头要在便利店门口里抓住“撑着最后一把伞站在门廊边”这一瞬间，传达安静，让最后一把伞成为情绪支点。",
                "story_anchor_bundle": {
                    "location": "便利店门口",
                    "weather": "雨夜",
                    "key_prop": "最后一把伞",
                    "emotion": "安静",
                    "composition_focus": "便利店门口和雨夜门廊先建立出来。"
                },
                "start_keyframe_prompt": "Character identity anchor: same early-20s girl, wet black hair, simple outerwear and dress silhouette. Primary protagonist must remain 20岁出头的女孩 in every frame. rainy convenience-store doorway, last umbrella, quiet emotion, vertical 9:16 composition",
                "end_keyframe_prompt": "cinematic continuation of the rainy convenience-store doorway moment, do not swap protagonist identity, preserve the same girl, same umbrella, same doorway light, same wet hair silhouette",
                "motion_prompt": "The girl holds the last umbrella quietly under the convenience-store awning; gentle natural motion, rain streaks, stable identity and outfit continuity.",
                "camera_prompt": "wide shot",
                "lighting_prompt": "cold rainy night practical light, convenience-store doorway glow, wet ground reflections",
                "style_prompt": "realistic cinematic healing short film, restrained rain-night mood",
                "consistency_prompt": "Character identity anchor: same early-20s girl, same wet black hair, same simple outerwear and dress silhouette, same lonely but gentle expression; Primary protagonist must remain 20岁出头的女孩 in every frame.",
                "identity_anchor_prompt": "Character identity anchor: same early-20s girl, same wet black hair, same simple outerwear and dress silhouette.",
                "negative_prompt": "watermark, logo, subtitles, duplicate person, extra limbs, deformed hands, face drift, outfit drift",
                "image_generation_notes": "Keep the rainy convenience-store doorway and last umbrella readable.",
                "video_generation_notes": "Preserve stable identity and low-amplitude movement.",
                "performance_prompt": "Quiet and restrained performance, very small movements.",
                "dialogue_delivery_prompt": "",
                "dependencies": {
                    "reference_images": ["03_characters/reference_images/CHAR_001_primary.png"],
                        "previous_shot_id": None,
                    "next_shot_id": "S002"
                }
            },
            {
                "shot_id": "S002",
                "duration_sec": 3,
                "characters": ["CHAR_001"],
                "scene_summary": "地点：便利店门口 / 天气：雨夜 / 动作：她把最后一把伞递给更需要的人。 / 道具：最后一把伞 / 情绪：克制善意 / 构图重点：递伞动作清晰，收伞人必须次要。",
                "intent_summary": "这个镜头要在便利店门口里抓住“递出最后一把伞”这一瞬间，传达克制善意，让最后一把伞成为情绪支点。",
                "story_anchor_bundle": {
                    "location": "便利店门口",
                    "weather": "雨夜",
                    "key_prop": "最后一把伞",
                    "emotion": "克制善意",
                    "composition_focus": "递伞动作清晰，收伞人必须次要。"
                },
                "start_keyframe_prompt": "Primary protagonist must remain 20岁出头的女孩. She hands the last umbrella forward in the rainy convenience-store doorway; a secondary receiver may exist but stays less dominant.",
                "end_keyframe_prompt": "Continue the umbrella handoff, do not swap protagonist identity, do not let the receiver become the lead.",
                "motion_prompt": "Small controlled handoff motion, rain and doorway light remain stable.",
                "camera_prompt": "medium shot",
                "lighting_prompt": "rainy night doorway practicals",
                "style_prompt": "realistic cinematic healing short film, restrained emotion",
                "consistency_prompt": "Character identity anchor: same early-20s girl, same wet black hair, same outfit; receiver stays secondary.",
                "identity_anchor_prompt": "Character identity anchor: same early-20s girl, same wet black hair, same outfit.",
                "negative_prompt": "duplicate protagonist, face drift, extra limbs, deformed hands",
                "image_generation_notes": "The umbrella exchange must read clearly.",
                "video_generation_notes": "Keep exactly one readable lead protagonist.",
                "performance_prompt": "Quiet handoff, emotionally restrained.",
                "dialogue_delivery_prompt": "",
                "dependencies": {
                    "reference_images": ["03_characters/reference_images/CHAR_001_primary.png"],
                    "previous_shot_id": "S001",
                    "next_shot_id": "S003"
                }
            },
            {
                "shot_id": "S003",
                "duration_sec": 3,
                "characters": ["CHAR_001"],
                "scene_summary": "地点：便利店门口 / 天气：雨夜 / 动作：她淋着雨走远，没有回头。 / 道具：无 / 情绪：落寞余温 / 构图重点：背影和雨幕压低情绪。",
                "intent_summary": "这个镜头要在便利店门口外的雨夜里抓住“淋着雨走远”这一瞬间，传达落寞余温。",
                "story_anchor_bundle": {
                    "location": "便利店门口",
                    "weather": "雨夜",
                    "key_prop": "",
                    "emotion": "落寞余温",
                    "composition_focus": "背影和雨幕压低情绪。"
                },
                "start_keyframe_prompt": "The same girl walks away alone into the rain outside the convenience-store doorway, no face or outfit drift.",
                "end_keyframe_prompt": "Continue the lonely rainy walk, keep the same protagonist identity and silhouette.",
                "motion_prompt": "Slow back-view departure with steady rain and small body movement.",
                "camera_prompt": "back shot",
                "lighting_prompt": "wet street reflections, cold rain-night ambience",
                "style_prompt": "realistic cinematic healing short film, rain-night melancholy",
                "consistency_prompt": "Character identity anchor: same early-20s girl, same wet black hair, same outfit silhouette.",
                "identity_anchor_prompt": "Character identity anchor: same early-20s girl, same wet black hair, same outfit silhouette.",
                "negative_prompt": "extra person, silhouette drift, deformed legs, face drift",
                "image_generation_notes": "Rain and doorway neon must stay readable in the background.",
                "video_generation_notes": "Keep movement subtle and identity stable.",
                "performance_prompt": "Quiet departure, do not exaggerate sadness.",
                "dialogue_delivery_prompt": "",
                "dependencies": {
                    "reference_images": ["03_characters/reference_images/CHAR_001_primary.png"],
                    "previous_shot_id": "S002",
                    "next_shot_id": "S004"
                }
            },
            {
                "shot_id": "S004",
                "duration_sec": 3,
                "characters": ["CHAR_001"],
                "scene_summary": "地点：便利店门口 / 天气：雨夜 / 动作：她回头看见门口多了一杯热可可。 / 道具：热可可 / 情绪：意外回暖 / 构图重点：热可可和门口台阶成为结尾落点。",
                "intent_summary": "这个镜头要在便利店门口里抓住“看见热可可”这一瞬间，传达意外回暖，让热可可成为情绪支点。",
                "story_anchor_bundle": {
                    "location": "便利店门口",
                    "weather": "雨夜",
                    "key_prop": "热可可",
                    "emotion": "意外回暖",
                    "composition_focus": "热可可和门口台阶成为结尾落点。"
                },
                "start_keyframe_prompt": "The same girl turns back toward the convenience-store doorway and notices a cup of hot cocoa on the step, rainy night, gentle emotional release.",
                "end_keyframe_prompt": "Hold on the hot cocoa and the girl's softened reaction, keep the same face and outfit.",
                "motion_prompt": "Small head turn and pause, warm steam from the hot cocoa becomes visible in the cold rain.",
                "camera_prompt": "close-up",
                "lighting_prompt": "doorway practical light with visible warm steam",
                "style_prompt": "realistic cinematic healing short film, quiet warm ending",
                "consistency_prompt": "Character identity anchor: same early-20s girl, same wet black hair, same outfit, same rainy doorway context.",
                "identity_anchor_prompt": "Character identity anchor: same early-20s girl, same wet black hair, same outfit.",
                "negative_prompt": "extra protagonist, wrong prop, face drift, outfit drift",
                "image_generation_notes": "Hot cocoa must be clearly visible as the emotional payoff prop.",
                "video_generation_notes": "End on a restrained emotional release with stable identity.",
                "performance_prompt": "Subtle surprise and warmth, no exaggerated smile.",
                "dialogue_delivery_prompt": "",
                "dependencies": {
                    "reference_images": ["03_characters/reference_images/CHAR_001_primary.png"],
                    "previous_shot_id": "S003",
                        "next_shot_id": None
                }
            }
        ],
        "transition_prompts": [
            {
                "transition_id": "T001",
                "from_shot_id": "S001",
                "to_shot_id": "S002",
                "transition_type": "cut",
                "transition_motion_prompt": "Continue from waiting under the awning into the umbrella handoff without changing the girl's identity.",
                "continuity_requirements": ["same character face and hair", "same outfit", "same rainy convenience-store doorway"]
            },
            {
                "transition_id": "T002",
                "from_shot_id": "S002",
                "to_shot_id": "S003",
                "transition_type": "cut",
                "transition_motion_prompt": "Move from the handoff to the lonely departure while keeping the same girl and rainy doorway context.",
                "continuity_requirements": ["same character face and hair", "same outfit", "same rain-night lighting"]
            },
            {
                "transition_id": "T003",
                "from_shot_id": "S003",
                "to_shot_id": "S004",
                "transition_type": "fade out",
                "transition_motion_prompt": "Turn from the rainy back-view walk to the hot-cocoa reveal while preserving the same girl and emotional arc.",
                "continuity_requirements": ["same character face and hair", "same outfit", "same emotional progression"]
            }
        ],
        "global_negative_prompt": "watermark, logo, subtitles, duplicate person, extra limbs, deformed hands, face drift, outfit drift",
        "self_check": {
            "matches_locked_brief": True,
            "matches_script": True,
            "matches_storyboard": True,
            "uses_character_consistency": True,
            "covers_all_storyboard_shots": True,
            "ready_for_image_generation": True,
            "notes": [],
        },
    }


class _FakeCompletedProcess:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class _FakeCodexExec:
    def __init__(self, payloads: list[dict]) -> None:
        self.payloads = list(payloads)
        self.calls: list[dict[str, object]] = []

    def __call__(self, cmd, input=None, text=None, capture_output=None, cwd=None, encoding=None):  # noqa: ANN001
        assert self.payloads, "Fake codex exec received more calls than prepared payloads"
        output_flag_index = cmd.index("--output-last-message")
        output_path = Path(cmd[output_flag_index + 1])
        payload = self.payloads.pop(0)
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        self.calls.append({
            "cmd": list(cmd),
            "cwd": cwd,
            "input": input,
        })
        return _FakeCompletedProcess(returncode=0)


def make_stage01_llm_output_for_example_brief() -> dict:
    return {
        "title_candidates": ["落日之后", "海风把话带走"],
        "selected_title": "落日之后",
        "logline": "一个20岁出头的女孩在落日海滩独自散步，在海浪与晚霞之间慢慢完成一次安静的告别。",
        "theme": "释怀旧情绪，在温暖黄昏里重新向前走",
        "protagonist_state": "她表面平静，内心仍带着没有说出口的情绪余波",
        "narrative_movement": "从独自沉浸到在海风与脚步里慢慢把情绪放下",
        "ending_direction": "她继续沿着潮线往前走，情绪不再回头",
        "avoid": ["不要出现第二主角", "不要写成对白驱动短剧"],
        "characters": [
            {
                "name": "20岁出头的女孩",
                "age": "20岁出头",
                "role": "main",
                "identity_anchor": "独自在黄昏海边散步、正在消化情绪的年轻女生",
            }
        ],
        "settings": ["落日余辉海滩", "潮线边的湿沙地"],
        "beats": [
            {
                "beat_id": "B01",
                "start": "00:00",
                "end": "00:07",
                "summary": "黄昏海面被拉开，她沿着潮线慢慢往前走。",
                "emotion": "克制",
                "visual": "竖屏建立镜头里，晚霞铺在海面上，她穿着长裙独自走在潮线边，脚步很轻。",
                "voiceover": "黄昏把白天的喧闹一点点收走。",
                "dialogue": "",
                "music_cue": "underscore: 温暖轻柔的氛围音乐与海浪声一起铺开",
            },
            {
                "beat_id": "B02",
                "start": "00:07",
                "end": "00:15",
                "summary": "她停下来望向海平线，让情绪在风里松动。",
                "emotion": "迟疑",
                "visual": "镜头从侧后方贴近她的肩颈与发梢，海风吹动长裙，她望着被夕光压低的海平线。",
                "voiceover": "有些话没有说出口，也会被风慢慢带远。",
                "dialogue": "",
                "music_cue": "underscore: 配乐轻轻抬起，保留明显海风与海浪环境音",
            },
            {
                "beat_id": "B03",
                "start": "00:15",
                "end": "00:23",
                "summary": "她低头看见脚边的贝壳，像看见一段已经可以放下的回忆。",
                "emotion": "松动",
                "visual": "特写她弯腰捡起一枚被海水打湿的贝壳，指尖停顿一下，再轻轻握住。",
                "voiceover": "原来真正的告别，不一定需要回头。",
                "dialogue": "",
                "music_cue": "underscore: 配乐在中段保持克制，给海水细节留出空间",
            },
            {
                "beat_id": "B04",
                "start": "00:23",
                "end": "00:30",
                "summary": "她把贝壳放回海边，继续朝前走，状态终于变轻。",
                "emotion": "释怀",
                "visual": "远景里她把贝壳放回湿沙地，随后转身继续向前，背影被落日拉成长长一条线。",
                "voiceover": "当脚步继续向前，心也终于开始重新呼吸。",
                "dialogue": "",
                "music_cue": "underscore: 配乐温柔收束，留下海浪声托住尾镜头",
            },
        ],
        "self_check": {
            "matches_locked_brief": True,
            "duration_fits": True,
            "genre_style_fits": True,
            "aspect_ratio_fits": True,
            "character_requirement_fits": True,
            "voice_fits": True,
            "music_fits": True,
            "final_output_scope_fits": True,
            "ready_for_storyboard": True,
            "notes": [],
        },
    }


def make_stage01_llm_output_for_rainy_store() -> dict:
    return {
        "title_candidates": ["雨夜留下的伞", "便利店门口的热可可"],
        "selected_title": "雨夜留下的伞",
        "logline": "一个20岁出头的女孩在雨夜把最后一把伞留给陌生人，自己走进雨里，却在回头时收到一杯热可可。",
        "theme": "微小善意会在寒冷时刻悄悄回到人身边",
        "protagonist_state": "她习惯自己扛住情绪，也习惯在冷雨里先顾别人",
        "narrative_movement": "从把温暖让出去到在雨夜重新接住一份被返还的善意",
        "ending_direction": "她捧着热可可站在雨夜便利店门口，情绪被轻轻安住",
        "avoid": ["不要写成多人对话短剧", "不要脱离雨夜便利店门口这个核心场景"],
        "characters": [
            {
                "name": "20岁出头的女孩",
                "age": "20岁出头",
                "role": "main",
                "identity_anchor": "在雨夜便利店门口把最后一把伞递出去的年轻女孩",
            }
        ],
        "settings": ["雨夜便利店门口", "便利店门廊下"],
        "beats": [
            {
                "beat_id": "B01",
                "start": "00:00",
                "end": "00:03",
                "summary": "雨夜便利店门口，她撑着最后一把伞站在门廊边。",
                "emotion": "安静",
                "visual": "竖屏建立镜头先交代雨夜便利店门口，霓虹落在湿地上，她撑着最后一把伞站在门廊边。",
                "voiceover": "雨下得很急，她还是把脚步停在了门口。",
                "dialogue": "",
                "music_cue": "underscore: 低温感钢琴与雨声一起铺开",
            },
            {
                "beat_id": "B02",
                "start": "00:03",
                "end": "00:06",
                "summary": "她把最后一把伞递给门口更需要的人。",
                "emotion": "决心",
                "visual": "近景里，她把最后一把伞递向画外，只留下手与伞的交换动作，不让第二主角喧宾夺主。",
                "voiceover": "有些决定，只在一瞬间就做好了。",
                "dialogue": "",
                "music_cue": "underscore: 配乐轻轻向上抬一格，保留雨滴打伞面的声音",
            },
            {
                "beat_id": "B03",
                "start": "00:06",
                "end": "00:09",
                "summary": "她淋着雨往前走，背影有点冷也有点倔强。",
                "emotion": "落寞",
                "visual": "背影镜头里，她离开便利店门口走进雨幕，肩线和裙摆很快被雨水打湿。",
                "voiceover": "她没回头，只让雨水把肩膀一点点打凉。",
                "dialogue": "",
                "music_cue": "underscore: 配乐压低，让脚步声和雨声更清楚",
            },
            {
                "beat_id": "B04",
                "start": "00:09",
                "end": "00:12",
                "summary": "她回头时，门口多了一杯热可可，善意被悄悄送回来了。",
                "emotion": "被安慰",
                "visual": "她回头望向便利店门口，门廊台阶上放着一杯热可可，热气在冷雨里很明显。",
                "voiceover": "原来留给别人的温暖，也会换一种方式回来。",
                "dialogue": "",
                "music_cue": "underscore: 配乐温柔收束，把情绪落在热可可的热气上",
            },
        ],
        "self_check": {
            "matches_locked_brief": True,
            "duration_fits": True,
            "genre_style_fits": True,
            "aspect_ratio_fits": True,
            "character_requirement_fits": True,
            "voice_fits": True,
            "music_fits": True,
            "final_output_scope_fits": True,
            "ready_for_storyboard": True,
            "notes": [],
        },
    }


def make_stage01_llm_output_for_music_video() -> dict:
    return {
        "title_candidates": ["风穿过川西", "在高原重新呼吸"],
        "selected_title": "风穿过川西",
        "logline": "她离开城市，在川西高原的风、雪山与草地之间重新找回呼吸与生活步调。",
        "theme": "逃离长期内耗，在人与自然之间重新找回身体和情绪的真实节奏",
        "protagonist_state": "30岁的城市景观规划师正处在职业危机与精神消耗交叠的失衡边缘",
        "narrative_movement": "从逃离钢筋水泥到在高原重新与世界建立真实联系",
        "ending_direction": "在星空下彻底放慢呼吸，重新接住自己的生活",
        "avoid": ["不要写成对白驱动短剧", "不要额外生成旁白或对白"],
        "characters": [
            {
                "name": "城市景观规划师",
                "age": "30岁",
                "role": "main",
                "identity_anchor": "长期被城市工作与精神内耗拖拽的女性景观规划师",
            },
            {
                "name": "野生动物巡护员",
                "age": "",
                "role": "supporting",
                "identity_anchor": "熟悉高原节奏、与自然保持稳定连接的当地巡护员",
            },
        ],
        "settings": ["川西高原旷野", "藏式民宿", "雪山草地", "高原星空"],
        "beats": [
            {
                "beat_id": "B01",
                "start": "00:00",
                "end": "00:07",
                "summary": "她离开钢筋水泥，独自驱车驶向川西高原旷野。",
                "emotion": "压抑",
                "visual": "横屏建立镜头从密集城市切到通往川西高原旷野的公路，车窗外的天空越来越开阔，她独自握着方向盘前行。",
                "voiceover": "",
                "dialogue": "",
                "music_cue": "song: 前奏铺开，环境音里保留车轮、风声和远处低频路噪",
            },
            {
                "beat_id": "B02",
                "start": "00:07",
                "end": "00:15",
                "summary": "在濒临倒闭的藏式民宿里，她开始修缮屋子，也开始让自己慢下来。",
                "emotion": "迟疑",
                "visual": "她在藏式民宿里修补木窗、擦拭旧桌面、搬动杂物，动作还带着城市惯性的紧绷。",
                "voiceover": "",
                "dialogue": "",
                "music_cue": "song: 主歌进入，配合修缮动作维持克制推进",
            },
            {
                "beat_id": "B03",
                "start": "00:15",
                "end": "00:23",
                "summary": "她与当地的野生动物巡护员并肩走进草地和雪山之间，第一次真正把视线从自己身上移开。",
                "emotion": "松动",
                "visual": "草地与雪山同框，她和野生动物巡护员一前一后穿过高原风口，远处偶尔闪过野生动物活动的痕迹。",
                "voiceover": "",
                "dialogue": "",
                "music_cue": "song: 副歌前段打开空间感，放大风声与脚步落地感",
            },
            {
                "beat_id": "B04",
                "start": "00:23",
                "end": "00:30",
                "summary": "雪山、草地与星空依次铺开，她终于重新找回自己的生活步调。",
                "emotion": "释怀",
                "visual": "雪山、草地与高原星空依次展开，她站在风里抬头呼吸，整个人的节奏终于慢下来。",
                "voiceover": "",
                "dialogue": "",
                "music_cue": "song: 副歌或尾奏收束，情绪落在开阔与释怀上",
            },
        ],
        "self_check": {
            "matches_locked_brief": True,
            "duration_fits": True,
            "genre_style_fits": True,
            "aspect_ratio_fits": True,
            "character_requirement_fits": True,
            "voice_fits": True,
            "music_fits": True,
            "final_output_scope_fits": True,
            "ready_for_storyboard": True,
            "notes": [],
        },
    }


def test_validate_project_brief_example() -> None:
    data = load_example_brief()
    ok, errors, warnings = validate_project_brief.validate(data, TEMPLATES / "project_brief.draft.example.json")
    assert ok, errors
    assert data["normalized"]["music_profile"] == "underscore"


def test_new_project_brief_template_generates_schema_compliant_draft(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260529_190842_project"
    intake_dir = project_dir / "00_intake"
    intake_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = project_dir / "project_manifest.json"
    manifest_path.write_text(json.dumps({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "current_stage": "STAGE_00_INTAKE",
        "brief_locked": False,
        "allowed_next_stage": None,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    draft_path = intake_dir / "project_brief.draft.json"
    assert new_project_brief_template.main(["new_project_brief_template.py", str(draft_path)]) == 0

    data = json.loads(draft_path.read_text(encoding="utf-8"))
    assert data["project_id"] == project_dir.name
    assert data["project_dir"] == str(project_dir).replace("\\", "/")
    ok, errors, warnings = validate_project_brief.validate(data, draft_path)
    assert ok, errors


def test_create_project_folder_uses_readable_slug_for_chinese_numeric_title(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", [
        "create_project_folder.py",
        "--root",
        str(tmp_path / "video_projects"),
        "--title",
        "一位20岁出头的女孩在落日余辉的海滩边散步",
    ])
    assert create_project_folder.main() == 0
    projects = list((tmp_path / "video_projects").iterdir())
    assert len(projects) == 1
    project_dir = projects[0]
    assert not project_dir.name.endswith("_20")
    assert not project_dir.name.endswith("_project")
    assert any("\u4e00" <= ch <= "\u9fff" for ch in project_dir.name.rsplit("_", 1)[-1])
    manifest = json.loads((project_dir / "project_manifest.json").read_text(encoding="utf-8"))
    assert manifest["project_title"] == "一位20岁出头的女孩在落日余辉的海滩边散步"
    assert validate_project_structure.main(["validate_project_structure.py", str(project_dir)]) == 0


def test_project_brief_must_match_containing_project_folder(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", [
        "create_project_folder.py",
        "--root",
        str(tmp_path / "video_projects"),
        "--project-id",
        "video_20260528_103000_sunset_beach_girl",
    ])
    assert create_project_folder.main() == 0
    project_dir = tmp_path / "video_projects" / "video_20260528_103000_sunset_beach_girl"
    draft_path = project_dir / "00_intake" / "project_brief.draft.json"

    data = load_example_brief()
    data["project_id"] = project_dir.name
    data["project_dir"] = str(project_dir).replace("\\", "/")
    draft_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    ok, errors, warnings = validate_project_brief.validate(data, draft_path)
    assert ok, errors

    data["project_id"] = "video_wrong_project"
    draft_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    ok, errors, warnings = validate_project_brief.validate(data, draft_path)
    assert not ok
    assert any("containing project folder" in e or "basename of project_dir" in e for e in errors)


def test_validate_project_brief_accepts_utf8_bom(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260529_190842_project"
    intake_dir = project_dir / "00_intake"
    intake_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = project_dir / "project_manifest.json"
    manifest_path.write_text(json.dumps({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "current_stage": "STAGE_00_INTAKE",
        "brief_locked": False,
        "allowed_next_stage": None,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    draft = load_example_brief()
    draft["project_id"] = project_dir.name
    draft["project_dir"] = str(project_dir).replace("\\", "/")
    draft_path = intake_dir / "project_brief.draft.json"
    draft_path.write_text("\ufeff" + json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8")

    assert validate_project_brief.main(["validate_project_brief.py", str(draft_path)]) == 0


def test_validate_script_example_final() -> None:
    data = json.loads((TEMPLATES / "script.example.json").read_text(encoding="utf-8"))
    ok, errors, warnings = validate_script.validate(data, mode="final")
    assert ok, errors


def test_new_script_template_generates_final_ready_draft(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260528_103000_sunset_beach_girl"
    intake_dir = project_dir / "00_intake"
    script_dir = project_dir / "01_script"
    intake_dir.mkdir(parents=True)
    script_dir.mkdir(parents=True)

    brief = load_example_brief()
    brief.update({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-28T10:35:00+08:00",
    })
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")
    write_stage01_llm_output(script_dir, make_stage01_llm_output_for_example_brief())

    script_json = script_dir / "script.json"
    assert new_script_template.main(["new_script_template.py", str(locked_brief), str(script_json)]) == 0

    script_data = json.loads(script_json.read_text(encoding="utf-8"))
    assert script_data["script"]["music_profile"] == "underscore"
    ok, errors, warnings = validate_script.validate(script_data, mode="draft")
    assert ok, errors
    ok, errors, warnings = validate_script.validate(script_data, mode="final")
    assert ok, errors
    assert script_data["title"]
    assert script_data["duration_plan"]["beats"]
    assert script_data["script"]["sections"]
    assert (script_dir / "story_direction.md").exists()
    assert (script_dir / "story_direction.json").exists()
    assert (script_dir / "plot_structure.md").exists()
    assert (script_dir / "plot_structure.json").exists()
    assert (script_dir / "script.md").exists()
    assert (script_dir / "script_review.md").exists()
    assert (script_dir / "stage01_prompt_packet.json").exists()
    assert (script_dir / "stage01_llm_output.json").exists()
    review_text = (script_dir / "script_review.md").read_text(encoding="utf-8")
    assert "1. 是否严格遵守 locked brief" in review_text
    assert "9. 是否可以进入 Stage 02 分镜拆解" in review_text


def test_new_script_template_requires_explicit_stage01_llm_output(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260528_103000_sunset_beach_girl"
    intake_dir = project_dir / "00_intake"
    script_dir = project_dir / "01_script"
    intake_dir.mkdir(parents=True)
    script_dir.mkdir(parents=True)

    brief = load_example_brief()
    brief.update({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-28T10:35:00+08:00",
    })
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    script_json = script_dir / "script.json"
    assert new_script_template.main(["new_script_template.py", str(locked_brief), str(script_json)]) == 1
    assert (script_dir / "stage01_prompt_packet.json").exists()
    assert not script_json.exists()


def test_stage01_preserves_explicit_age_location_and_song_profile_for_music_video(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260602_203600_30_mv"
    intake_dir = project_dir / "00_intake"
    script_dir = project_dir / "01_script"
    intake_dir.mkdir(parents=True)
    script_dir.mkdir(parents=True)

    brief = load_music_video_plateau_brief(project_dir)
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")
    write_stage01_llm_output(script_dir, make_stage01_llm_output_for_music_video())

    script_json = script_dir / "script.json"
    assert new_script_template.main(["new_script_template.py", str(locked_brief), str(script_json)]) == 0

    script_data = json.loads(script_json.read_text(encoding="utf-8"))
    assert script_data["characters"][0]["name"] == "城市景观规划师"
    assert script_data["characters"][0]["age"] == "30岁"
    assert "川西高原旷野" in script_data["settings"]
    assert "藏式民宿" in script_data["settings"]
    assert all(str(section.get("music_cue") or "").startswith("song:") for section in script_data["script"]["sections"])
    ok, errors, warnings = validate_script.validate(script_data, mode="final")
    assert ok, errors


def test_stage01_normalizes_natural_language_music_cues_to_locked_profile(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260602_220801_beach_walk"
    intake_dir = project_dir / "00_intake"
    script_dir = project_dir / "01_script"
    intake_dir.mkdir(parents=True)
    script_dir.mkdir(parents=True)

    brief = load_example_brief()
    brief.update({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-06-02T22:08:01+08:00",
    })
    brief["normalized"].update({
        "voice_mode": "不需要配音",
        "music_mode": "需要",
        "music_profile": "underscore",
    })
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    llm_output = make_stage01_llm_output_for_example_brief()
    llm_output["beats"][0]["music_cue"] = "极简低频铺底缓慢进入，稀薄环境氛围带一点冷感混响"
    llm_output["beats"][1]["music_cue"] = "underscore：配乐轻轻抬起，保留明显海风与海浪环境音"
    write_stage01_llm_output(script_dir, llm_output)

    script_json = script_dir / "script.json"
    assert new_script_template.main(["new_script_template.py", str(locked_brief), str(script_json)]) == 0

    script_data = json.loads(script_json.read_text(encoding="utf-8"))
    cues = [str(section.get("music_cue") or "") for section in script_data["script"]["sections"]]
    assert cues[0].startswith("underscore:")
    assert cues[1].startswith("underscore:")
    ok, errors, warnings = validate_script.validate(script_data, mode="final")
    assert ok, errors


def test_validate_script_rejects_song_profile_with_underscore_sections() -> None:
    data = json.loads((TEMPLATES / "script.example.json").read_text(encoding="utf-8"))
    data["script"]["music_profile"] = "song"
    data["script"]["sections"][0]["music_cue"] = "underscore: 背景配乐托住环境"
    ok, errors, warnings = validate_script.validate(data, mode="final")
    assert not ok
    assert any("music_cue must match" in error for error in errors)


def test_new_script_template_uses_existing_llm_output_when_present(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260602_203600_30_mv"
    intake_dir = project_dir / "00_intake"
    script_dir = project_dir / "01_script"
    intake_dir.mkdir(parents=True)
    script_dir.mkdir(parents=True)

    brief = load_music_video_plateau_brief(project_dir)
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")
    write_stage01_llm_output(script_dir, make_stage01_llm_output_for_music_video())

    script_json = script_dir / "script.json"
    assert new_script_template.main(["new_script_template.py", str(locked_brief), str(script_json)]) == 0
    script_data = json.loads(script_json.read_text(encoding="utf-8"))
    assert script_data["title"] == "风穿过川西"
    assert script_data["logline"].startswith("她离开城市")
    assert script_data["generation_meta"]["mode"] == "codex_llm_output"
    assert (script_dir / "stage01_prompt_packet.json").exists()
    ok, errors, warnings = validate_script.validate(script_data, mode="final")
    assert ok, errors


def test_new_script_template_writes_repair_packet_when_llm_output_fails_validation(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260602_203600_30_mv"
    intake_dir = project_dir / "00_intake"
    script_dir = project_dir / "01_script"
    intake_dir.mkdir(parents=True)
    script_dir.mkdir(parents=True)

    brief = load_music_video_plateau_brief(project_dir)
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    llm_output = {
        "title_candidates": ["风穿过川西"],
        "selected_title": "风穿过川西",
        "logline": "她离开城市，在高原重新呼吸。",
        "theme": "逃离内耗，重新找回呼吸",
        "protagonist_state": "她处在失衡边缘",
        "narrative_movement": "从逃离到释怀",
        "ending_direction": "在高原放下情绪",
        "avoid": ["不要额外生成旁白或对白"],
        "characters": [
            {
                "name": "城市景观规划师",
                "age": "30岁",
                "role": "main",
                "identity_anchor": "长期被工作消耗的女性景观规划师",
            }
        ],
        "settings": ["川西高原旷野", "藏式民宿"],
        "beats": [
            {
                "beat_id": "B01",
                "start": "00:00",
                "end": "00:30",
                "summary": "她离开城市。",
                "emotion": "压抑",
                "visual": "她在城市边缘上车。",
                "voiceover": "",
                "dialogue": "",
                "music_cue": "underscore: 背景配乐托住环境氛围",
            }
        ],
        "self_check": {
            "matches_locked_brief": True,
            "duration_fits": True,
            "genre_style_fits": True,
            "aspect_ratio_fits": True,
            "character_requirement_fits": True,
            "voice_fits": True,
            "music_fits": True,
            "final_output_scope_fits": True,
            "ready_for_storyboard": True,
            "notes": [],
        },
    }
    (script_dir / "stage01_llm_output.json").write_text(json.dumps(llm_output, ensure_ascii=False, indent=2), encoding="utf-8")

    script_json = script_dir / "script.json"
    assert new_script_template.main(["new_script_template.py", str(locked_brief), str(script_json)]) == 1
    assert (script_dir / "stage01_validation_errors.json").exists()
    assert (script_dir / "stage01_repair_packet.json").exists()


def test_run_stage01_codex_flow_generates_stage01_package_without_manual_llm_fill(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260528_103000_sunset_beach_girl"
    intake_dir = project_dir / "00_intake"
    script_dir = project_dir / "01_script"
    intake_dir.mkdir(parents=True)
    script_dir.mkdir(parents=True)

    brief = load_example_brief()
    brief.update({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-28T10:35:00+08:00",
    })
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    script_json = script_dir / "script.json"
    assert run_stage01_codex_flow.main([str(locked_brief), str(script_json)]) == 0

    assert (script_dir / "stage01_prompt_packet.json").exists()
    assert (script_dir / "stage01_llm_output.json").exists()
    assert (script_dir / "stage01_codex_generation_request.txt").exists()
    assert "STAGE01_LOCAL_EXECUTION_MODE" in (script_dir / "stage01_codex_last_message.txt").read_text(encoding="utf-8")
    script_data = json.loads(script_json.read_text(encoding="utf-8"))
    llm_output = json.loads((script_dir / "stage01_llm_output.json").read_text(encoding="utf-8"))
    assert script_data["title"] == llm_output["selected_title"]
    assert script_data["title"]


def test_run_stage01_codex_flow_auto_repairs_failed_first_attempt(tmp_path: Path, monkeypatch) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260602_203600_30_mv"
    intake_dir = project_dir / "00_intake"
    script_dir = project_dir / "01_script"
    intake_dir.mkdir(parents=True)
    script_dir.mkdir(parents=True)

    brief = load_music_video_plateau_brief(project_dir)
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    original_builder = run_stage01_codex_flow.build_stage01_llm_output
    calls = {"count": 0}

    def flaky_local_builder(local_brief, prompt_packet=None, repair_packet=None):  # noqa: ANN001
        calls["count"] += 1
        if calls["count"] == 1:
            bad_first_output = stage01_local_semantics.build_stage01_llm_output(
                local_brief,
                prompt_packet=prompt_packet,
                repair_packet=repair_packet,
            )
            bad_first_output["characters"][0]["name"] = "城市景观规划师"
            bad_first_output["characters"][0]["identity_anchor"] = "长期被工作消耗的女性景观规划师"
            bad_first_output["settings"] = ["城市边缘"]
            bad_first_output["beats"] = bad_first_output["beats"][:1]
            return bad_first_output
        return original_builder(local_brief, prompt_packet=prompt_packet, repair_packet=repair_packet)

    monkeypatch.setattr(run_stage01_codex_flow, "build_stage01_llm_output", flaky_local_builder)

    script_json = script_dir / "script.json"
    assert run_stage01_codex_flow.main([str(locked_brief), str(script_json), "--max-repair-attempts", "1"]) == 0

    assert calls["count"] == 2
    assert (script_dir / "stage01_codex_repair_request_attempt_1.txt").exists()
    assert "STAGE01_LOCAL_REPAIR_MODE" in (script_dir / "stage01_codex_repair_last_message_attempt_1.txt").read_text(encoding="utf-8")
    assert not (script_dir / "stage01_validation_errors.json").exists()
    assert not (script_dir / "stage01_repair_packet.json").exists()
    script_data = json.loads(script_json.read_text(encoding="utf-8"))
    assert script_data["generation_meta"]["mode"] == "codex_llm_output"
    assert all(str(section.get("music_cue") or "").startswith("song:") for section in script_data["script"]["sections"])


def test_run_stage02_codex_flow_generates_storyboard_package_without_manual_llm_fill(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260528_103000_sunset_beach_girl"
    intake_dir = project_dir / "00_intake"
    script_dir = project_dir / "01_script"
    storyboard_dir = project_dir / "02_storyboard"
    intake_dir.mkdir(parents=True)
    script_dir.mkdir(parents=True)
    storyboard_dir.mkdir(parents=True)

    brief = load_example_brief()
    brief.update({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
    })
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    script = json.loads((TEMPLATES / "script.example.json").read_text(encoding="utf-8"))
    script["project_id"] = project_dir.name
    script["source_brief"] = str(locked_brief).replace("\\", "/")
    script_json = script_dir / "script.json"
    script_json.write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")

    storyboard_json = storyboard_dir / "storyboard.json"
    assert run_stage02_codex_flow.main([str(locked_brief), str(script_json), str(storyboard_json)]) == 0
    assert (storyboard_dir / "stage02_prompt_packet.json").exists()
    assert (storyboard_dir / "stage02_llm_output.json").exists()
    assert "STAGE02_LOCAL_EXECUTION_MODE" in (storyboard_dir / "stage02_codex_last_message.txt").read_text(encoding="utf-8")
    storyboard_data = json.loads(storyboard_json.read_text(encoding="utf-8"))
    llm_output = json.loads((storyboard_dir / "stage02_llm_output.json").read_text(encoding="utf-8"))
    assert storyboard_data["shot_count"] > 0
    assert storyboard_data["shot_count"] == len(llm_output["shots"])
    assert all(str(shot.get("production_note") or "").strip() for shot in storyboard_data["shots"])


def test_run_stage02_codex_flow_auto_repairs_failed_first_attempt(tmp_path: Path, monkeypatch) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260528_103000_sunset_beach_girl"
    intake_dir = project_dir / "00_intake"
    script_dir = project_dir / "01_script"
    storyboard_dir = project_dir / "02_storyboard"
    intake_dir.mkdir(parents=True)
    script_dir.mkdir(parents=True)
    storyboard_dir.mkdir(parents=True)

    brief = load_example_brief()
    brief.update({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
    })
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    script = json.loads((TEMPLATES / "script.example.json").read_text(encoding="utf-8"))
    script["project_id"] = project_dir.name
    script["source_brief"] = str(locked_brief).replace("\\", "/")
    script_json = script_dir / "script.json"
    script_json.write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")

    original_builder = run_stage02_codex_flow.build_stage02_llm_output
    calls = {"count": 0}

    def flaky_local_builder(local_brief, local_script, prompt_packet=None, repair_packet=None):  # noqa: ANN001
        calls["count"] += 1
        if calls["count"] == 1:
            bad_output = original_builder(local_brief, local_script, prompt_packet=prompt_packet, repair_packet=repair_packet)
            bad_output["shots"] = bad_output["shots"][:1]
            bad_output["target_duration_sec"] = 30
            return bad_output
        return original_builder(local_brief, local_script, prompt_packet=prompt_packet, repair_packet=repair_packet)

    monkeypatch.setattr(run_stage02_codex_flow, "build_stage02_llm_output", flaky_local_builder)

    storyboard_json = storyboard_dir / "storyboard.json"
    assert run_stage02_codex_flow.main([str(locked_brief), str(script_json), str(storyboard_json), "--max-repair-attempts", "1"]) == 0

    assert calls["count"] == 2
    assert (storyboard_dir / "stage02_codex_repair_request_attempt_1.txt").exists()
    assert "STAGE02_LOCAL_REPAIR_MODE" in (storyboard_dir / "stage02_codex_repair_last_message_attempt_1.txt").read_text(encoding="utf-8")
    assert not (storyboard_dir / "stage02_validation_errors.json").exists()
    assert not (storyboard_dir / "stage02_repair_packet.json").exists()
    storyboard_data = json.loads(storyboard_json.read_text(encoding="utf-8"))
    assert storyboard_data["shot_count"] > 1


def test_run_stage03_codex_flow_generates_character_bible_without_manual_llm_fill(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260528_103000_sunset_beach_girl"
    intake_dir = project_dir / "00_intake"
    script_dir = project_dir / "01_script"
    storyboard_dir = project_dir / "02_storyboard"
    character_dir = project_dir / "03_characters"
    for path in [intake_dir, script_dir, storyboard_dir, character_dir]:
        path.mkdir(parents=True)

    brief = load_example_brief()
    brief.update({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
    })
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    script = json.loads((TEMPLATES / "script.example.json").read_text(encoding="utf-8"))
    script["project_id"] = project_dir.name
    script["source_brief"] = str(locked_brief).replace("\\", "/")
    script_json = script_dir / "script.json"
    script_json.write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")

    storyboard = json.loads((TEMPLATES / "storyboard.example.json").read_text(encoding="utf-8"))
    storyboard["project_id"] = project_dir.name
    storyboard["source_brief"] = str(locked_brief).replace("\\", "/")
    storyboard["source_script"] = str(script_json).replace("\\", "/")
    storyboard_json = storyboard_dir / "storyboard.json"
    storyboard_json.write_text(json.dumps(storyboard, ensure_ascii=False, indent=2), encoding="utf-8")

    character_json = character_dir / "character_bible.json"
    assert run_stage03_codex_flow.main([str(locked_brief), str(script_json), str(storyboard_json), str(character_json)]) == 0
    assert (character_dir / "stage03_prompt_packet.json").exists()
    assert (character_dir / "stage03_llm_output.json").exists()
    assert "STAGE03_LOCAL_EXECUTION_MODE" in (character_dir / "stage03_codex_last_message.txt").read_text(encoding="utf-8")
    character_data = json.loads(character_json.read_text(encoding="utf-8"))
    llm_output = json.loads((character_dir / "stage03_llm_output.json").read_text(encoding="utf-8"))
    assert character_data["characters"]
    assert len(character_data["characters"]) == len(llm_output["characters"])
    assert all(str(item.get("visual_consistency_prompt") or "").strip() for item in character_data["characters"])
    first_character = character_data["characters"][0]
    assert "同一人物设定：" in first_character["visual_consistency_prompt"]
    assert "保持同一张脸" in first_character["visual_consistency_prompt"]
    assert first_character["performance_profile"]["baseline_expression"] != "观察"
    assert "避免脸型变化" in first_character["negative_consistency_prompt"]


def test_run_stage03_codex_flow_auto_repairs_failed_first_attempt(tmp_path: Path, monkeypatch) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260528_103000_sunset_beach_girl"
    intake_dir = project_dir / "00_intake"
    script_dir = project_dir / "01_script"
    storyboard_dir = project_dir / "02_storyboard"
    character_dir = project_dir / "03_characters"
    for path in [intake_dir, script_dir, storyboard_dir, character_dir]:
        path.mkdir(parents=True)

    brief = load_example_brief()
    brief.update({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
    })
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    script = json.loads((TEMPLATES / "script.example.json").read_text(encoding="utf-8"))
    script["project_id"] = project_dir.name
    script["source_brief"] = str(locked_brief).replace("\\", "/")
    script_json = script_dir / "script.json"
    script_json.write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")

    storyboard = json.loads((TEMPLATES / "storyboard.example.json").read_text(encoding="utf-8"))
    storyboard["project_id"] = project_dir.name
    storyboard["source_brief"] = str(locked_brief).replace("\\", "/")
    storyboard["source_script"] = str(script_json).replace("\\", "/")
    storyboard_json = storyboard_dir / "storyboard.json"
    storyboard_json.write_text(json.dumps(storyboard, ensure_ascii=False, indent=2), encoding="utf-8")

    original_builder = run_stage03_codex_flow.build_stage03_llm_output
    calls = {"count": 0}

    def flaky_local_builder(local_brief, local_script, local_storyboard, prompt_packet=None, repair_packet=None):  # noqa: ANN001
        calls["count"] += 1
        if calls["count"] == 1:
            bad_output = original_builder(
                local_brief,
                local_script,
                local_storyboard,
                prompt_packet=prompt_packet,
                repair_packet=repair_packet,
            )
            bad_output["characters"][0]["appearance"]["clothing"] = ""
            return bad_output
        return original_builder(
            local_brief,
            local_script,
            local_storyboard,
            prompt_packet=prompt_packet,
            repair_packet=repair_packet,
        )

    monkeypatch.setattr(run_stage03_codex_flow, "build_stage03_llm_output", flaky_local_builder)

    character_json = character_dir / "character_bible.json"
    assert run_stage03_codex_flow.main([str(locked_brief), str(script_json), str(storyboard_json), str(character_json), "--max-repair-attempts", "1"]) == 0

    assert calls["count"] == 2
    assert (character_dir / "stage03_codex_repair_request_attempt_1.txt").exists()
    assert "STAGE03_LOCAL_REPAIR_MODE" in (character_dir / "stage03_codex_repair_last_message_attempt_1.txt").read_text(encoding="utf-8")
    assert not (character_dir / "stage03_validation_errors.json").exists()
    assert not (character_dir / "stage03_repair_packet.json").exists()
    character_data = json.loads(character_json.read_text(encoding="utf-8"))
    assert character_data["characters"][0]["appearance"]["clothing"]


def test_run_stage04_codex_flow_generates_keyframe_prompts_without_manual_llm_fill(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260528_103000_sunset_beach_girl"
    intake_dir = project_dir / "00_intake"
    script_dir = project_dir / "01_script"
    storyboard_dir = project_dir / "02_storyboard"
    character_dir = project_dir / "03_characters"
    keyframe_dir = project_dir / "04_keyframes"
    for path in [intake_dir, script_dir, storyboard_dir, character_dir, keyframe_dir]:
        path.mkdir(parents=True)

    brief = load_example_brief()
    brief.update({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
    })
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    script = json.loads((TEMPLATES / "script.example.json").read_text(encoding="utf-8"))
    script["project_id"] = project_dir.name
    script["source_brief"] = str(locked_brief).replace("\\", "/")
    script_json = script_dir / "script.json"
    script_json.write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")

    storyboard = json.loads((TEMPLATES / "storyboard.example.json").read_text(encoding="utf-8"))
    storyboard["project_id"] = project_dir.name
    storyboard["source_brief"] = str(locked_brief).replace("\\", "/")
    storyboard["source_script"] = str(script_json).replace("\\", "/")
    storyboard_json = storyboard_dir / "storyboard.json"
    storyboard_json.write_text(json.dumps(storyboard, ensure_ascii=False, indent=2), encoding="utf-8")

    character = json.loads((TEMPLATES / "character_bible.example.json").read_text(encoding="utf-8"))
    character["project_id"] = project_dir.name
    character["source_brief"] = str(locked_brief).replace("\\", "/")
    character["source_script"] = str(script_json).replace("\\", "/")
    character["source_storyboard"] = str(storyboard_json).replace("\\", "/")
    character_json = character_dir / "character_bible.json"
    character_json.write_text(json.dumps(character, ensure_ascii=False, indent=2), encoding="utf-8")

    keyframe_json = keyframe_dir / "keyframe_prompts.json"
    assert run_stage04_codex_flow.main([str(locked_brief), str(script_json), str(storyboard_json), str(character_json), str(keyframe_json)]) == 0
    assert (keyframe_dir / "stage04_prompt_packet.json").exists()
    assert (keyframe_dir / "stage04_llm_output.json").exists()
    assert "STAGE04_LOCAL_EXECUTION_MODE" in (keyframe_dir / "stage04_codex_last_message.txt").read_text(encoding="utf-8")
    keyframe_data = json.loads(keyframe_json.read_text(encoding="utf-8"))
    llm_output = json.loads((keyframe_dir / "stage04_llm_output.json").read_text(encoding="utf-8"))
    assert keyframe_data["shot_prompts"]
    assert len(keyframe_data["shot_prompts"]) == len(llm_output["shot_prompts"])
    assert all(str(item.get("consistency_prompt") or "").startswith("Character identity anchor:") for item in keyframe_data["shot_prompts"])
    assert keyframe_data["transition_prompts"]


def test_stage04_local_semantics_rewrites_abstract_storyboard_language_to_direct_visual_actions() -> None:
    shot = {
        "shot_id": "S001",
        "location": "黄昏海滩",
        "scene": "黄昏海滩",
        "camera": "wide establishing shot",
        "action": "黄昏海滩上，年轻的亚洲女性沿着潮线慢慢往前走，像是在等海风把心事吹散。",
        "emotion": "观察",
        "composition_focus": "把镜头重心放在动作过后的情绪回落，突出人物状态和环境呼吸。",
    }
    rewritten_action = stage04_local_semantics._rewritten_action(shot)
    rewritten_focus = stage04_local_semantics._rewritten_composition(shot)
    rewritten_emotion = stage04_local_semantics._story_anchor_bundle(shot)["emotion"]
    assert "像是在等海风把心事吹散" not in rewritten_action
    assert "海风吹动头发和裙摆，她继续慢慢往前走，不要夸张表情" in rewritten_action
    assert "情绪回落" not in rewritten_focus
    assert "动作结束后的停顿要清楚，肩膀和呼吸都更放松" in rewritten_focus
    assert rewritten_emotion == "继续慢慢往前走，嘴唇自然闭合，视线停在前方或海平线，不回头"


def test_run_stage04_codex_flow_auto_repairs_failed_first_attempt(tmp_path: Path, monkeypatch) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260528_103000_sunset_beach_girl"
    intake_dir = project_dir / "00_intake"
    script_dir = project_dir / "01_script"
    storyboard_dir = project_dir / "02_storyboard"
    character_dir = project_dir / "03_characters"
    keyframe_dir = project_dir / "04_keyframes"
    for path in [intake_dir, script_dir, storyboard_dir, character_dir, keyframe_dir]:
        path.mkdir(parents=True)

    brief = load_example_brief()
    brief.update({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
    })
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    script = json.loads((TEMPLATES / "script.example.json").read_text(encoding="utf-8"))
    script["project_id"] = project_dir.name
    script["source_brief"] = str(locked_brief).replace("\\", "/")
    script_json = script_dir / "script.json"
    script_json.write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")

    storyboard = json.loads((TEMPLATES / "storyboard.example.json").read_text(encoding="utf-8"))
    storyboard["project_id"] = project_dir.name
    storyboard["source_brief"] = str(locked_brief).replace("\\", "/")
    storyboard["source_script"] = str(script_json).replace("\\", "/")
    storyboard_json = storyboard_dir / "storyboard.json"
    storyboard_json.write_text(json.dumps(storyboard, ensure_ascii=False, indent=2), encoding="utf-8")

    character = json.loads((TEMPLATES / "character_bible.example.json").read_text(encoding="utf-8"))
    character["project_id"] = project_dir.name
    character["source_brief"] = str(locked_brief).replace("\\", "/")
    character["source_script"] = str(script_json).replace("\\", "/")
    character["source_storyboard"] = str(storyboard_json).replace("\\", "/")
    character_json = character_dir / "character_bible.json"
    character_json.write_text(json.dumps(character, ensure_ascii=False, indent=2), encoding="utf-8")

    original_builder = run_stage04_codex_flow.build_stage04_llm_output
    calls = {"count": 0}

    def flaky_local_builder(local_brief, local_script, local_storyboard, local_character_bible, prompt_packet=None, repair_packet=None):  # noqa: ANN001
        calls["count"] += 1
        if calls["count"] == 1:
            bad_output = original_builder(
                local_brief,
                local_script,
                local_storyboard,
                local_character_bible,
                prompt_packet=prompt_packet,
                repair_packet=repair_packet,
            )
            bad_output["shot_prompts"][0]["start_keyframe_prompt"] = ""
            return bad_output
        return original_builder(
            local_brief,
            local_script,
            local_storyboard,
            local_character_bible,
            prompt_packet=prompt_packet,
            repair_packet=repair_packet,
        )

    monkeypatch.setattr(run_stage04_codex_flow, "build_stage04_llm_output", flaky_local_builder)

    keyframe_json = keyframe_dir / "keyframe_prompts.json"
    assert run_stage04_codex_flow.main([
        str(locked_brief),
        str(script_json),
        str(storyboard_json),
        str(character_json),
        str(keyframe_json),
        "--max-repair-attempts",
        "1",
    ]) == 0

    assert calls["count"] == 2
    assert (keyframe_dir / "stage04_codex_repair_request_attempt_1.txt").exists()
    assert "STAGE04_LOCAL_REPAIR_MODE" in (keyframe_dir / "stage04_codex_repair_last_message_attempt_1.txt").read_text(encoding="utf-8")
    assert not (keyframe_dir / "stage04_validation_errors.json").exists()
    assert not (keyframe_dir / "stage04_repair_packet.json").exists()
    keyframe_data = json.loads(keyframe_json.read_text(encoding="utf-8"))
    assert keyframe_data["shot_prompts"][0]["start_keyframe_prompt"]


def test_resolve_codex_bin_prefers_windows_cmd_over_powershell_shim(monkeypatch) -> None:
    monkeypatch.setattr(run_stage01_codex_flow.sys, "platform", "win32")

    def fake_which(name: str) -> str | None:
        mapping = {
            "codex": r"C:\Tools\NodeJs\node-v24.15.0\codex.ps1",
            "codex.cmd": r"C:\Tools\NodeJs\node-v24.15.0\codex.cmd",
            "codex.exe": r"C:\Users\hongguangsheng\AppData\Local\Programs\Codex\codex.exe",
        }
        return mapping.get(name)

    monkeypatch.setattr(run_stage01_codex_flow.shutil, "which", fake_which)

    resolved = run_stage01_codex_flow.resolve_codex_bin("codex")
    assert resolved.endswith("codex.cmd")


def test_resolve_codex_bin_rejects_explicit_windows_powershell_shim(monkeypatch) -> None:
    monkeypatch.setattr(run_stage01_codex_flow.sys, "platform", "win32")

    try:
        run_stage01_codex_flow.resolve_codex_bin(r"C:\Tools\NodeJs\node-v24.15.0\codex.ps1")
    except SystemExit as exc:
        assert "PowerShell shim" in str(exc)
    else:
        raise AssertionError("Expected explicit .ps1 codex bin to be rejected on Windows")


def test_stage01_llm_output_schema_is_strict_for_codex_response_format() -> None:
    schema_path = SCRIPT.parent / "references" / "stage01_llm_output.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    assert schema["additionalProperties"] is False
    assert schema["properties"]["characters"]["items"]["additionalProperties"] is False
    assert schema["properties"]["beats"]["items"]["additionalProperties"] is False
    assert schema["properties"]["self_check"]["additionalProperties"] is False


def test_stage01_opening_composition_tracks_locked_aspect_ratio() -> None:
    expected_phrases = {
        "9:16": "先用竖屏建立镜头交代",
        "16:9": "先用横屏建立镜头交代",
        "1:1": "先用方画幅建立镜头交代",
        "21:9": "先用宽银幕建立镜头交代",
    }

    for aspect_ratio, expected in expected_phrases.items():
        brief = load_example_brief()
        brief["normalized"]["aspect_ratio"] = aspect_ratio
        brief["normalized"]["aspect_ratio_label"] = aspect_ratio
        script_data = pipeline_blueprints.build_stage01_script(brief)
        opening = script_data["story_anchors"]["composition_beats"][0]
        assert expected in opening


def test_stage01_beach_music_video_text_quality_avoids_template_tone() -> None:
    brief = load_example_brief()
    brief["normalized"].update({
        "idea": "一名年轻的亚洲女性，穿着裙子在黄昏的海滩边散步、放空自己。",
        "genre": "音乐MV",
        "style": "写实电影感",
        "aspect_ratio": "16:9",
        "aspect_ratio_label": "16:9 横屏",
        "voice_mode": "不确定，先由模型建议",
        "voice_required": "recommend",
        "music_mode": "需要，背景配乐（underscore）",
        "music_profile": "underscore",
        "final_output": "合成粗剪成片",
    })

    script_data = pipeline_blueprints.build_stage01_script(brief)

    assert script_data["title"] == "黄昏潮线"
    assert script_data["characters"][0]["name"] == "年轻的亚洲女性"
    assert "既定题材与风格" not in script_data["logline"]
    assert script_data["theme"] == "把没说出口的情绪留给海风和晚霞"
    assert script_data["narrative_movement"] == "从独自沉浸到在海风与脚步里慢慢把情绪放下"
    assert script_data["ending_direction"] == "年轻的亚洲女性沿着潮线继续往前走，背影和呼吸都慢慢轻下来。"
    assert script_data["settings"] == ["黄昏海滩"]
    assert script_data["duration_plan"]["beats"][0]["summary"] == "黄昏海滩上，年轻的亚洲女性沿着潮线慢慢往前走，像是在等海风把心事吹散。"
    assert script_data["duration_plan"]["beats"][2]["summary"] == "海风裹着晚霞从她身边过去，那点没说出口的情绪终于开始松开。"
    assert all(not str(section.get("voiceover") or "").strip() for section in script_data["script"]["sections"])
    assert all("推进“" not in str(beat.get("summary") or "") for beat in script_data["duration_plan"]["beats"])
    assert all("一名" not in str(beat.get("summary") or "") for beat in script_data["duration_plan"]["beats"])
    assert "推进“" not in script_data["script"]["sections"][0]["visual"]
    assert "一名" not in script_data["script"]["sections"][0]["visual"]
    assert all("构图重点：" not in str(section.get("visual") or "") for section in script_data["script"]["sections"])
    assert all(str(section.get("composition_focus") or "").strip() for section in script_data["script"]["sections"])


def test_write_stage01_outputs_syncs_story_anchors_with_generated_beats(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260603_180000_beach_anchor_sync"
    intake_dir = project_dir / "00_intake"
    script_dir = project_dir / "01_script"
    intake_dir.mkdir(parents=True, exist_ok=True)
    script_dir.mkdir(parents=True, exist_ok=True)

    brief = load_example_brief()
    brief.update({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
    })
    brief["normalized"].update({
        "idea": "一名年轻的亚洲女性，穿着裙子在黄昏的海滩边散步、放空自己。",
        "genre": "音乐MV",
        "style": "写实电影感",
        "aspect_ratio": "16:9",
        "aspect_ratio_label": "16:9 横屏",
        "voice_mode": "不确定，先由模型建议",
        "voice_required": "recommend",
        "music_mode": "需要，背景配乐（underscore）",
        "music_profile": "underscore",
        "final_output": "合成粗剪成片",
    })
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    script_json = script_dir / "script.json"
    assert run_stage01_codex_flow.main([str(locked_brief), str(script_json)]) == 0
    script_data = json.loads(script_json.read_text(encoding="utf-8"))

    assert script_data["settings"] == ["黄昏海滩"]
    assert script_data["story_anchors"]["subject"] == "年轻的亚洲女性"
    assert script_data["story_anchors"]["scene_label"] == "黄昏海滩"
    assert script_data["story_anchors"]["action_beats"] == [beat["summary"] for beat in script_data["duration_plan"]["beats"]]
    assert script_data["story_anchors"]["composition_beats"] == [section["visual"] for section in script_data["script"]["sections"]]
    assert script_data["story_anchors"]["composition_focus_beats"] == [section["composition_focus"] for section in script_data["script"]["sections"]]
    assert script_data["characters"][0]["identity_anchor"] == "20岁出头，在黄昏海边独自散步、想把心事慢慢放下的亚洲年轻女性"


def test_stage03_and_stage04_preserve_gender_and_aspect_ratio_for_beach_girl(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260601_150210_beach_girl"
    intake_dir = project_dir / "00_intake"
    script_dir = project_dir / "01_script"
    storyboard_dir = project_dir / "02_storyboard"
    character_dir = project_dir / "03_characters"
    keyframe_dir = project_dir / "04_keyframes"
    for path in [intake_dir, script_dir, storyboard_dir, character_dir, keyframe_dir]:
        path.mkdir(parents=True, exist_ok=True)

    brief = load_example_brief()
    brief.update({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
    })
    brief["normalized"].update({
        "idea": "一个穿裙子的女生在黄昏的沙滩上独自散步，画面安静、克制，突出晚霞、海风与孤独但温柔的情绪。",
        "genre": "电影感镜头片段",
        "style": "写实电影感",
        "aspect_ratio": "16:9",
        "aspect_ratio_label": "16:9 横屏",
        "voice_mode": "不需要配音",
        "voice_required": False,
        "final_output": "合成粗剪成片",
    })
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    script_json = script_dir / "script.json"
    script_data = json.loads((TEMPLATES / "script.example.json").read_text(encoding="utf-8"))
    script_data["project_id"] = project_dir.name
    script_data["source_brief"] = str(locked_brief).replace("\\", "/")
    script_json.write_text(json.dumps(script_data, ensure_ascii=False, indent=2), encoding="utf-8")

    stage02_llm_output = make_stage02_llm_output_from_example()
    first_shot = stage02_llm_output["shots"][0]
    first_shot["composition"] = "黄昏海滩横向铺开，女生穿裙子独自沿潮线散步，晚霞和海风一起进入画面。"
    (storyboard_dir / "stage02_llm_output.json").write_text(json.dumps(stage02_llm_output, ensure_ascii=False, indent=2), encoding="utf-8")
    storyboard_json = storyboard_dir / "storyboard.json"
    assert new_storyboard_template.main(["new_storyboard_template.py", str(locked_brief), str(script_json), str(storyboard_json)]) == 0

    stage03_llm_output = make_stage03_llm_output_from_example()
    stage03_llm_output["characters"][0]["gender_presentation"] = "female"
    stage03_llm_output["characters"][0]["visual_consistency_prompt"] = (
        "same young woman in her early 20s, female, long black hair, light dress, sunset beach, restrained emotion"
    )
    (character_dir / "stage03_llm_output.json").write_text(json.dumps(stage03_llm_output, ensure_ascii=False, indent=2), encoding="utf-8")
    character_json = character_dir / "character_bible.json"
    assert new_character_bible_template.main([
        "new_character_bible_template.py",
        str(locked_brief),
        str(script_json),
        str(storyboard_json),
        str(character_json),
    ]) == 0
    character_bible = json.loads(character_json.read_text(encoding="utf-8"))
    assert character_bible["characters"][0]["gender_presentation"] == "female"

    stage04_llm_output = make_stage04_llm_output_from_example()
    stage04_llm_output["shot_prompts"][0]["start_keyframe_prompt"] += ", horizontal 16:9 composition"
    stage04_llm_output["shot_prompts"][0]["end_keyframe_prompt"] += ", horizontal 16:9 composition"
    stage04_llm_output["shot_prompts"][0]["consistency_prompt"] += "; female protagonist"
    (keyframe_dir / "stage04_llm_output.json").write_text(json.dumps(stage04_llm_output, ensure_ascii=False, indent=2), encoding="utf-8")
    keyframe_json = keyframe_dir / "keyframe_prompts.json"
    assert new_keyframe_prompts_template.main([
        "new_keyframe_prompts_template.py",
        str(locked_brief),
        str(script_json),
        str(storyboard_json),
        str(character_json),
        str(keyframe_json),
    ]) == 0
    keyframe_data = json.loads(keyframe_json.read_text(encoding="utf-8"))
    first_shot = keyframe_data["shot_prompts"][0]
    assert "horizontal 16:9 composition" in first_shot["start_keyframe_prompt"]
    assert "horizontal 16:9 composition" in first_shot["end_keyframe_prompt"]
    assert "female" in first_shot["consistency_prompt"]


def test_stage05_and_stage06_jobs_prefer_locked_normalized_visual_spec(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260601_150210_黄昏时分海滩长裙女生散步"
    intake_dir = project_dir / "00_intake"
    storyboard_dir = project_dir / "02_storyboard"
    keyframe_dir = project_dir / "04_keyframes"
    images_dir = project_dir / "05_images"
    video_dir = project_dir / "06_video_clips"
    intake_dir.mkdir(parents=True)
    storyboard_dir.mkdir(parents=True)
    keyframe_dir.mkdir(parents=True)
    images_dir.mkdir(parents=True)
    video_dir.mkdir(parents=True)

    brief = load_example_brief()
    brief.update({
        "schema_version": "0.7.0",
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "aspect_ratio": "9:16",
        "resolution": "1080P",
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-06-01T15:02:10+08:00",
    })
    brief["normalized"].update({
        "aspect_ratio": "16:9",
        "aspect_ratio_label": "16:9 横屏",
        "resolution": "720P",
        "resolution_label": "720P",
        "final_output": "合成粗剪成片",
    })
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    storyboard = json.loads((TEMPLATES / "storyboard.example.json").read_text(encoding="utf-8"))
    storyboard["project_id"] = project_dir.name
    storyboard_json = storyboard_dir / "storyboard.json"
    storyboard_json.write_text(json.dumps(storyboard, ensure_ascii=False, indent=2), encoding="utf-8")

    keyframe = json.loads((TEMPLATES / "keyframe_prompts.example.json").read_text(encoding="utf-8"))
    keyframe["project_id"] = project_dir.name
    keyframe["source_brief"] = str(locked_brief).replace("\\", "/")
    keyframe["status"] = "confirmed"
    keyframe["shot_prompts"] = keyframe["shot_prompts"][:1]
    keyframe_json = keyframe_dir / "keyframe_prompts.json"
    keyframe_json.write_text(json.dumps(keyframe, ensure_ascii=False, indent=2), encoding="utf-8")

    image_manifest_json = images_dir / "keyframe_image_manifest.json"
    assert new_keyframe_image_jobs.main(["new_keyframe_image_jobs.py", str(locked_brief), str(keyframe_json), str(image_manifest_json)]) == 0
    image_manifest = json.loads(image_manifest_json.read_text(encoding="utf-8"))
    assert {job["aspect_ratio"] for job in image_manifest["jobs"]} == {"16:9"}
    assert {job["resolution"] for job in image_manifest["jobs"]} == {"720P"}
    for job in image_manifest["jobs"]:
        output_path = Path(job["output_path"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"png")
        job["status"] = "succeeded"
        job["provider"] = "manual"
        job["evidence"]["file_exists"] = True
        job["evidence"]["file_size_bytes"] = output_path.stat().st_size
    image_manifest["status"] = "confirmed"
    image_manifest["self_check"]["all_required_images_exist"] = True
    image_manifest["self_check"]["ready_for_video_clip_generation"] = True
    image_manifest_json.write_text(json.dumps(image_manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    clip_manifest_json = video_dir / "video_clip_manifest.json"
    assert new_video_clip_jobs.main([
        "new_video_clip_jobs.py",
        str(locked_brief),
        str(storyboard_json),
        str(keyframe_json),
        str(image_manifest_json),
        str(clip_manifest_json),
    ]) == 0
    clip_manifest = json.loads(clip_manifest_json.read_text(encoding="utf-8"))
    assert {job["aspect_ratio"] for job in clip_manifest["jobs"]} == {"16:9"}
    assert {job["resolution"] for job in clip_manifest["jobs"]} == {"720P"}


def test_validate_storyboard_example_final() -> None:
    data = json.loads((TEMPLATES / "storyboard.example.json").read_text(encoding="utf-8"))
    ok, errors, warnings = validate_storyboard.validate(data, mode="final")
    assert ok, errors


def test_new_storyboard_template_generates_final_ready_draft(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260528_103000_sunset_beach_girl"
    intake_dir = project_dir / "00_intake"
    script_dir = project_dir / "01_script"
    storyboard_dir = project_dir / "02_storyboard"
    intake_dir.mkdir(parents=True)
    script_dir.mkdir(parents=True)
    storyboard_dir.mkdir(parents=True)

    brief = load_example_brief()
    brief.update({
        "schema_version": "0.3.0",
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-28T10:35:00+08:00",
    })
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    script = json.loads((TEMPLATES / "script.example.json").read_text(encoding="utf-8"))
    script["project_id"] = project_dir.name
    script["source_brief"] = str(locked_brief).replace("\\", "/")
    script_json = script_dir / "script.json"
    script_json.write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")

    (storyboard_dir / "stage02_llm_output.json").write_text(
        json.dumps(make_stage02_llm_output_from_example(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    storyboard_json = storyboard_dir / "storyboard.json"
    assert new_storyboard_template.main(["new_storyboard_template.py", str(locked_brief), str(script_json), str(storyboard_json)]) == 0

    storyboard_data = json.loads(storyboard_json.read_text(encoding="utf-8"))
    ok, errors, warnings = validate_storyboard.validate(storyboard_data, mode="draft")
    assert ok, errors
    ok, errors, warnings = validate_storyboard.validate(storyboard_data, mode="final")
    assert ok, errors
    assert storyboard_data["shots"]
    assert storyboard_data["shot_count"] == len(storyboard_data["shots"])
    assert (storyboard_dir / "storyboard.md").exists()
    assert (storyboard_dir / "storyboard_review.md").exists()



def test_validate_character_bible_example_final() -> None:
    data = json.loads((TEMPLATES / "character_bible.example.json").read_text(encoding="utf-8"))
    ok, errors, warnings = validate_character_bible.validate(data, mode="final")
    assert ok, errors


def test_new_character_bible_template_generates_final_ready_draft(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260528_103000_sunset_beach_girl"
    intake_dir = project_dir / "00_intake"
    script_dir = project_dir / "01_script"
    storyboard_dir = project_dir / "02_storyboard"
    character_dir = project_dir / "03_characters"
    intake_dir.mkdir(parents=True)
    script_dir.mkdir(parents=True)
    storyboard_dir.mkdir(parents=True)
    character_dir.mkdir(parents=True)

    brief = load_example_brief()
    brief.update({
        "schema_version": "0.4.0",
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-28T10:35:00+08:00",
    })
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    script = json.loads((TEMPLATES / "script.example.json").read_text(encoding="utf-8"))
    script["project_id"] = project_dir.name
    script["source_brief"] = str(locked_brief).replace("\\", "/")
    script_json = script_dir / "script.json"
    script_json.write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")

    storyboard = json.loads((TEMPLATES / "storyboard.example.json").read_text(encoding="utf-8"))
    storyboard["project_id"] = project_dir.name
    storyboard["source_brief"] = str(locked_brief).replace("\\", "/")
    storyboard["source_script"] = str(script_json).replace("\\", "/")
    storyboard_json = storyboard_dir / "storyboard.json"
    storyboard_json.write_text(json.dumps(storyboard, ensure_ascii=False, indent=2), encoding="utf-8")

    (character_dir / "stage03_llm_output.json").write_text(
        json.dumps(make_stage03_llm_output_from_example(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    character_json = character_dir / "character_bible.json"
    assert new_character_bible_template.main(["new_character_bible_template.py", str(locked_brief), str(script_json), str(storyboard_json), str(character_json)]) == 0

    character_data = json.loads(character_json.read_text(encoding="utf-8"))
    ok, errors, warnings = validate_character_bible.validate(character_data, mode="draft")
    assert ok, errors
    ok, errors, warnings = validate_character_bible.validate(character_data, mode="final")
    assert ok, errors
    assert character_data["characters"]
    assert "performance_profile" in character_data["characters"][0]
    assert character_data["reference_image_status"]["all_present"] is False
    assert character_data["stage05_execution_readiness"]["safe_to_auto_generate"] is False
    assert character_data["self_check"]["reference_images_ready"] is False
    assert (character_dir / "character_bible.md").exists()
    assert (character_dir / "character_review.md").exists()
    assert (character_dir / "reference_image_plan.json").exists()
    assert (character_dir / "reference_image_start_here.md").exists()
    bible_text = (character_dir / "character_bible.md").read_text(encoding="utf-8")
    review_text = (character_dir / "character_review.md").read_text(encoding="utf-8")
    reference_start_here = (character_dir / "reference_image_start_here.md").read_text(encoding="utf-8")
    assert "定位：" in bible_text
    assert "表演基线：" in bible_text
    assert "连续性锚点：" in bible_text
    assert "角色：main" not in bible_text
    assert "角色参考图就绪：否" in review_text
    assert "CHAR_001_primary.png" in review_text
    assert "角色参考图补齐入口" in reference_start_here
    assert "03_characters/reference_images/CHAR_001_primary.png" in reference_start_here

def test_update_project_manifest_sets_pipeline_flags(tmp_path: Path, monkeypatch) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260528_103000_sunset_beach_girl"
    project_dir.mkdir(parents=True)
    monkeypatch.setattr(sys, "argv", [
        "update_project_manifest.py",
        str(project_dir),
        "--stage", "STAGE_01_SCRIPT_CONFIRMED",
        "--script-confirmed", "true",
        "--allowed-next-stage", "STAGE_02_STORYBOARD",
        "--character-bible-confirmed", "false",
        "--keyframe-prompts-confirmed", "true",
        "--keyframe-images-confirmed", "false",
        "--video-clips-confirmed", "true",
        "--audio-confirmed", "true",
        "--assembly-confirmed", "false",
    ])
    assert update_project_manifest.main() == 0
    data = json.loads((project_dir / "project_manifest.json").read_text(encoding="utf-8"))
    assert data["current_stage"] == "STAGE_01_SCRIPT_CONFIRMED"
    assert data["script_confirmed"] is True
    assert data["allowed_next_stage"] == "STAGE_02_STORYBOARD"
    assert data["character_bible_confirmed"] is False


def test_show_creator_home_points_to_reference_recovery_or_workbench(tmp_path: Path, capsys) -> None:
    project_dir = tmp_path / "video_projects" / "creator_status_demo"
    (project_dir / "03_characters").mkdir(parents=True, exist_ok=True)
    (project_dir / "04_keyframes").mkdir(parents=True, exist_ok=True)
    manifest_path = project_dir / "project_manifest.json"
    manifest_path.write_text(json.dumps({
        "project_id": project_dir.name,
        "project_title": "雨夜便利店让伞",
        "project_dir": str(project_dir).replace("\\", "/"),
        "current_stage": "STAGE_04_KEYFRAME_PROMPTS_GENERATION",
        "status": "active",
        "brief_locked": True,
        "script_confirmed": True,
        "storyboard_confirmed": True,
        "character_bible_confirmed": True,
        "keyframe_prompts_confirmed": True,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    (project_dir / "03_characters" / "character_bible.json").write_text(json.dumps({
        "stage": "STAGE_03_CHARACTER_BIBLE",
        "project_id": project_dir.name,
        "reference_image_status": {
            "all_present": False,
            "missing_paths": ["03_characters/reference_images/CHAR_001_primary.png"],
        },
        "stage05_execution_readiness": {
            "safe_to_auto_generate": False,
            "missing_reference_images": ["03_characters/reference_images/CHAR_001_primary.png"],
        },
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    (project_dir / "04_keyframes" / "keyframe_prompts.json").write_text(json.dumps({
        "stage": "STAGE_04_KEYFRAME_PROMPTS",
        "project_id": project_dir.name,
        "reference_image_status": {
            "all_present": False,
            "missing_paths": ["03_characters/reference_images/CHAR_001_primary.png"],
        },
        "stage05_execution_readiness": {
            "safe_to_auto_generate": False,
            "missing_reference_images": ["03_characters/reference_images/CHAR_001_primary.png"],
        },
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    assert show_creator_home.main(["--project-dir", str(project_dir)]) == 0
    output = capsys.readouterr().out
    assert "CREATOR_HOME_READY" in output
    assert "RECOMMENDED_ENTRY_LABEL: 打开角色参考图说明" in output
    assert "03_characters/reference_image_start_here.md" in output



def test_validate_keyframe_prompts_example_final() -> None:
    data = json.loads((TEMPLATES / "keyframe_prompts.example.json").read_text(encoding="utf-8"))
    ok, errors, warnings = validate_keyframe_prompts.validate(data, mode="final")
    assert ok, errors


def test_new_keyframe_prompts_template_generates_final_ready_draft(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260528_103000_sunset_beach_girl"
    intake_dir = project_dir / "00_intake"
    script_dir = project_dir / "01_script"
    storyboard_dir = project_dir / "02_storyboard"
    character_dir = project_dir / "03_characters"
    keyframe_dir = project_dir / "04_keyframes"
    intake_dir.mkdir(parents=True)
    script_dir.mkdir(parents=True)
    storyboard_dir.mkdir(parents=True)
    character_dir.mkdir(parents=True)
    keyframe_dir.mkdir(parents=True)

    brief = load_example_brief()
    brief.update({
        "schema_version": "0.5.0",
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-28T10:35:00+08:00",
    })
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    script = json.loads((TEMPLATES / "script.example.json").read_text(encoding="utf-8"))
    script["project_id"] = project_dir.name
    script["source_brief"] = str(locked_brief).replace("\\", "/")
    script_json = script_dir / "script.json"
    script_json.write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")

    storyboard = json.loads((TEMPLATES / "storyboard.example.json").read_text(encoding="utf-8"))
    storyboard["project_id"] = project_dir.name
    storyboard["source_brief"] = str(locked_brief).replace("\\", "/")
    storyboard["source_script"] = str(script_json).replace("\\", "/")
    storyboard_json = storyboard_dir / "storyboard.json"
    storyboard_json.write_text(json.dumps(storyboard, ensure_ascii=False, indent=2), encoding="utf-8")

    character = json.loads((TEMPLATES / "character_bible.example.json").read_text(encoding="utf-8"))
    character["project_id"] = project_dir.name
    character["source_brief"] = str(locked_brief).replace("\\", "/")
    character["source_script"] = str(script_json).replace("\\", "/")
    character["source_storyboard"] = str(storyboard_json).replace("\\", "/")
    character_json = character_dir / "character_bible.json"
    character_json.write_text(json.dumps(character, ensure_ascii=False, indent=2), encoding="utf-8")

    (keyframe_dir / "stage04_llm_output.json").write_text(
        json.dumps(make_stage04_llm_output_from_example(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    keyframe_json = keyframe_dir / "keyframe_prompts.json"
    assert new_keyframe_prompts_template.main([
        "new_keyframe_prompts_template.py", str(locked_brief), str(script_json), str(storyboard_json), str(character_json), str(keyframe_json)
    ]) == 0

    keyframe_data = json.loads(keyframe_json.read_text(encoding="utf-8"))
    ok, errors, warnings = validate_keyframe_prompts.validate(keyframe_data, mode="draft")
    assert ok, errors
    assert len(keyframe_data["shot_prompts"]) == len(storyboard["shots"])
    ok, errors, warnings = validate_keyframe_prompts.validate(keyframe_data, mode="final")
    assert ok, errors
    assert keyframe_data["transition_prompts"]
    assert keyframe_data["shot_prompts"][0]["performance_prompt"]
    assert keyframe_data["reference_image_status"]["all_present"] is False
    assert keyframe_data["stage05_execution_readiness"]["safe_to_auto_generate"] is False
    assert keyframe_data["self_check"]["character_reference_images_ready"] is False
    assert (keyframe_dir / "keyframe_prompts.md").exists()
    assert (keyframe_dir / "motion_prompts.json").exists()
    assert (keyframe_dir / "prompt_review.md").exists()
    assert (keyframe_dir / "stage05_start_here.md").exists()
    prompt_review_text = (keyframe_dir / "prompt_review.md").read_text(encoding="utf-8")
    stage05_start_here = (keyframe_dir / "stage05_start_here.md").read_text(encoding="utf-8")
    assert "角色参考图就绪：否" in prompt_review_text
    assert "CHAR_001_primary.png" in prompt_review_text
    assert "03_characters/reference_image_start_here.md" in stage05_start_here


def test_rainy_store_story_anchors_survive_stage01_to_stage04(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "creator_trial_20260530_rainy_store"
    intake_dir = project_dir / "00_intake"
    script_dir = project_dir / "01_script"
    storyboard_dir = project_dir / "02_storyboard"
    character_dir = project_dir / "03_characters"
    keyframe_dir = project_dir / "04_keyframes"
    for path in [intake_dir, script_dir, storyboard_dir, character_dir, keyframe_dir]:
        path.mkdir(parents=True, exist_ok=True)

    brief = load_rainy_store_brief(project_dir)
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")
    write_stage01_llm_output(script_dir, make_stage01_llm_output_for_rainy_store())

    script_json = script_dir / "script.json"
    assert new_script_template.main(["new_script_template.py", str(locked_brief), str(script_json)]) == 0
    (storyboard_dir / "stage02_llm_output.json").write_text(
        json.dumps(make_stage02_llm_output_for_rainy_store(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    storyboard_json = storyboard_dir / "storyboard.json"
    assert new_storyboard_template.main(["new_storyboard_template.py", str(locked_brief), str(script_json), str(storyboard_json)]) == 0
    (character_dir / "stage03_llm_output.json").write_text(
        json.dumps(make_stage03_llm_output_for_rainy_store(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    character_json = character_dir / "character_bible.json"
    assert new_character_bible_template.main([
        "new_character_bible_template.py",
        str(locked_brief),
        str(script_json),
        str(storyboard_json),
        str(character_json),
    ]) == 0
    (keyframe_dir / "stage04_llm_output.json").write_text(
        json.dumps(make_stage04_llm_output_for_rainy_store(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    keyframe_json = keyframe_dir / "keyframe_prompts.json"
    assert new_keyframe_prompts_template.main([
        "new_keyframe_prompts_template.py",
        str(locked_brief),
        str(script_json),
        str(storyboard_json),
        str(character_json),
        str(keyframe_json),
    ]) == 0

    script_data = json.loads(script_json.read_text(encoding="utf-8"))
    storyboard_data = json.loads(storyboard_json.read_text(encoding="utf-8"))
    character_data = json.loads(character_json.read_text(encoding="utf-8"))
    keyframe_data = json.loads(keyframe_json.read_text(encoding="utf-8"))

    assert script_data["story_anchors"]["scene_label"] == "雨夜便利店门口"
    assert script_data["story_anchors"]["key_props"][:2] == ["最后一把伞", "热可可"]
    script_text = (script_dir / "script.md").read_text(encoding="utf-8")
    assert "雨夜便利店门口" in script_text
    assert "最后一把伞" in script_text
    assert "热可可" in script_text
    assert "核心场景" not in script_text
    assert "海边女孩" not in script_text

    joined_storyboard = "\n".join(
        f"{shot.get('scene')} {shot.get('composition')} {shot.get('action')} {shot.get('key_prop')}"
        for shot in storyboard_data["shots"]
    )
    assert "雨夜便利店门口" in joined_storyboard
    assert "最后一把伞" in joined_storyboard
    assert "热可可" in joined_storyboard
    assert storyboard_data["shots"][0]["location"] == "便利店门口"
    assert storyboard_data["shots"][0]["weather"] == "雨夜"

    assert character_data["characters"][0]["name"] == "20岁出头的女孩"
    assert "最后一把伞" in character_data["characters"][0]["appearance"]["accessories"]

    prompt_text = (keyframe_dir / "keyframe_prompts.md").read_text(encoding="utf-8")
    assert "地点：便利店门口" in prompt_text
    assert "天气：雨夜" in prompt_text
    assert "关键道具：最后一把伞" in prompt_text
    assert "关键道具：热可可" in prompt_text
    assert "构图重点：" in prompt_text
    assert "镜头意图：" in prompt_text
    assert all(shot.get("intent_summary") for shot in keyframe_data["shot_prompts"])
    assert all("地点：" in shot["scene_summary"] for shot in keyframe_data["shot_prompts"])
    assert all("天气：" in shot["scene_summary"] for shot in keyframe_data["shot_prompts"])
    assert "Character identity anchor:" in keyframe_data["shot_prompts"][0]["consistency_prompt"]
    assert "Primary protagonist must remain 20岁出头的女孩" in keyframe_data["shot_prompts"][0]["start_keyframe_prompt"]
    assert "do not swap protagonist identity" in keyframe_data["shot_prompts"][0]["end_keyframe_prompt"]


def test_stage02_to_stage04_reuse_upstream_story_anchors_instead_of_rereading_brief(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260603_000100_anchor_truth"
    intake_dir = project_dir / "00_intake"
    script_dir = project_dir / "01_script"
    storyboard_dir = project_dir / "02_storyboard"
    character_dir = project_dir / "03_characters"
    keyframe_dir = project_dir / "04_keyframes"
    for path in [intake_dir, script_dir, storyboard_dir, character_dir, keyframe_dir]:
        path.mkdir(parents=True, exist_ok=True)

    brief = load_example_brief()
    brief.update({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
    })
    brief["normalized"]["idea"] = "一个穿裙子的女生在黄昏的海滩上独自散步。"
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    script = json.loads((TEMPLATES / "script.example.json").read_text(encoding="utf-8"))
    script["project_id"] = project_dir.name
    script["source_brief"] = str(locked_brief).replace("\\", "/")
    script["story_anchors"] = {
        "subject": "20岁出头的女孩",
        "subject_age": "20岁出头",
        "location": "便利店门口",
        "weather": "雨夜",
        "time_of_day": "夜晚",
        "scene_label": "雨夜便利店门口",
        "key_props": ["最后一把伞", "热可可"],
        "action_beats": ["撑着最后一把伞站在门廊边", "把最后一把伞留给陌生人", "淋着雨走远", "回头看见热可可"],
        "emotion_beats": ["安静", "克制善意", "落寞余温", "意外回暖"],
        "composition_beats": ["先用竖屏建立镜头交代雨夜便利店门口与雨夜，人物与最后一把伞同框。"],
    }
    script_json = script_dir / "script.json"
    script_json.write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")

    stage02_packet = build_stage02_prompt_packet.build_packet(brief, script, locked_brief, script_json)
    assert stage02_packet["story_anchors"]["scene_label"] == "雨夜便利店门口"
    assert stage02_packet["story_anchors"]["key_props"][:2] == ["最后一把伞", "热可可"]

    storyboard_llm_output = make_stage02_llm_output_for_rainy_store()
    storyboard_json = storyboard_dir / "storyboard.json"
    storyboard_payload = write_stage02_outputs.write_stage02_outputs(
        brief,
        script,
        storyboard_llm_output,
        locked_brief,
        script_json,
        storyboard_dir / "stage02_llm_output.json",
        storyboard_json,
    )
    assert storyboard_payload["story_anchors"]["scene_label"] == "雨夜便利店门口"
    assert storyboard_payload["story_anchors"]["location"] == "便利店门口"

    stage03_packet = build_stage03_prompt_packet.build_packet(
        brief,
        script,
        storyboard_payload,
        locked_brief,
        script_json,
        storyboard_json,
    )
    assert stage03_packet["story_anchors"]["scene_label"] == "雨夜便利店门口"
    assert stage03_packet["story_anchors"]["weather"] == "雨夜"

    character_llm_output = make_stage03_llm_output_for_rainy_store()
    character_json = character_dir / "character_bible.json"
    character_payload = write_stage03_outputs.write_stage03_outputs(
        brief,
        script,
        storyboard_payload,
        character_llm_output,
        locked_brief,
        script_json,
        storyboard_json,
        character_dir / "stage03_llm_output.json",
        character_json,
    )
    assert character_payload["story_anchors"]["scene_label"] == "雨夜便利店门口"
    assert character_payload["story_anchors"]["key_props"][:2] == ["最后一把伞", "热可可"]

    stage04_packet = build_stage04_prompt_packet.build_packet(
        brief,
        script,
        storyboard_payload,
        character_payload,
        locked_brief,
        script_json,
        storyboard_json,
        character_json,
    )
    assert stage04_packet["story_anchors"]["scene_label"] == "雨夜便利店门口"
    assert stage04_packet["story_anchors"]["key_props"][:2] == ["最后一把伞", "热可可"]

    keyframe_llm_output = make_stage04_llm_output_for_rainy_store()
    keyframe_json = keyframe_dir / "keyframe_prompts.json"
    keyframe_payload = write_stage04_outputs.write_stage04_outputs(
        brief,
        script,
        storyboard_payload,
        character_payload,
        keyframe_llm_output,
        locked_brief,
        script_json,
        storyboard_json,
        character_json,
        keyframe_dir / "stage04_llm_output.json",
        keyframe_json,
    )
    assert keyframe_payload["story_anchors"]["scene_label"] == "雨夜便利店门口"
    assert keyframe_payload["story_anchors"]["location"] == "便利店门口"
    assert keyframe_payload["story_anchors"]["key_props"][:2] == ["最后一把伞", "热可可"]


def test_rainy_store_story_anchors_survive_stage06_to_stage08_and_tiny_rough_cut_cannot_pass(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "creator_trial_20260530_rainy_store"
    intake_dir = project_dir / "00_intake"
    script_dir = project_dir / "01_script"
    storyboard_dir = project_dir / "02_storyboard"
    character_dir = project_dir / "03_characters"
    keyframe_dir = project_dir / "04_keyframes"
    images_dir = project_dir / "05_images"
    video_dir = project_dir / "06_video_clips"
    audio_dir = project_dir / "07_audio"
    assembly_dir = project_dir / "08_assembly"
    for path in [intake_dir, script_dir, storyboard_dir, character_dir, keyframe_dir, images_dir, video_dir, audio_dir, assembly_dir]:
        path.mkdir(parents=True, exist_ok=True)

    manifest_path = project_dir / "project_manifest.json"
    manifest_path.write_text(json.dumps({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "current_stage": "STAGE_04_KEYFRAME_PROMPTS_GENERATION",
        "status": "active",
        "brief_locked": True,
        "keyframe_images_confirmed": True,
        "video_clips_confirmed": True,
        "audio_confirmed": True,
        "assembly_confirmed": True,
        "allowed_next_stage": "STAGE_09_QA",
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    brief = load_rainy_store_brief(project_dir)
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")
    write_stage01_llm_output(script_dir, make_stage01_llm_output_for_rainy_store())

    script_json = script_dir / "script.json"
    assert new_script_template.main(["new_script_template.py", str(locked_brief), str(script_json)]) == 0
    (storyboard_dir / "stage02_llm_output.json").write_text(
        json.dumps(make_stage02_llm_output_for_rainy_store(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    storyboard_json = storyboard_dir / "storyboard.json"
    assert new_storyboard_template.main(["new_storyboard_template.py", str(locked_brief), str(script_json), str(storyboard_json)]) == 0
    (character_dir / "stage03_llm_output.json").write_text(
        json.dumps(make_stage03_llm_output_for_rainy_store(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    character_json = character_dir / "character_bible.json"
    assert new_character_bible_template.main([
        "new_character_bible_template.py",
        str(locked_brief),
        str(script_json),
        str(storyboard_json),
        str(character_json),
    ]) == 0
    (keyframe_dir / "stage04_llm_output.json").write_text(
        json.dumps(make_stage04_llm_output_for_rainy_store(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    keyframe_json = keyframe_dir / "keyframe_prompts.json"
    assert new_keyframe_prompts_template.main([
        "new_keyframe_prompts_template.py",
        str(locked_brief),
        str(script_json),
        str(storyboard_json),
        str(character_json),
        str(keyframe_json),
    ]) == 0

    image_manifest_json = images_dir / "keyframe_image_manifest.json"
    assert new_keyframe_image_jobs.main(["new_keyframe_image_jobs.py", str(locked_brief), str(keyframe_json), str(image_manifest_json)]) == 0
    image_manifest = json.loads(image_manifest_json.read_text(encoding="utf-8"))
    first_shot_jobs = [job for job in image_manifest["jobs"] if job["shot_id"] == "S001"]
    assert any("missing_character_reference" in (job.get("quality_gate") or {}).get("risk_tags", []) for job in first_shot_jobs)
    assert any("Character identity anchor:" in job.get("consistency_prompt", "") for job in first_shot_jobs)
    for job in image_manifest["jobs"]:
        output_path = Path(job["output_path"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"png")
    image_manifest_json.write_text(json.dumps(image_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    old_argv = sys.argv[:]
    try:
        sys.argv = ["sync_keyframe_image_manifest.py", str(image_manifest_json), "--provider", "openai_image"]
        assert sync_keyframe_image_manifest.main() == 0
        sys.argv = [
            "approve_stage05_review_queue.py",
            str(image_manifest_json),
            "--all-pending",
            "--content-aligned",
            "--content-alignment-note",
            "Rainy store creator sample approved after Stage 05 review workbench inspection.",
        ]
        assert approve_stage05_review_queue.main() == 0
    finally:
        sys.argv = old_argv

    clip_manifest_json = video_dir / "video_clip_manifest.json"
    assert new_video_clip_jobs.main([
        "new_video_clip_jobs.py",
        str(locked_brief),
        str(storyboard_json),
        str(keyframe_json),
        str(image_manifest_json),
        str(clip_manifest_json),
    ]) == 0
    clip_manifest = json.loads(clip_manifest_json.read_text(encoding="utf-8"))
    clip_text = json.dumps(clip_manifest, ensure_ascii=False)
    assert "雨夜便利店门口" in clip_text
    assert "最后一把伞" in clip_text
    assert "热可可" in clip_text
    assert "海边女孩" not in clip_text
    assert "核心场景" not in clip_text
    for job in clip_manifest["jobs"]:
        output_path = Path(job["output_path"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"\x00\x00\x00\x18ftypmp42REALCLIP" + (b"0" * 512))
        job["status"] = "succeeded"
        job["provider"] = "comfyui_ltx_i2v"
    clip_manifest_json.write_text(json.dumps(clip_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    old_argv = sys.argv[:]
    try:
        sys.argv = ["sync_video_clip_manifest.py", str(clip_manifest_json)]
        assert sync_video_clip_manifest.main() == 0
    finally:
        sys.argv = old_argv

    audio_manifest_json = audio_dir / "audio_manifest.json"
    assert new_audio_jobs.main([
        "new_audio_jobs.py",
        str(locked_brief),
        str(script_json),
        str(storyboard_json),
        str(character_json),
        str(clip_manifest_json),
        str(audio_manifest_json),
    ]) == 0
    audio_manifest = json.loads(audio_manifest_json.read_text(encoding="utf-8"))
    audio_text = json.dumps(audio_manifest, ensure_ascii=False)
    assert "雨夜便利店门口" in audio_text
    assert "热可可" in audio_text
    assert "海边女孩" not in audio_text
    assert "核心场景" not in audio_text
    voiceovers = [job for job in audio_manifest["jobs"] if job["audio_type"] == "voiceover"]
    assert voiceovers
    assert all(job["speaker_name"] == "旁白" for job in voiceovers)
    for job in audio_manifest["jobs"]:
        output_path = Path(job["output_path"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"audio-output")
        job["status"] = "succeeded"
        job["provider"] = "manual"
    audio_manifest_json.write_text(json.dumps(audio_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        sys.argv = ["sync_audio_manifest.py", str(audio_manifest_json)]
        assert sync_audio_manifest.main() == 0
    finally:
        sys.argv = old_argv

    assembly_manifest_json = assembly_dir / "assembly_manifest.json"
    assert new_assembly_manifest.main([
        "new_assembly_manifest.py",
        str(locked_brief),
        str(storyboard_json),
        str(clip_manifest_json),
        str(audio_manifest_json),
        str(assembly_manifest_json),
    ]) == 0
    assembly_manifest = json.loads(assembly_manifest_json.read_text(encoding="utf-8"))
    assembly_text = json.dumps(assembly_manifest, ensure_ascii=False)
    assert "雨夜便利店门口" in assembly_text
    assert "热可可" in assembly_text
    assert "海边女孩" not in assembly_text
    assert "核心场景" not in assembly_text

    rough_cut_path = project_dir / "08_assembly" / "rough_cut" / "rough_cut.mp4"
    rough_cut_path.parent.mkdir(parents=True, exist_ok=True)
    rough_cut_path.write_bytes(b"\x00\x00\x00\x18ftypmp42tiny")
    assembly_manifest["assembly_provider"] = "ffmpeg"
    assembly_manifest["ffmpeg_commands"] = [{
        "command": ["ffmpeg"],
        "provider": "ffmpeg",
        "strategy": "reencode_mix",
        "return_code": 0,
        "stdout_excerpt": "",
        "stderr_excerpt": "",
        "ran_at": "2026-05-30T00:00:00+00:00",
    }]
    assembly_manifest_json.write_text(json.dumps(assembly_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        sys.argv = ["sync_assembly_manifest.py", str(assembly_manifest_json)]
        assert sync_assembly_manifest.main() == 0
    finally:
        sys.argv = old_argv

        synced_assembly = json.loads(assembly_manifest_json.read_text(encoding="utf-8"))
        assert synced_assembly["self_check"]["ready_for_qa_stage"] is False
        assert synced_assembly["allowed_next_stage"] is None
        project_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert project_manifest["current_stage"] == "STAGE_08_ASSEMBLY"
        assert project_manifest["keyframe_images_confirmed"] is True
        assert project_manifest["video_clips_confirmed"] is True
        assert project_manifest["audio_confirmed"] is True
        assert project_manifest["assembly_confirmed"] is False

def test_stage06_stays_draft_only_when_stage05_manual_review_not_cleared(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260531_stage06_draft_only_gate"
    intake_dir = project_dir / "00_intake"
    storyboard_dir = project_dir / "02_storyboard"
    keyframe_dir = project_dir / "04_keyframes"
    images_dir = project_dir / "05_images"
    video_dir = project_dir / "06_video_clips"
    for path in [intake_dir, storyboard_dir, keyframe_dir, images_dir, video_dir]:
        path.mkdir(parents=True, exist_ok=True)

    manifest_path = project_dir / "project_manifest.json"
    manifest_path.write_text(json.dumps({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "current_stage": "STAGE_05_KEYFRAME_IMAGES",
        "status": "active",
        "brief_locked": True,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    brief = load_example_brief()
    brief.update({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-31T12:00:00+08:00",
    })
    brief["user_answers"]["final_output"] = "生成视频片段素材包"
    brief["normalized"]["final_output"] = "生成视频片段素材包"
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    storyboard_json = storyboard_dir / "storyboard.json"
    storyboard_json.write_text(json.dumps({
        "stage": "STAGE_02_STORYBOARD_GENERATION",
        "project_id": project_dir.name,
        "shots": [{
            "shot_id": "S001",
            "duration_sec": 4,
            "scene": "雨夜便利店门口",
            "location": "便利店门口",
            "weather": "雨夜",
            "key_prop": "最后一把伞",
            "action": "女孩把最后一把伞递给陌生人",
            "emotion": "克制善意",
        }],
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    prompts_json = keyframe_dir / "keyframe_prompts.json"
    prompts_json.write_text(json.dumps({
        "stage": "STAGE_04_KEYFRAME_PROMPTS",
        "project_id": project_dir.name,
        "shot_prompts": [{
            "shot_id": "S001",
            "duration_sec": 4,
            "motion_prompt": "完成一次清晰的递伞动作",
            "negative_prompt": "多手，重复道具",
        }],
        "global_negative_prompt": "多手，重复道具",
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    start_image = images_dir / "S001_start.png"
    end_image = images_dir / "S001_end.png"
    start_image.write_bytes(b"png-start")
    end_image.write_bytes(b"png-end")
    image_manifest_json = images_dir / "keyframe_image_manifest.json"
    image_manifest_json.write_text(json.dumps({
        "stage": "STAGE_05_KEYFRAME_IMAGES",
        "status": "generated",
        "project_id": project_dir.name,
        "stage05_mode": "reference_guided_storyboard",
        "reference_guidance_active": True,
        "image_provider_strategy": {"primary": "openai_image", "fallback": ["comfyui", "manual"]},
        "jobs": [
            {
                "image_id": "IMG_S001_START",
                "shot_id": "S001",
                "frame_role": "start",
                "output_path": str(start_image).replace("\\", "/"),
                "provider": "openai_image",
                "evidence": {"file_path": str(start_image).replace("\\", "/"), "file_exists": True, "file_size_bytes": start_image.stat().st_size},
            },
            {
                "image_id": "IMG_S001_END",
                "shot_id": "S001",
                "frame_role": "end",
                "output_path": str(end_image).replace("\\", "/"),
                "provider": "openai_image",
                "evidence": {"file_path": str(end_image).replace("\\", "/"), "file_exists": True, "file_size_bytes": end_image.stat().st_size},
            },
        ],
        "quality_review": {
            "blocking_image_ids": ["IMG_S001_START"],
            "next_review_image_ids": ["IMG_S001_START"],
            "manual_review_cleared": False,
        },
        "self_check": {
            "all_required_images_exist": True,
            "manual_review_cleared": False,
            "ready_for_video_clip_generation": False,
        },
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    clip_manifest_json = video_dir / "video_clip_manifest.json"
    assert new_video_clip_jobs.main([
        "new_video_clip_jobs.py",
        str(locked_brief),
        str(storyboard_json),
        str(prompts_json),
        str(image_manifest_json),
        str(clip_manifest_json),
    ]) == 0

    planned = json.loads(clip_manifest_json.read_text(encoding="utf-8"))
    assert planned["planning_overrides"]["stage05_gate_ready_for_stage06"] is False
    assert planned["formal_promotion_status"] == "draft_only"
    assert any("Stage 05 review is not cleared yet" in item for item in planned["self_check"]["notes"])

    for job in planned["jobs"]:
        output_path = Path(job["output_path"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"\x00\x00\x00\x18ftypmp42REALCLIP" + (b"0" * 512))
        job["status"] = "succeeded"
        job["provider"] = "comfyui_ltx_i2v"
    clip_manifest_json.write_text(json.dumps(planned, ensure_ascii=False, indent=2), encoding="utf-8")

    old_argv = sys.argv[:]
    try:
        sys.argv = ["sync_video_clip_manifest.py", str(clip_manifest_json)]
        assert sync_video_clip_manifest.main() == 0
    finally:
        sys.argv = old_argv

    synced = json.loads(clip_manifest_json.read_text(encoding="utf-8"))
    assert synced["self_check"]["all_required_clips_exist"] is True
    assert synced["self_check"]["ready_for_audio_stage"] is False
    assert synced["self_check"]["formal_progression_ready"] is False
    assert synced["allowed_next_stage"] is None
    assert synced["formal_promotion_status"] == "draft_only"
    assert any("formal_progression_blocker:" in item for item in synced["self_check"]["notes"])

    project_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert project_manifest["current_stage"] == "STAGE_05_KEYFRAME_IMAGES"
    assert project_manifest["video_clips_confirmed"] is False


def test_lock_project_brief_derives_routing_and_updates_manifest(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260528_103000_sunset_beach_girl"
    intake_dir = project_dir / "00_intake"
    intake_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = project_dir / "project_manifest.json"
    manifest_path.write_text(json.dumps({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "current_stage": "STAGE_00_INTAKE",
        "brief_locked": False,
        "allowed_next_stage": None,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    draft = load_example_brief()
    draft["project_id"] = project_dir.name
    draft["project_dir"] = str(project_dir).replace("\\", "/")
    draft["status"] = "draft"
    draft["confirmed_by_user"] = False
    draft["normalized"]["final_output"] = "只要剧本"
    draft_path = intake_dir / "project_brief.draft.json"
    draft_path.write_text(json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8")
    locked_path = intake_dir / "project_brief.locked.json"

    assert lock_project_brief.main(["lock_project_brief.py", str(draft_path), str(locked_path)]) == 0
    locked = json.loads(locked_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert locked["routing"]["requested_output_scope"] == "script_only"
    assert locked["routing"]["requested_terminal_stage"] == "STAGE_01_SCRIPT_CONFIRMED"
    assert locked["compiled_requirements"]["requested_output_scope"] == "script_only"
    assert locked["quality_contract"]["project_shape"] == locked["compiled_requirements"]["project_shape"]
    assert locked["quality_contract"]["axes"]
    assert manifest["requested_terminal_stage"] == "STAGE_01_SCRIPT_CONFIRMED"
    assert manifest["compiled_requirements"]["requested_output_scope"] == "script_only"
    assert manifest["quality_contract"]["axes"]
    creator_home = json.loads((project_dir / "creator_home.json").read_text(encoding="utf-8"))
    recommended_entry = creator_home["recommended_entry"]
    assert recommended_entry["label"] == "运行 Stage 01 自动剧本生成"
    assert "run_stage01_from_locked_brief.py" in recommended_entry["command"]
    assert "00_intake/project_brief.locked.json" in recommended_entry["command"]
    assert "01_script/script.json" in recommended_entry["command"]


def test_stage00_question_blocks_stay_aligned_with_canonical_option_mapping() -> None:
    canonical = (INTAKE.parent / "references" / "first_layer_options.md").read_text(encoding="utf-8")
    question_blocks = (INTAKE.parent / "references" / "stage00_question_blocks.md").read_text(encoding="utf-8")

    expected_pairs = [
        ("| B | 30秒 | 30 |", "B. 30秒"),
        ("| H | 自定义 | custom |", "H. 自定义"),
        ("| C | 恐怖惊悚 |", "C. 恐怖惊悚"),
        ("| P | 音乐MV |", "P. 音乐MV"),
        ("| C | 日系动画风（日本动漫感） |", "C. 日系动画风（日本动漫感）"),
        ("| I | 温暖治愈 |", "I. 温暖治愈"),
        ("| B | 16:9 横屏 | 16:9 |", "B. 16:9 横屏"),
        ("| 2 | 1080P | Recommended default |", "2. 1080P"),
        ("| C | 由模型根据故事自动判断 |", "C. 由模型根据故事自动判断"),
        ("| A | 不需要配音 |", "A. 不需要配音"),
        ("| B3 | 需要，背景配乐（underscore） |", "B3. 需要，背景配乐（underscore）"),
        ("| F | 合成粗剪成片 |", "F. 合成粗剪成片"),
    ]
    for canonical_snippet, prompt_snippet in expected_pairs:
        assert canonical_snippet in canonical
        assert prompt_snippet in question_blocks

    assert "情绪氛围片" not in question_blocks
    assert "清冷孤独" not in question_blocks


def test_stage00_skills_reference_canonical_question_block_source() -> None:
    intake_skill = (ROOT / "skills" / "video-project-intake" / "SKILL.md").read_text(encoding="utf-8")
    pipeline_skill = (ROOT / "skills" / "video-production-pipeline" / "SKILL.md").read_text(encoding="utf-8")
    startup_doc = (ROOT / "CODEX_START_HERE.md").read_text(encoding="utf-8")

    assert "references/stage00_question_blocks.md" in intake_skill
    assert "references/first_layer_options.md" in intake_skill
    assert "stage00_question_blocks.md" in pipeline_skill
    assert "first_layer_options.md" in pipeline_skill
    assert "stage00_question_blocks.md" in startup_doc


def test_show_creator_home_recommends_stage01_command_after_brief_lock(tmp_path: Path, capsys) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260528_103000_sunset_beach_girl"
    intake_dir = project_dir / "00_intake"
    intake_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = project_dir / "project_manifest.json"
    manifest_path.write_text(json.dumps({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "current_stage": "STAGE_00_BRIEF_LOCKED",
        "status": "active",
        "brief_locked": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    brief = load_example_brief()
    brief.update({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-28T10:35:00+08:00",
    })
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    assert show_creator_home.main(["--project-dir", str(project_dir)]) == 0
    output = capsys.readouterr().out
    assert "TRUSTED_STAGE: STAGE_00_BRIEF_LOCKED" in output
    assert "RECOMMENDED_ENTRY_LABEL: 运行 Stage 01 自动剧本生成" in output
    assert "RECOMMENDED_ENTRY_COMMAND: python skills/video-production-pipeline/scripts/run_stage01_from_locked_brief.py" in output


def test_continue_pipeline_dispatches_brief_locked_project_to_stage01_runner(tmp_path: Path, monkeypatch, capsys) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260528_103000_sunset_beach_girl"
    intake_dir = project_dir / "00_intake"
    intake_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = project_dir / "project_manifest.json"
    manifest_path.write_text(json.dumps({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "current_stage": "STAGE_00_BRIEF_LOCKED",
        "status": "active",
        "brief_locked": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    brief = load_example_brief()
    brief.update({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-28T10:35:00+08:00",
    })
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    called: dict[str, object] = {}

    def fake_stage01(argv):  # noqa: ANN001
        called["argv"] = list(argv)
        return 0

    monkeypatch.setattr(continue_pipeline.run_stage01_from_locked_brief, "main", fake_stage01)

    assert continue_pipeline.main(["--project-dir", str(project_dir)]) == 0
    output = capsys.readouterr().out
    assert "PIPELINE_DISPATCH_STAGE: STAGE_01_SCRIPT_GENERATION" in output
    assert "run_stage01_from_locked_brief.py" in output
    assert called["argv"] == [
        str((project_dir / "00_intake" / "project_brief.locked.json")),
        str((project_dir / "01_script" / "script.json")),
    ]


def test_continue_pipeline_dispatches_script_confirmed_project_to_stage02_runner(tmp_path: Path, monkeypatch, capsys) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260602_233000_stage02_dispatch"
    paths = seed_confirmed_stage_chain(project_dir)
    manifest_path = project_dir / "project_manifest.json"
    manifest_path.write_text(json.dumps({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "current_stage": "STAGE_01_SCRIPT_CONFIRMED",
        "status": "active",
        "brief_locked": True,
        "script_confirmed": True,
        "storyboard_confirmed": False,
        "allowed_next_stage": "STAGE_02_STORYBOARD",
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    called: dict[str, object] = {}

    def fake_stage02(argv):  # noqa: ANN001
        called["argv"] = list(argv)
        return 0

    monkeypatch.setattr(continue_pipeline.run_stage02_from_confirmed_script, "main", fake_stage02)

    assert continue_pipeline.main(["--project-dir", str(project_dir)]) == 0
    output = capsys.readouterr().out
    assert "PIPELINE_DISPATCH_STAGE: STAGE_02_STORYBOARD_GENERATION" in output
    assert "run_stage02_from_confirmed_script.py" in output
    assert called["argv"] == [
        str(paths["locked_brief"]),
        str(paths["script_json"]),
        str(paths["storyboard_json"]),
    ]


def test_continue_pipeline_dispatches_storyboard_confirmed_project_to_stage03_runner(tmp_path: Path, monkeypatch, capsys) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260602_233100_stage03_dispatch"
    paths = seed_confirmed_stage_chain(project_dir)
    manifest_path = project_dir / "project_manifest.json"
    manifest_path.write_text(json.dumps({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "current_stage": "STAGE_02_STORYBOARD_CONFIRMED",
        "status": "active",
        "brief_locked": True,
        "script_confirmed": True,
        "storyboard_confirmed": True,
        "character_bible_confirmed": False,
        "allowed_next_stage": "STAGE_03_CHARACTER_BIBLE",
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    called: dict[str, object] = {}

    def fake_stage03(argv):  # noqa: ANN001
        called["argv"] = list(argv)
        return 0

    monkeypatch.setattr(continue_pipeline.run_stage03_from_confirmed_storyboard, "main", fake_stage03)

    assert continue_pipeline.main(["--project-dir", str(project_dir)]) == 0
    output = capsys.readouterr().out
    assert "PIPELINE_DISPATCH_STAGE: STAGE_03_CHARACTER_BIBLE_GENERATION" in output
    assert "run_stage03_from_confirmed_storyboard.py" in output
    assert called["argv"] == [
        str(paths["locked_brief"]),
        str(paths["script_json"]),
        str(paths["storyboard_json"]),
        str(paths["character_json"]),
    ]


def test_continue_pipeline_dispatches_character_confirmed_project_to_stage04_runner(tmp_path: Path, monkeypatch, capsys) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260602_233200_stage04_dispatch"
    paths = seed_confirmed_stage_chain(project_dir)
    manifest_path = project_dir / "project_manifest.json"
    manifest_path.write_text(json.dumps({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "current_stage": "STAGE_03_CHARACTER_BIBLE_CONFIRMED",
        "status": "active",
        "brief_locked": True,
        "script_confirmed": True,
        "storyboard_confirmed": True,
        "character_bible_confirmed": True,
        "keyframe_prompts_confirmed": False,
        "allowed_next_stage": "STAGE_04_KEYFRAME_PROMPTS",
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    called: dict[str, object] = {}

    def fake_stage04(argv):  # noqa: ANN001
        called["argv"] = list(argv)
        return 0

    monkeypatch.setattr(continue_pipeline.run_stage04_from_confirmed_character_bible, "main", fake_stage04)

    assert continue_pipeline.main(["--project-dir", str(project_dir)]) == 0
    output = capsys.readouterr().out
    assert "PIPELINE_DISPATCH_STAGE: STAGE_04_KEYFRAME_PROMPTS_GENERATION" in output
    assert "run_stage04_from_confirmed_character_bible.py" in output
    assert called["argv"] == [
        str(paths["locked_brief"]),
        str(paths["script_json"]),
        str(paths["storyboard_json"]),
        str(paths["character_json"]),
        str(paths["keyframe_json"]),
    ]


def test_stage05_compiler_keeps_comfyui_first_for_anime_projects(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260528_103000_anime_demo"
    intake_dir = project_dir / "00_intake"
    keyframe_dir = project_dir / "04_keyframes"
    images_dir = project_dir / "05_images"
    intake_dir.mkdir(parents=True, exist_ok=True)
    keyframe_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    brief = load_example_brief()
    brief.update({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-28T10:35:00+08:00",
    })
    brief["normalized"]["genre"] = "动漫短片"
    brief["normalized"]["style"] = "日系动画风（日本动漫感）"
    brief["normalized"]["final_output"] = "生成关键帧图片素材包"
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    keyframe = json.loads((TEMPLATES / "keyframe_prompts.example.json").read_text(encoding="utf-8"))
    keyframe["project_id"] = project_dir.name
    keyframe["source_brief"] = str(locked_brief).replace("\\", "/")
    keyframe["shot_prompts"][0]["style_prompt"] = "anime key visual, clean cel shading"
    keyframe_json = keyframe_dir / "keyframe_prompts.json"
    keyframe_json.write_text(json.dumps(keyframe, ensure_ascii=False, indent=2), encoding="utf-8")

    image_manifest_json = images_dir / "keyframe_image_manifest.json"
    assert new_keyframe_image_jobs.main(["new_keyframe_image_jobs.py", str(locked_brief), str(keyframe_json), str(image_manifest_json)]) == 0
    data = json.loads(image_manifest_json.read_text(encoding="utf-8"))
    assert data["compiled_requirements"]["visual_family_hint"] == "anime"
    assert data["image_provider_strategy"]["primary"] == "comfyui_txt2img"
    assert data["jobs"][0]["provider_priority"][0] == "comfyui_txt2img"
    assert data["stage05_route_key"] == "anime_jp"
    assert data["stage05_mode"] == "reference_guided_storyboard"
    assert data["comfyui_workflow_mapping_key"] == "stage05_realistic_cinematic_qwen_edit_nextscene_local"
    assert data["comfyui_model_id"] == "Qwen/Qwen-Edit-2511"
    assert data["preferred_comfyui_workflow_candidate"] == "qwen_edit_nextscene_local"
    assert data["preferred_comfyui_model_candidate"] == "Qwen/Qwen-Edit-2511"
    assert data["route_migration_state"] == "stage05b_reference_guided_mainline"
    assert data["reference_bootstrap"]["workflow_mapping_key"] == "stage05_anime_jp"
    assert data["reference_bootstrap"]["workflow_name"] == "amazing_z_image_a_safetensors"
    assert data["jobs"][0]["comfyui_workflow_name"] == "qwen_edit_nextscene_local"
    assert data["jobs"][0]["comfyui_workflow_mapping_key"] == "stage05_realistic_cinematic_qwen_edit_nextscene_local"
    assert data["jobs"][0]["comfyui_model_id"] == "Qwen/Qwen-Edit-2511"
    assert data["jobs"][0]["preferred_comfyui_workflow_candidate"] == "qwen_edit_nextscene_local"
    assert data["jobs"][0]["preferred_comfyui_model_candidate"] == "Qwen/Qwen-Edit-2511"
    assert data["jobs"][0]["route_migration_state"] == "stage05b_reference_guided_mainline"
    assert data["jobs"][0]["stage05_route_key"] == "anime_jp"
    assert data["route_resolution"]["used_registry"] is True
    assert data["route_resolution"]["resolution_mode"] == "stage00_style_registry_plus_stage05b_mainline"
    assert data["route_resolution"]["workflow_mapping_resolution"] == "stage05b_qwen_nextscene_mainline"
    assert data["route_resolution"]["preferred_comfyui_workflow_candidate"] == "qwen_edit_nextscene_local"
    assert data["route_resolution"]["preferred_comfyui_model_candidate"] == "Qwen/Qwen-Edit-2511"
    assert data["route_resolution"]["route_migration_state"] == "stage05b_reference_guided_mainline"


def test_stage05_route_registry_maps_cn_animation_style_to_new_route_key(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260528_103000_cn_anime_demo"
    intake_dir = project_dir / "00_intake"
    keyframe_dir = project_dir / "04_keyframes"
    images_dir = project_dir / "05_images"
    intake_dir.mkdir(parents=True, exist_ok=True)
    keyframe_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    brief = load_example_brief()
    brief.update({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-28T10:35:00+08:00",
    })
    brief["normalized"]["genre"] = "动画短片"
    brief["normalized"]["style"] = "国漫动画风（中国动画/新国风）"
    brief["normalized"]["final_output"] = "生成关键帧图片素材包"
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    keyframe = json.loads((TEMPLATES / "keyframe_prompts.example.json").read_text(encoding="utf-8"))
    keyframe["project_id"] = project_dir.name
    keyframe["source_brief"] = str(locked_brief).replace("\\", "/")
    keyframe["shot_prompts"][0]["style_prompt"] = "anime key visual, eastern architecture, refined line art"
    keyframe_json = keyframe_dir / "keyframe_prompts.json"
    keyframe_json.write_text(json.dumps(keyframe, ensure_ascii=False, indent=2), encoding="utf-8")

    image_manifest_json = images_dir / "keyframe_image_manifest.json"
    assert new_keyframe_image_jobs.main(["new_keyframe_image_jobs.py", str(locked_brief), str(keyframe_json), str(image_manifest_json)]) == 0
    data = json.loads(image_manifest_json.read_text(encoding="utf-8"))
    assert data["stage05_route_key"] == "anime_cn_newguofeng"
    assert data["style_family"] == "anime"
    assert data["stage05_mode"] == "reference_guided_storyboard"
    assert data["comfyui_workflow_mapping_key"] == "stage05_realistic_cinematic_qwen_edit_nextscene_local"
    assert data["comfyui_model_id"] == "Qwen/Qwen-Edit-2511"
    assert data["preferred_comfyui_workflow_candidate"] == "qwen_edit_nextscene_local"
    assert data["preferred_comfyui_model_candidate"] == "Qwen/Qwen-Edit-2511"
    assert data["route_migration_state"] == "stage05b_reference_guided_mainline"
    assert data["reference_bootstrap"]["workflow_mapping_key"] == "stage05_anime_jp"
    assert data["reference_bootstrap"]["workflow_name"] == "amazing_z_image_a_safetensors"
    assert data["jobs"][0]["comfyui_workflow_name"] == "qwen_edit_nextscene_local"
    assert data["jobs"][0]["comfyui_workflow_mapping_key"] == "stage05_realistic_cinematic_qwen_edit_nextscene_local"
    assert data["route_resolution"]["used_registry"] is True


def test_validate_keyframe_image_manifest_example_final() -> None:
    data = json.loads((TEMPLATES / "keyframe_image_manifest.example.json").read_text(encoding="utf-8"))
    assert data["stage05_route_key"] == "realistic_cinematic"
    assert data["stage05_mode"] == "reference_guided_storyboard"
    assert data["comfyui_workflow_mapping_key"] == "stage05_realistic_cinematic_qwen_edit_nextscene_local"
    assert data["comfyui_model_id"] == "Qwen/Qwen-Edit-2511"
    assert data["preferred_comfyui_workflow_candidate"] == "qwen_edit_nextscene_local"
    assert data["preferred_comfyui_model_candidate"] == "Qwen/Qwen-Edit-2511"
    assert data["route_migration_state"] == "stage05b_reference_guided_mainline"
    assert data["preferred_comfyui_workflow_source_ref"] == "F:/ComfyUI/ComfyUI/user/default/workflows/AI漫剧制作/AI漫剧-16宫格分镜图生成-QwenEdit+NextScene（自动分镜）-V1版.json"
    assert data["preferred_comfyui_workflow_format"] == "ui_graph"
    assert data["preferred_comfyui_workflow_custom_node_dependencies"] == ["rgthree-comfy"]
    assert data["preferred_comfyui_workflow_import_blockers"] == []
    assert data["route_resolution"]["resolution_mode"] == "stage00_style_registry_plus_stage05b_mainline"
    assert all(job["stage05_route_key"] == "realistic_cinematic" for job in data["jobs"])
    assert all(job["comfyui_workflow_mapping_key"] == "stage05_realistic_cinematic_qwen_edit_nextscene_local" for job in data["jobs"])
    assert all(job["comfyui_workflow_name"] == "qwen_edit_nextscene_local" for job in data["jobs"])
    assert all(job["preferred_comfyui_workflow_candidate"] == "qwen_edit_nextscene_local" for job in data["jobs"])
    assert all(job["preferred_comfyui_model_candidate"] == "Qwen/Qwen-Edit-2511" for job in data["jobs"])
    assert all(job["route_migration_state"] == "stage05b_reference_guided_mainline" for job in data["jobs"])
    assert all(job["preferred_comfyui_workflow_format"] == "ui_graph" for job in data["jobs"])
    example_job = dict(data["jobs"][0])
    example_job["image_id"] = "IMG_S001_END"
    example_job["frame_role"] = "end"
    example_job["source_prompt_ref"] = "keyframe_prompts.json#S001.end"
    example_job["output_path"] = "example_keyframe_images/S001_end.png"
    example_job["evidence"] = {
        "file_path": "example_keyframe_images/S001_end.png",
        "file_exists": True,
        "file_size_bytes": 1263,
        "created_at": "2026-06-04T10:50:00+08:00",
    }
    data["jobs"].append(example_job)
    data["summary"]["expected_image_count"] = 2
    data["summary"]["generated_image_count"] = 2
    data["quality_signals"] = {
        "intent_route_matches_strategy": True,
        "style_route_matches_stage00": True,
        "style_route_matches_strategy": True,
        "reference_guidance_state_consistent": True,
        "consistency_prompts_present": True,
        "shot_consistency_prompts_present": True,
        "quality_targets_defined": True,
    }
    ok, errors, warnings = validate_keyframe_image_manifest.validate(data, TEMPLATES / "keyframe_image_manifest.example.json", mode="final")
    assert ok, errors


def test_new_keyframe_image_jobs_passes_draft_then_placeholder_passes_final(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260528_103000_sunset_beach_girl"
    intake_dir = project_dir / "00_intake"
    keyframe_dir = project_dir / "04_keyframes"
    images_dir = project_dir / "05_images"
    intake_dir.mkdir(parents=True)
    keyframe_dir.mkdir(parents=True)
    images_dir.mkdir(parents=True)

    brief = load_example_brief()
    brief.update({
        "schema_version": "0.6.0",
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "aspect_ratio": "9:16",
        "resolution": "1080P",
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-28T10:35:00+08:00",
    })
    brief["normalized"]["final_output"] = "生成关键帧图片素材包"
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    keyframe = json.loads((TEMPLATES / "keyframe_prompts.example.json").read_text(encoding="utf-8"))
    keyframe["project_id"] = project_dir.name
    keyframe["source_brief"] = str(locked_brief).replace("\\", "/")
    keyframe_json = keyframe_dir / "keyframe_prompts.json"
    keyframe_json.write_text(json.dumps(keyframe, ensure_ascii=False, indent=2), encoding="utf-8")

    manifest_json = images_dir / "keyframe_image_manifest.json"
    assert new_keyframe_image_jobs.main([
        "new_keyframe_image_jobs.py",
        str(locked_brief),
        str(keyframe_json),
        str(manifest_json),
        "--allow-beyond-requested-scope",
    ]) == 0
    data = json.loads(manifest_json.read_text(encoding="utf-8"))
    ok, errors, warnings = validate_keyframe_image_manifest.validate(data, manifest_json, mode="draft")
    assert ok, errors
    assert warnings
    assert data["reference_image_status"]["all_present"] is False
    assert data["stage05_execution_readiness"]["safe_to_auto_generate"] is False
    assert data["reference_guidance_requested"] is True
    assert data["reference_guidance_ready"] is False
    assert data["reference_guidance_active"] is False
    assert "selected_workflow_does_not_accept_reference_images" in data["workflow_capability_gaps"]
    assert data["comfyui_workflow_capabilities"]["supports_reference_images"] is False
    assert len(data["jobs"]) == 2 * len(keyframe["shot_prompts"])
    assert data["style_family"] == "realistic"
    assert data["comfyui_workflow_mapping_key"] == "stage05_realistic_cinematic_amazing_z_photo_original"
    assert data["comfyui_model_id"] == "Tongyi-MAI/Z-Image"
    assert data["preferred_comfyui_workflow_candidate"] == "amazing_z_photo_safetensors"
    assert data["preferred_comfyui_model_candidate"] == "Tongyi-MAI/Z-Image"
    assert data["route_migration_state"] == "repo_transitional"
    assert data["preferred_comfyui_workflow_source_ref"] == "F:/ComfyUI/ComfyUI/user/default/workflows/Zimage/amazing-z-photo_SAFETENSORS.json"
    assert data["preferred_comfyui_workflow_format"] == "ui_graph"
    assert data["comfyui_workflow_router"]["realistic"] == "txt2img_keyframe_realistic"
    assert all(job["style_family"] == "realistic" for job in data["jobs"])
    assert all(job["comfyui_workflow_mapping_key"] == "stage05_realistic_cinematic_amazing_z_photo_original" for job in data["jobs"])
    assert all(job["comfyui_workflow_name"] == "amazing_z_photo_safetensors" for job in data["jobs"])
    assert all(job["preferred_comfyui_workflow_candidate"] == "amazing_z_photo_safetensors" for job in data["jobs"])
    assert all(job["preferred_comfyui_model_candidate"] == "Tongyi-MAI/Z-Image" for job in data["jobs"])
    assert all(job["route_migration_state"] == "repo_transitional" for job in data["jobs"])
    assert all(job["preferred_comfyui_workflow_format"] == "ui_graph" for job in data["jobs"])
    assert all(job["reference_guidance_requested"] is True for job in data["jobs"])
    assert all(job["reference_guidance_active"] is False for job in data["jobs"])

    ok, errors, warnings = validate_keyframe_image_manifest.validate(data, manifest_json, mode="final")
    assert not ok
    assert any("status must be succeeded" in e or "image file does not exist" in e for e in errors)

    # Test-only placeholder generation creates real files and should then pass final validation.
    import sys as _sys
    old_argv = _sys.argv[:]
    try:
        _sys.argv = ["generate_placeholder_keyframe_images.py", str(manifest_json), "--width", "64", "--height", "96"]
        assert generate_placeholder_keyframe_images.main() == 0
    finally:
        _sys.argv = old_argv
    data = json.loads(manifest_json.read_text(encoding="utf-8"))
    ok, errors, warnings = validate_keyframe_image_manifest.validate(data, manifest_json, mode="final")
    assert ok, errors


def test_sync_keyframe_image_manifest_backfills_route_key_from_top_level(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260529_210000_route_sync_demo"
    intake_dir = project_dir / "00_intake"
    keyframe_dir = project_dir / "04_keyframes"
    images_dir = project_dir / "05_images"
    intake_dir.mkdir(parents=True, exist_ok=True)
    keyframe_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    brief = load_example_brief()
    brief.update({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-29T21:00:00+08:00",
    })
    brief["normalized"]["style"] = "日系动画风（日本动漫感）"
    brief["normalized"]["final_output"] = "生成关键帧图片素材包"
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    keyframe = json.loads((TEMPLATES / "keyframe_prompts.example.json").read_text(encoding="utf-8"))
    keyframe["project_id"] = project_dir.name
    keyframe["source_brief"] = str(locked_brief).replace("\\", "/")
    keyframe_json = keyframe_dir / "keyframe_prompts.json"
    keyframe_json.write_text(json.dumps(keyframe, ensure_ascii=False, indent=2), encoding="utf-8")

    manifest_json = images_dir / "keyframe_image_manifest.json"
    assert new_keyframe_image_jobs.main([
        "new_keyframe_image_jobs.py",
        str(locked_brief),
        str(keyframe_json),
        str(manifest_json),
        "--allow-beyond-requested-scope",
    ]) == 0

    data = json.loads(manifest_json.read_text(encoding="utf-8"))
    assert data["stage05_route_key"] == "anime_jp"
    data.pop("stage05_route_key", None)
    data.pop("comfyui_workflow_mapping_key", None)
    data.pop("comfyui_model_id", None)
    data.pop("preferred_comfyui_workflow_candidate", None)
    data.pop("preferred_comfyui_model_candidate", None)
    data.pop("route_migration_state", None)
    for job in data["jobs"]:
        job.pop("stage05_route_key", None)
        job.pop("comfyui_workflow_mapping_key", None)
        job.pop("comfyui_model_id", None)
        job.pop("preferred_comfyui_workflow_candidate", None)
        job.pop("preferred_comfyui_model_candidate", None)
        job.pop("route_migration_state", None)
    manifest_json.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    old_argv = sys.argv[:]
    try:
        sys.argv = ["sync_keyframe_image_manifest.py", str(manifest_json)]
        assert sync_keyframe_image_manifest.main() == 0
    finally:
        sys.argv = old_argv

    synced = json.loads(manifest_json.read_text(encoding="utf-8"))
    assert synced["stage05_route_key"] == "anime_jp"
    assert synced["comfyui_workflow_mapping_key"] == "stage05_anime_jp"
    assert synced["comfyui_model_id"] == "Tongyi-MAI/Z-Image"
    assert synced["preferred_comfyui_workflow_candidate"] == "amazing_z_image_a_safetensors"
    assert synced["preferred_comfyui_model_candidate"] == "Tongyi-MAI/Z-Image"
    assert synced["route_migration_state"] == "repo_transitional"
    assert synced["preferred_comfyui_workflow_source_ref"] == "F:/ComfyUI/ComfyUI/user/default/workflows/Zimage/amazing-z-image-a_SAFETENSORS.json"
    assert all(job["stage05_route_key"] == "anime_jp" for job in synced["jobs"])
    assert all(job["comfyui_workflow_mapping_key"] == "stage05_anime_jp" for job in synced["jobs"])
    assert all(job["comfyui_model_id"] == "Tongyi-MAI/Z-Image" for job in synced["jobs"])
    assert all(job["preferred_comfyui_workflow_candidate"] == "amazing_z_image_a_safetensors" for job in synced["jobs"])
    assert all(job["preferred_comfyui_model_candidate"] == "Tongyi-MAI/Z-Image" for job in synced["jobs"])
    assert all(job["route_migration_state"] == "repo_transitional" for job in synced["jobs"])
    assert synced["status"] == "draft"
    assert synced["summary"]["generated_image_count"] == 0


def test_new_keyframe_image_jobs_activates_reference_guided_mode_when_mapping_supports_it(tmp_path: Path, monkeypatch) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260528_103000_reference_ready"
    intake_dir = project_dir / "00_intake"
    keyframe_dir = project_dir / "04_keyframes"
    images_dir = project_dir / "05_images"
    reference_dir = project_dir / "03_characters" / "reference_images"
    intake_dir.mkdir(parents=True, exist_ok=True)
    keyframe_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)
    reference_dir.mkdir(parents=True, exist_ok=True)

    brief = load_example_brief()
    brief.update({
        "schema_version": "0.5.0",
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-28T10:35:00+08:00",
    })
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    keyframe = json.loads((TEMPLATES / "keyframe_prompts.example.json").read_text(encoding="utf-8"))
    keyframe["project_id"] = project_dir.name
    keyframe["source_brief"] = str(locked_brief).replace("\\", "/")
    keyframe["reference_image_status"] = {
        "required": True,
        "target_paths": ["03_characters/reference_images/CHAR_001_primary.png"],
        "existing_paths": ["03_characters/reference_images/CHAR_001_primary.png"],
        "missing_paths": [],
        "all_present": True,
        "item_count": 1,
        "missing_count": 0,
        "items": [{"character_id": "CHAR_001", "target_path": "03_characters/reference_images/CHAR_001_primary.png", "file_exists": True}],
    }
    keyframe["stage05_execution_readiness"] = {
        "continuity_mode": "character_locked",
        "reference_image_required": True,
        "safe_to_auto_generate": True,
        "blocker_reasons": [],
        "missing_reference_images": [],
    }
    keyframe["self_check"]["character_reference_images_ready"] = True
    keyframe["self_check"]["safe_for_auto_image_generation"] = True
    for shot in keyframe["shot_prompts"]:
        shot["camera_prompt"] = "medium shot"
        shot["start_keyframe_prompt"] = "same heroine waiting under rainy convenience-store light"
        shot["end_keyframe_prompt"] = "the same heroine keeps standing under rainy convenience-store light"
    keyframe_json = keyframe_dir / "keyframe_prompts.json"
    keyframe_json.write_text(json.dumps(keyframe, ensure_ascii=False, indent=2), encoding="utf-8")
    (reference_dir / "CHAR_001_primary.png").write_bytes(b"PNGDATA")

    fake_mapping_path = tmp_path / "workflow_node_mapping.yaml"
    fake_mapping = {
        "workflows": {
            "stage05_realistic_cinematic_amazing_z_photo_original": {
                "file": "workflows/comfyui/fake_reference.workflow_api.json",
                "nodes": {
                    "positive_prompt": {"node_id": "1", "input_name": "text"},
                    "reference_image_path": {"node_id": "2", "input_name": "image"},
                },
                "capabilities": {
                    "supports_reference_images": True,
                    "supported_control_modes": ["prompt_only", "reference_guided"],
                },
            }
        }
    }
    monkeypatch.setattr(new_keyframe_image_jobs, "load_workflow_mapping", lambda root=None: (fake_mapping, fake_mapping_path))
    monkeypatch.setattr(new_keyframe_image_jobs, "get_workflow_mapping", lambda data, workflow_name: data["workflows"][workflow_name])

    manifest_json = images_dir / "keyframe_image_manifest.json"
    assert new_keyframe_image_jobs.main([
        "new_keyframe_image_jobs.py",
        str(locked_brief),
        str(keyframe_json),
        str(manifest_json),
        "--allow-beyond-requested-scope",
    ]) == 0
    data = json.loads(manifest_json.read_text(encoding="utf-8"))
    assert data["comfyui_control_mode"] == "reference_guided"
    assert data["reference_guidance_requested"] is True
    assert data["reference_guidance_ready"] is True
    assert data["reference_guidance_active"] is True
    assert data["workflow_capability_gaps"] == []
    assert data["comfyui_workflow_capabilities"]["supports_reference_images"] is True
    assert all(job["comfyui_control_mode"] == "reference_guided" for job in data["jobs"])
    assert all(job["reference_guidance_active"] is True for job in data["jobs"])


def test_new_keyframe_image_jobs_keeps_qwen_nextscene_route_in_reference_guided_mode(tmp_path: Path, monkeypatch) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260604_180000_qwen_nextscene_reference_ready"
    intake_dir = project_dir / "00_intake"
    keyframe_dir = project_dir / "04_keyframes"
    images_dir = project_dir / "05_images"
    reference_dir = project_dir / "03_characters" / "reference_images"
    intake_dir.mkdir(parents=True, exist_ok=True)
    keyframe_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)
    reference_dir.mkdir(parents=True, exist_ok=True)

    brief = load_example_brief()
    brief.update({
        "schema_version": "0.5.0",
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-06-04T18:00:00+08:00",
    })
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    keyframe = json.loads((TEMPLATES / "keyframe_prompts.example.json").read_text(encoding="utf-8"))
    keyframe["project_id"] = project_dir.name
    keyframe["source_brief"] = str(locked_brief).replace("\\", "/")
    keyframe["reference_image_status"] = {
        "required": True,
        "target_paths": ["03_characters/reference_images/CHAR_001_primary.png"],
        "existing_paths": ["03_characters/reference_images/CHAR_001_primary.png"],
        "missing_paths": [],
        "all_present": True,
        "item_count": 1,
        "missing_count": 0,
        "items": [{"character_id": "CHAR_001", "target_path": "03_characters/reference_images/CHAR_001_primary.png", "file_exists": True}],
    }
    keyframe["stage05_execution_readiness"] = {
        "continuity_mode": "character_locked",
        "reference_image_required": True,
        "safe_to_auto_generate": True,
        "blocker_reasons": [],
        "missing_reference_images": [],
    }
    keyframe["self_check"]["character_reference_images_ready"] = True
    keyframe["self_check"]["safe_for_auto_image_generation"] = True
    keyframe["shot_prompts"] = keyframe["shot_prompts"][:1]
    for shot in keyframe["shot_prompts"]:
        shot["camera_prompt"] = "medium shot"
        shot["start_keyframe_prompt"] = "Next Scene：同一位年轻亚洲女性站在黄昏海边，望向海平线。"
        shot["end_keyframe_prompt"] = "Next Scene：同一位年轻亚洲女性仍然站在黄昏海边，情绪更安静。"
    keyframe_json = keyframe_dir / "keyframe_prompts.json"
    keyframe_json.write_text(json.dumps(keyframe, ensure_ascii=False, indent=2), encoding="utf-8")
    (reference_dir / "CHAR_001_primary.png").write_bytes(b"PNGDATA")

    fake_route_resolution = {
        "route_key": "realistic_cinematic",
        "style_family": "realistic",
        "stage05_mode": "reference_guided_storyboard",
        "comfyui_workflow_mapping_key": "stage05_realistic_cinematic_qwen_edit_nextscene_local",
        "comfyui_workflow_name": "stage05_realistic_cinematic_qwen_edit_nextscene_local",
        "comfyui_model_id": "Qwen/Qwen-Edit-2511",
        "comfyui_style_selector": None,
        "preferred_comfyui_workflow_candidate": "qwen_edit_nextscene_local",
        "preferred_comfyui_model_candidate": "Qwen/Qwen-Edit",
        "route_migration_state": "stage05b_reference_guided_mainline",
        "preferred_comfyui_workflow_source_ref": "F:/ComfyUI/ComfyUI/user/default/workflows/AI漫剧制作/AI漫剧-16宫格分镜图生成-QwenEdit+NextScene（自动分镜）-V1版.json",
        "preferred_comfyui_workflow_format": "ui_graph",
        "preferred_comfyui_workflow_custom_node_dependencies": ["rgthree-comfy"],
        "preferred_comfyui_workflow_import_blockers": [],
        "comfyui_style_preset_key": None,
        "comfyui_style_preset_label": None,
        "comfyui_style_positive_anchor": None,
        "comfyui_style_negative_anchor": None,
        "comfyui_control_mode": "reference_guided",
        "stage00_style": "写实电影感",
        "registry_path": None,
        "used_registry": False,
        "resolution_mode": "manual_qwen_nextscene_override",
        "workflow_mapping_resolution": "manual_qwen_nextscene_override",
        "reference_guided_route_selected": True,
        "reference_bootstrap_workflow_mapping_key": "stage05_realistic_cinematic_amazing_z_photo_original",
        "reference_bootstrap_workflow_name": "amazing_z_photo_safetensors",
        "reference_bootstrap_comfyui_model_id": "Tongyi-MAI/Z-Image",
        "reference_bootstrap_preferred_workflow_candidate": "amazing_z_photo_safetensors",
        "reference_bootstrap_preferred_workflow_source_ref": "F:/ComfyUI/ComfyUI/user/default/workflows/Zimage/amazing-z-photo_SAFETENSORS.json",
        "reference_bootstrap_preferred_workflow_format": "ui_graph",
        "reference_bootstrap_style_preset_key": "classic_film_realism",
        "reference_bootstrap_style_preset_label": "Classic Film Realism",
        "reference_bootstrap_style_positive_anchor": "grounded story-world realism",
        "reference_bootstrap_style_negative_anchor": "studio set contamination",
        "reference_bootstrap_style_selector": "classic_film_photo",
    }
    fake_mapping_path = tmp_path / "workflow_node_mapping.yaml"
    fake_mapping = {
        "workflows": {
            "stage05_realistic_cinematic_qwen_edit_nextscene_local": {
                "file": "workflows/comfyui/fake_qwen_nextscene.workflow.json",
                "nodes": {
                    "positive_prompt": {"node_id": "1", "input_name": "text"},
                    "reference_image_path": {"node_id": "2", "input_name": "image"},
                },
                "capabilities": {
                    "supports_reference_images": True,
                    "supported_control_modes": ["reference_guided"],
                },
            }
        }
    }
    monkeypatch.setattr(new_keyframe_image_jobs, "resolve_stage05_route", lambda brief_obj, prompts_obj: fake_route_resolution)
    monkeypatch.setattr(new_keyframe_image_jobs, "load_workflow_mapping", lambda root=None: (fake_mapping, fake_mapping_path))
    monkeypatch.setattr(new_keyframe_image_jobs, "get_workflow_mapping", lambda data, workflow_name: data["workflows"][workflow_name])

    manifest_json = images_dir / "keyframe_image_manifest.json"
    assert new_keyframe_image_jobs.main([
        "new_keyframe_image_jobs.py",
        str(locked_brief),
        str(keyframe_json),
        str(manifest_json),
        "--allow-beyond-requested-scope",
    ]) == 0
    data = json.loads(manifest_json.read_text(encoding="utf-8"))
    assert data["comfyui_workflow_mapping_key"] == "stage05_realistic_cinematic_qwen_edit_nextscene_local"
    assert data["preferred_comfyui_workflow_source_ref"].endswith("QwenEdit+NextScene（自动分镜）-V1版.json")
    assert data["comfyui_control_mode"] == "reference_guided"
    assert data["reference_guidance_active"] is True
    assert all(job["comfyui_workflow_mapping_key"] == "stage05_realistic_cinematic_qwen_edit_nextscene_local" for job in data["jobs"])
    assert all(job["comfyui_control_mode"] == "reference_guided" for job in data["jobs"])
    assert all(job["reference_guidance_active"] is True for job in data["jobs"])


def test_new_keyframe_image_jobs_promotes_interaction_handoff_to_dual_reference_when_context_frame_exists(tmp_path: Path, monkeypatch) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260531_120000_handoff_dual_ref"
    intake_dir = project_dir / "00_intake"
    keyframe_dir = project_dir / "04_keyframes"
    images_dir = project_dir / "05_images"
    keyframes_output_dir = images_dir / "keyframes"
    reference_dir = project_dir / "03_characters" / "reference_images"
    intake_dir.mkdir(parents=True, exist_ok=True)
    keyframe_dir.mkdir(parents=True, exist_ok=True)
    keyframes_output_dir.mkdir(parents=True, exist_ok=True)
    reference_dir.mkdir(parents=True, exist_ok=True)

    brief = load_example_brief()
    brief.update({
        "schema_version": "0.5.0",
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-31T12:00:00+08:00",
    })
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    keyframe = json.loads((TEMPLATES / "keyframe_prompts.example.json").read_text(encoding="utf-8"))
    keyframe["project_id"] = project_dir.name
    keyframe["source_brief"] = str(locked_brief).replace("\\", "/")
    keyframe["shot_prompts"] = keyframe["shot_prompts"][:1]
    keyframe_json = keyframe_dir / "keyframe_prompts.json"
    keyframe_json.write_text(json.dumps(keyframe, ensure_ascii=False, indent=2), encoding="utf-8")

    (reference_dir / "CHAR_001_primary.png").write_bytes(b"PNGDATA")
    (keyframes_output_dir / "S001_end.png").write_bytes(b"PNGDATA")

    fake_mapping_path = tmp_path / "workflow_node_mapping.yaml"
    fake_mapping = {
        "workflows": {
            "stage05_realistic_cinematic_amazing_z_photo_original": {
                "file": "workflows/comfyui/fake_reference.workflow_api.json",
                "nodes": {
                    "positive_prompt": {"node_id": "1", "input_name": "text"},
                    "reference_image_path": {"node_id": "2", "input_name": "image"},
                },
                "capabilities": {
                    "supports_reference_images": True,
                    "supported_control_modes": ["prompt_only", "reference_guided"],
                },
            },
        }
    }
    monkeypatch.setattr(new_keyframe_image_jobs, "load_workflow_mapping", lambda root=None: (fake_mapping, fake_mapping_path))
    monkeypatch.setattr(new_keyframe_image_jobs, "get_workflow_mapping", lambda data, workflow_name: data["workflows"][workflow_name])
    monkeypatch.setattr(
        new_keyframe_image_jobs,
        "classify_stage06_generation",
        lambda shot_prompt, storyboard_shot, bundle: {"route_hint": "interaction_handoff"},
    )

    manifest_json = images_dir / "keyframe_image_manifest.json"
    assert new_keyframe_image_jobs.main([
        "new_keyframe_image_jobs.py",
        str(locked_brief),
        str(keyframe_json),
        str(manifest_json),
        "--allow-beyond-requested-scope",
    ]) == 0
    data = json.loads(manifest_json.read_text(encoding="utf-8"))
    mid_job = next(job for job in data["jobs"] if job["image_id"] == "IMG_S001_MID")
    assert mid_job["stage06_route_hint"] == "interaction_handoff"
    assert mid_job["comfyui_workflow_mapping_key"] == "stage05_realistic_cinematic_amazing_z_photo_original"
    assert mid_job["comfyui_workflow_name"] == "amazing_z_photo_safetensors"
    assert mid_job["reference_bundle_mode"] == "primary_plus_context_frame"
    assert mid_job["reference_images"] == [
        "03_characters/reference_images/CHAR_001_primary.png",
        "05_images/keyframes/S001_end.png",
    ]
    assert mid_job["secondary_reference_images"] == ["05_images/keyframes/S001_end.png"]
    assert "avoid symmetrical posing" in mid_job["prompt"]
    assert "floating handle" in mid_job["negative_prompt"]


def test_resolve_stage05_route_switches_shortdrama_realistic_to_reference_guided_target_when_refs_ready() -> None:
    brief = {
        "normalized": {
            "style": "短剧爽感",
            "genre": "治愈",
        }
    }
    prompts = {
        "reference_image_status": {
            "all_present": True,
        },
        "stage05_execution_readiness": {
            "reference_image_required": True,
        },
        "shot_prompts": [
            {
                "style_prompt": "realistic dramatic short drama still",
            }
        ],
    }
    resolved = new_keyframe_image_jobs.resolve_stage05_route(brief, prompts)
    assert resolved["used_registry"] is True
    assert resolved["route_key"] == "shortdrama_realistic"
    assert resolved["stage05_mode"] == "reference_guided_storyboard"
    assert resolved["reference_guided_route_selected"] is True
    assert resolved["comfyui_workflow_mapping_key"] == "stage05_realistic_cinematic_qwen_edit_nextscene_local"
    assert resolved["comfyui_workflow_name"] == "qwen_edit_nextscene_local"
    assert resolved["comfyui_model_id"] == "Qwen/Qwen-Edit-2511"
    assert resolved["preferred_comfyui_workflow_candidate"] == "qwen_edit_nextscene_local"
    assert resolved["preferred_comfyui_model_candidate"] == "Qwen/Qwen-Edit-2511"
    assert resolved["comfyui_control_mode"] == "reference_guided"
    assert resolved["reference_bootstrap_workflow_mapping_key"] == "stage05_realistic_cinematic_amazing_z_photo_original"
    assert resolved["reference_bootstrap_workflow_name"] == "amazing_z_photo_safetensors"


def test_resolve_stage05_route_switches_realistic_cinematic_to_reference_guided_target_when_refs_ready() -> None:
    brief = {
        "normalized": {
            "style": "写实电影感",
            "genre": "治愈",
        }
    }
    prompts = {
        "reference_image_status": {
            "all_present": True,
        },
        "stage05_execution_readiness": {
            "reference_image_required": True,
        },
        "shot_prompts": [
            {
                "style_prompt": "realistic cinematic still",
            }
        ],
    }
    resolved = new_keyframe_image_jobs.resolve_stage05_route(brief, prompts)
    assert resolved["used_registry"] is True
    assert resolved["route_key"] == "realistic_cinematic"
    assert resolved["stage05_mode"] == "reference_guided_storyboard"
    assert resolved["reference_guided_route_selected"] is True
    assert resolved["comfyui_workflow_mapping_key"] == "stage05_realistic_cinematic_qwen_edit_nextscene_local"
    assert resolved["comfyui_workflow_name"] == "qwen_edit_nextscene_local"
    assert resolved["comfyui_model_id"] == "Qwen/Qwen-Edit-2511"
    assert resolved["preferred_comfyui_workflow_candidate"] == "qwen_edit_nextscene_local"
    assert resolved["preferred_comfyui_model_candidate"] == "Qwen/Qwen-Edit-2511"
    assert resolved["comfyui_control_mode"] == "reference_guided"
    assert resolved["reference_bootstrap_workflow_mapping_key"] == "stage05_realistic_cinematic_amazing_z_photo_original"
    assert resolved["reference_bootstrap_workflow_name"] == "amazing_z_photo_safetensors"


def test_new_keyframe_jobs_keep_wide_establishing_realistic_shot_on_prompt_only_route_even_with_refs_ready(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260601_223000_establishing_guardrail"
    intake_dir = project_dir / "00_intake"
    keyframe_dir = project_dir / "04_keyframes"
    images_dir = project_dir / "05_images"
    intake_dir.mkdir(parents=True, exist_ok=True)
    keyframe_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    brief = load_example_brief()
    brief.update({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-06-01T22:30:00+08:00",
    })
    brief["normalized"]["style"] = "写实电影感"
    brief["normalized"]["final_output"] = "生成关键帧图片素材包"
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    keyframe = json.loads((TEMPLATES / "keyframe_prompts.example.json").read_text(encoding="utf-8"))
    keyframe["project_id"] = project_dir.name
    keyframe["source_brief"] = str(locked_brief).replace("\\", "/")
    keyframe["reference_image_status"] = {"all_present": True}
    keyframe["stage05_execution_readiness"] = {"reference_image_required": True}
    keyframe["shot_prompts"] = keyframe["shot_prompts"][:1]
    keyframe["shot_prompts"][0]["camera_prompt"] = "wide shot"
    keyframe["shot_prompts"][0]["start_keyframe_prompt"] = "single woman walking along the shoreline at sunset"
    keyframe["shot_prompts"][0]["end_keyframe_prompt"] = "the same woman keeps walking along the shoreline in a wide sunset view"
    keyframe["shot_prompts"][0]["dependencies"] = {
        "reference_images": ["03_characters/reference_images/CHAR_001_primary.png"],
    }
    keyframe_json = keyframe_dir / "keyframe_prompts.json"
    keyframe_json.write_text(json.dumps(keyframe, ensure_ascii=False, indent=2), encoding="utf-8")

    manifest_json = images_dir / "keyframe_image_manifest.json"
    assert new_keyframe_image_jobs.main([
        "new_keyframe_image_jobs.py",
        str(locked_brief),
        str(keyframe_json),
        str(manifest_json),
        "--allow-beyond-requested-scope",
    ]) == 0

    data = json.loads(manifest_json.read_text(encoding="utf-8"))
    start_job = next(job for job in data["jobs"] if job["image_id"] == "IMG_S001_START")
    assert data["comfyui_workflow_mapping_key"] == "stage05_realistic_cinematic_amazing_z_photo_original"
    assert start_job["comfyui_workflow_mapping_key"] == "stage05_realistic_cinematic_amazing_z_photo_original"
    assert start_job["comfyui_workflow_name"] == "amazing_z_photo_safetensors"
    assert start_job["comfyui_style_preset_key"] == "environmental_establishing_film"
    assert start_job["comfyui_style_selector"] == "classic_film_photo"
    assert start_job["comfyui_control_mode"] == "prompt_only"
    assert start_job["prompt_composition_mode"] == "zimage_skill_aligned"
    assert "cinematic keyframe" not in start_job["prompt"]
    assert "realistic cinematic short film" not in start_job["prompt"]
    assert start_job["reference_guidance_active"] is False

    end_job = next(job for job in data["jobs"] if job["image_id"] == "IMG_S001_END")
    assert end_job["comfyui_workflow_mapping_key"] == "stage05_realistic_cinematic_amazing_z_photo_original"
    assert end_job["comfyui_workflow_name"] == "amazing_z_photo_safetensors"
    assert end_job["comfyui_style_preset_key"] == "environmental_establishing_film"
    assert end_job["comfyui_style_selector"] == "classic_film_photo"
    assert end_job["comfyui_control_mode"] == "prompt_only"
    assert end_job["prompt_composition_mode"] == "zimage_skill_aligned"
    assert end_job["reference_guidance_active"] is False


def test_new_keyframe_jobs_upgrade_guofeng_scenic_umbrella_shot_to_scenic_preset(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260601_231000_guofeng_scenic_override"
    intake_dir = project_dir / "00_intake"
    keyframe_dir = project_dir / "04_keyframes"
    images_dir = project_dir / "05_images"
    intake_dir.mkdir(parents=True, exist_ok=True)
    keyframe_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    brief = load_example_brief()
    brief.update({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-06-01T23:10:00+08:00",
    })
    brief["normalized"]["style"] = "国风水墨/古风"
    brief["normalized"]["final_output"] = "生成关键帧图片素材包"
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    keyframe = json.loads((TEMPLATES / "keyframe_prompts.example.json").read_text(encoding="utf-8"))
    keyframe["project_id"] = project_dir.name
    keyframe["source_brief"] = str(locked_brief).replace("\\", "/")
    keyframe["shot_prompts"] = keyframe["shot_prompts"][:1]
    keyframe["shot_prompts"][0]["camera_prompt"] = "medium scenic shot"
    keyframe["shot_prompts"][0]["start_keyframe_prompt"] = "ancient Chinese woman holding one oil-paper umbrella in misty rain"
    keyframe["shot_prompts"][0]["end_keyframe_prompt"] = "the same woman turns with the same oil-paper umbrella under mist"
    keyframe_json = keyframe_dir / "keyframe_prompts.json"
    keyframe_json.write_text(json.dumps(keyframe, ensure_ascii=False, indent=2), encoding="utf-8")

    manifest_json = images_dir / "keyframe_image_manifest.json"
    assert new_keyframe_image_jobs.main([
        "new_keyframe_image_jobs.py",
        str(locked_brief),
        str(keyframe_json),
        str(manifest_json),
        "--allow-beyond-requested-scope",
    ]) == 0

    data = json.loads(manifest_json.read_text(encoding="utf-8"))
    start_job = next(job for job in data["jobs"] if job["image_id"] == "IMG_S001_START")
    assert start_job["comfyui_style_preset_key"] == "scenic_single_subject_umbrella"
    assert "not a beauty close-up portrait" in start_job["comfyui_style_positive_anchor"]
    assert "beauty close-up portrait" in start_job["comfyui_style_negative_anchor"]


def test_sync_keyframe_image_manifest_blocks_risky_umbrella_scene_until_approved(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260530_umbrella_review_demo"
    intake_dir = project_dir / "00_intake"
    keyframe_dir = project_dir / "04_keyframes"
    images_dir = project_dir / "05_images"
    intake_dir.mkdir(parents=True, exist_ok=True)
    keyframe_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    brief = load_example_brief()
    brief.update({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-30T20:00:00+08:00",
    })
    brief["normalized"]["style"] = "国风水墨/古风"
    brief["normalized"]["final_output"] = "生成关键帧图片素材包"
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    keyframe = json.loads((TEMPLATES / "keyframe_prompts.example.json").read_text(encoding="utf-8"))
    keyframe["project_id"] = project_dir.name
    keyframe["source_brief"] = str(locked_brief).replace("\\", "/")
    keyframe["shot_prompts"] = keyframe["shot_prompts"][:1]
    keyframe["shot_prompts"][0]["start_keyframe_prompt"] = "ancient Chinese woman holding one oil-paper umbrella in misty rain"
    keyframe["shot_prompts"][0]["end_keyframe_prompt"] = "the same woman turns slightly while holding the same oil-paper umbrella"
    keyframe_json = keyframe_dir / "keyframe_prompts.json"
    keyframe_json.write_text(json.dumps(keyframe, ensure_ascii=False, indent=2), encoding="utf-8")

    manifest_json = images_dir / "keyframe_image_manifest.json"
    assert new_keyframe_image_jobs.main(["new_keyframe_image_jobs.py", str(locked_brief), str(keyframe_json), str(manifest_json)]) == 0

    manifest = json.loads(manifest_json.read_text(encoding="utf-8"))
    assert manifest["comfyui_control_mode"] == "prompt_only"
    assert manifest["quality_review"]["manual_review_cleared"] is False
    assert all(job["quality_gate"]["requires_manual_review"] is True for job in manifest["jobs"])
    assert all(job["quality_gate"]["manual_review_status"] == "pending" for job in manifest["jobs"])

    for job in manifest["jobs"]:
        output_path = Path(job["output_path"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"png")
    manifest_json.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    old_argv = sys.argv[:]
    try:
        sys.argv = ["sync_keyframe_image_manifest.py", str(manifest_json)]
        assert sync_keyframe_image_manifest.main() == 0
    finally:
        sys.argv = old_argv

    blocked = json.loads(manifest_json.read_text(encoding="utf-8"))
    assert blocked["self_check"]["all_required_images_exist"] is True
    assert blocked["self_check"]["manual_review_cleared"] is False
    assert blocked["self_check"]["ready_for_video_clip_generation"] is False
    assert blocked["allowed_next_stage"] is None
    assert blocked["quality_review"]["next_review_image_ids"] == ["IMG_S001_START", "IMG_S001_END"]
    assert blocked["quality_review"]["review_queue"][0]["priority_label"] == "高优先级复核"
    assert blocked["jobs"][0]["creator_review_card"]["checklist"]
    manual_review_text = (images_dir / "manual_review.md").read_text(encoding="utf-8")
    assert "# Stage 05 Manual Review" in manual_review_text
    assert "建议先看" in manual_review_text
    assert "Top 3 快速问题卡" in manual_review_text
    assert "IMG_S001_START" in manual_review_text
    assert "复核清单" in manual_review_text
    review_workbench_html = (images_dir / "stage05_review_workbench.html").read_text(encoding="utf-8")
    review_workbench_json = json.loads((images_dir / "stage05_review_workbench.json").read_text(encoding="utf-8"))
    assert "Stage 05 审图工作台" in review_workbench_html
    assert review_workbench_json["cards"][0]["image_id"] == "IMG_S001_START"
    prompt_patch_plan = json.loads((images_dir / "prompt_patch_plan.json").read_text(encoding="utf-8"))
    assert prompt_patch_plan["patch_count"] == 2
    assert prompt_patch_plan["queue_patch_count"] == 2
    assert prompt_patch_plan["top_prompt_patches"][0]["image_id"] == "IMG_S001_START"
    assert "auto_repair_stage05_review_queue.py" in prompt_patch_plan["top_prompt_patches"][0]["rerun_command"]
    prompt_patch_cards = (images_dir / "prompt_patch_cards.md").read_text(encoding="utf-8")
    assert "最短改法" in prompt_patch_cards

    old_argv = sys.argv[:]
    try:
        sys.argv = ["sync_keyframe_image_manifest.py", str(manifest_json), "--approve-risky-jobs"]
        assert sync_keyframe_image_manifest.main() == 0
    finally:
        sys.argv = old_argv

    approved = json.loads(manifest_json.read_text(encoding="utf-8"))
    assert approved["quality_review"]["manual_review_cleared"] is True
    assert approved["self_check"]["manual_review_cleared"] is True
    assert approved["self_check"]["ready_for_video_clip_generation"] is True
    assert approved["allowed_next_stage"] == "STAGE_06_VIDEO_CLIPS"
    assert all(job["quality_gate"]["manual_review_status"] == "approved" for job in approved["jobs"])


def test_rerun_top_prompt_patches_invokes_stage05_runner_in_priority_order(tmp_path: Path, monkeypatch) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260530_prompt_patch_rerun_demo"
    intake_dir = project_dir / "00_intake"
    keyframe_dir = project_dir / "04_keyframes"
    images_dir = project_dir / "05_images"
    intake_dir.mkdir(parents=True, exist_ok=True)
    keyframe_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    brief = load_example_brief()
    brief.update({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-30T20:00:00+08:00",
    })
    brief["normalized"]["style"] = "国风水墨/古风"
    brief["normalized"]["final_output"] = "生成关键帧图片素材包"
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    keyframe = json.loads((TEMPLATES / "keyframe_prompts.example.json").read_text(encoding="utf-8"))
    keyframe["project_id"] = project_dir.name
    keyframe["source_brief"] = str(locked_brief).replace("\\", "/")
    keyframe["shot_prompts"] = keyframe["shot_prompts"][:2]
    keyframe["shot_prompts"][0]["start_keyframe_prompt"] = "ancient Chinese woman holding one oil-paper umbrella in misty rain"
    keyframe["shot_prompts"][0]["end_keyframe_prompt"] = "the same woman turns slightly while holding the same oil-paper umbrella"
    keyframe["shot_prompts"][1]["start_keyframe_prompt"] = "another woman holding one oil-paper umbrella under street rain"
    keyframe["shot_prompts"][1]["end_keyframe_prompt"] = "the same woman keeps holding the same oil-paper umbrella while stepping forward"
    keyframe_json = keyframe_dir / "keyframe_prompts.json"
    keyframe_json.write_text(json.dumps(keyframe, ensure_ascii=False, indent=2), encoding="utf-8")

    manifest_json = images_dir / "keyframe_image_manifest.json"
    assert new_keyframe_image_jobs.main(["new_keyframe_image_jobs.py", str(locked_brief), str(keyframe_json), str(manifest_json)]) == 0
    manifest = json.loads(manifest_json.read_text(encoding="utf-8"))
    for job in manifest["jobs"]:
        job["quality_gate"] = {
            "risk_tags": ["umbrella_prop_contact"],
            "control_mode": "prompt_only",
            "requires_manual_review": True,
            "manual_review_status": "pending",
            "reason": "test prompt patch queue",
        }
    manifest["quality_review"] = {
        "review_queue": [
            {"image_id": "IMG_S001_START", "manual_review_status": "pending"},
            {"image_id": "IMG_S001_END", "manual_review_status": "pending"},
            {"image_id": "IMG_S002_START", "manual_review_status": "pending"},
            {"image_id": "IMG_S002_END", "manual_review_status": "pending"},
        ],
        "top_review_cards": [
            {"image_id": "IMG_S001_START"},
            {"image_id": "IMG_S001_END"},
            {"image_id": "IMG_S002_START"},
        ],
        "manual_review_cleared": False,
    }
    manifest_json.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    prompt_patch_plan = {
        "project_id": project_dir.name,
        "manifest_path": str(manifest_json.resolve()).replace("\\", "/"),
        "generated_at": "2026-05-30T20:05:00+08:00",
        "patch_count": 4,
        "queue_patch_count": 4,
        "top_prompt_patches": [
            {"image_id": "IMG_S001_START"},
            {"image_id": "IMG_S001_END"},
            {"image_id": "IMG_S002_START"},
            {"image_id": "IMG_S002_END"},
        ],
        "all_prompt_patches": [
            {"image_id": "IMG_S001_START"},
            {"image_id": "IMG_S001_END"},
            {"image_id": "IMG_S002_START"},
            {"image_id": "IMG_S002_END"},
        ],
    }
    (images_dir / "prompt_patch_plan.json").write_text(json.dumps(prompt_patch_plan, ensure_ascii=False, indent=2), encoding="utf-8")

    invoked: list[list[str]] = []

    def fake_main(argv: list[str] | None = None) -> int:
        assert argv is not None
        invoked.append(list(argv))
        manifest_data = json.loads(manifest_json.read_text(encoding="utf-8"))
        target_image_id = argv[2]
        for job in manifest_data["jobs"]:
            if job["image_id"] != target_image_id:
                continue
            output_path = Path(job["output_path"])
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(b"png")
            job["status"] = "succeeded"
            break
        manifest_json.write_text(json.dumps(manifest_data, ensure_ascii=False, indent=2), encoding="utf-8")
        return 0

    monkeypatch.setattr(
        rerun_top_prompt_patches,
        "select_stage05_runner",
        lambda data, config_path=None: {
            "provider": "openai_gpt_image2",
            "status": "ready",
            "reason": "test_forced_openai",
            "priority": ["openai_gpt_image2", "comfyui_txt2img", "manual"],
            "probe_results": [],
            "config_path": None,
        },
    )
    monkeypatch.setattr(rerun_top_prompt_patches.run_openai_gpt_image2, "main", fake_main)
    assert rerun_top_prompt_patches.main([str(manifest_json), "--limit", "3", "--allow-beyond-requested-scope"]) == 0

    assert [args[2] for args in invoked] == ["IMG_S001_START", "IMG_S001_END", "IMG_S002_START"]
    assert all("--allow-beyond-requested-scope" in args for args in invoked)
    rerun_report = json.loads((images_dir / "prompt_patch_rerun_report.json").read_text(encoding="utf-8"))
    assert rerun_report["selected_count"] == 3
    assert rerun_report["success_count"] == 3
    assert rerun_report["failure_count"] == 0
    assert rerun_report["selected_provider"] == "openai_gpt_image2"
    assert str(rerun_report["results"][0]["command"]).endswith("--allow-beyond-requested-scope")
    assert rerun_report["remaining_pending_count"] == 4
    assert rerun_report["next_pending_image_ids"][:3] == ["IMG_S001_START", "IMG_S001_END", "IMG_S002_START"]
    rerun_report_md = (images_dir / "prompt_patch_rerun_report.md").read_text(encoding="utf-8")
    assert "# Stage 05 Prompt Patch Rerun Report" in rerun_report_md
    assert "IMG_S001_START" in rerun_report_md

    assert approve_stage05_review_queue.main([str(manifest_json), "--top", "3", "--note", "creator approved after visual review"]) == 1
    assert approve_stage05_review_queue.main([
        str(manifest_json),
        "--top",
        "3",
        "--note",
        "creator approved after visual review",
        "--content-aligned",
        "--content-alignment-note",
        "Reviewed against shot intent and image content matches the prompt package.",
    ]) == 0

    invoked.clear()
    assert rerun_top_prompt_patches.main([str(manifest_json), "--limit", "3", "--dry-run"]) == 0
    assert invoked == []
    rerun_report = json.loads((images_dir / "prompt_patch_rerun_report.json").read_text(encoding="utf-8"))
    assert rerun_report["selected_count"] == 1
    assert rerun_report["results"][0]["image_id"] == "IMG_S002_END"
    assert rerun_report["skipped_manually_cleared_image_ids"] == ["IMG_S001_END", "IMG_S001_START", "IMG_S002_START"]
    assert rerun_report["previously_succeeded_image_ids"] == ["IMG_S001_END", "IMG_S001_START", "IMG_S002_START"]
    assert rerun_report["skipped_previously_succeeded_image_ids"] == []
    assert rerun_report["remaining_pending_count"] == 1
    assert rerun_report["next_pending_image_ids"] == ["IMG_S002_END"]
    approved_manifest = json.loads(manifest_json.read_text(encoding="utf-8"))
    approved_jobs = {
        job["image_id"]: job
        for job in approved_manifest["jobs"]
        if job["image_id"] in {"IMG_S001_START", "IMG_S001_END", "IMG_S002_START"}
    }
    assert all(job["quality_gate"]["manual_review_status"] == "approved" for job in approved_jobs.values())
    assert all(job["quality_gate"]["review_note"] == "creator approved after visual review" for job in approved_jobs.values())
    assert all(job["quality_gate"]["content_text_alignment_confirmed"] is True for job in approved_jobs.values())
    assert all(job["quality_gate"]["content_text_alignment_note"] for job in approved_jobs.values())
    manual_review_text = (images_dir / "manual_review.md").read_text(encoding="utf-8")
    assert "## 看完后的推进" in manual_review_text
    assert "approve_stage05_review_queue.py" in manual_review_text

    final_pending_manifest = json.loads(manifest_json.read_text(encoding="utf-8"))
    for job in final_pending_manifest["jobs"]:
        if job["image_id"] != "IMG_S002_END":
            continue
        output_path = Path(job["output_path"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"png")
        job["status"] = "succeeded"
        break
    manifest_json.write_text(json.dumps(final_pending_manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    assert approve_stage05_review_queue.main([
        str(manifest_json),
        "--all-pending",
        "--content-aligned",
        "--content-alignment-note",
        "Remaining approved images were checked against the prompt description and continuity notes.",
    ]) == 0
    fully_approved_manifest = json.loads(manifest_json.read_text(encoding="utf-8"))
    assert fully_approved_manifest["quality_review"]["manual_review_cleared"] is True
    assert fully_approved_manifest["self_check"]["ready_for_video_clip_generation"] is True
    assert fully_approved_manifest["allowed_next_stage"] == "STAGE_06_VIDEO_CLIPS"


def test_rerun_top_prompt_patches_switches_to_comfyui_when_openai_unavailable(tmp_path: Path, monkeypatch) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260531_stage05_auto_repair_comfy"
    intake_dir = project_dir / "00_intake"
    keyframe_dir = project_dir / "04_keyframes"
    images_dir = project_dir / "05_images"
    intake_dir.mkdir(parents=True, exist_ok=True)
    keyframe_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    brief = load_example_brief()
    brief.update({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-31T11:00:00+08:00",
    })
    brief["normalized"]["final_output"] = "生成关键帧图片素材包"
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    keyframe = json.loads((TEMPLATES / "keyframe_prompts.example.json").read_text(encoding="utf-8"))
    keyframe["project_id"] = project_dir.name
    keyframe["source_brief"] = str(locked_brief).replace("\\", "/")
    keyframe["shot_prompts"] = keyframe["shot_prompts"][:1]
    keyframe["shot_prompts"][0]["start_keyframe_prompt"] = "young woman with one umbrella in rainy storefront"
    keyframe["shot_prompts"][0]["end_keyframe_prompt"] = "same woman keeps one umbrella while leaving storefront"
    keyframe_json = keyframe_dir / "keyframe_prompts.json"
    keyframe_json.write_text(json.dumps(keyframe, ensure_ascii=False, indent=2), encoding="utf-8")

    manifest_json = images_dir / "keyframe_image_manifest.json"
    assert new_keyframe_image_jobs.main(["new_keyframe_image_jobs.py", str(locked_brief), str(keyframe_json), str(manifest_json)]) == 0

    invoked: list[list[str]] = []

    def fake_comfy_main(argv: list[str] | None = None) -> int:
        assert argv is not None
        invoked.append(list(argv))
        manifest_data = json.loads(manifest_json.read_text(encoding="utf-8"))
        image_id = argv[2]
        for job in manifest_data["jobs"]:
            if job["image_id"] != image_id:
                continue
            output_path = Path(job["output_path"])
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(b"png")
            job["status"] = "succeeded"
            job["provider"] = "comfyui_txt2img"
            break
        manifest_json.write_text(json.dumps(manifest_data, ensure_ascii=False, indent=2), encoding="utf-8")
        return 0

    monkeypatch.setattr(
        rerun_top_prompt_patches,
        "select_stage05_runner",
        lambda data, config_path=None: {
            "provider": "comfyui_txt2img",
            "status": "ready",
            "reason": "openai_invalid_api_key",
            "priority": ["openai_gpt_image2", "comfyui_txt2img", "manual"],
            "probe_results": [
                {"provider": "openai_gpt_image2", "status": "invalid_api_key"},
                {"provider": "comfyui_txt2img", "status": "ready"},
            ],
            "config_path": None,
        },
    )
    monkeypatch.setattr(rerun_top_prompt_patches.run_comfyui_txt2img, "main", fake_comfy_main)
    assert rerun_top_prompt_patches.main([str(manifest_json), "--image-id", "IMG_S001_START"]) == 0

    assert invoked and invoked[0][2] == "IMG_S001_START"
    rerun_report = json.loads((images_dir / "prompt_patch_rerun_report.json").read_text(encoding="utf-8"))
    assert rerun_report["selected_provider"] == "comfyui_txt2img"
    assert rerun_report["provider_probe"]["reason"] == "openai_invalid_api_key"
    assert rerun_report["results"][0]["provider"] == "comfyui_txt2img"


def test_stage05_review_workbench_server_serves_state_and_actions(tmp_path: Path, monkeypatch) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260531_stage05_workbench_server"
    intake_dir = project_dir / "00_intake"
    keyframe_dir = project_dir / "04_keyframes"
    images_dir = project_dir / "05_images"
    intake_dir.mkdir(parents=True, exist_ok=True)
    keyframe_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    brief = load_example_brief()
    brief.update({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-31T12:00:00+08:00",
    })
    brief["normalized"]["style"] = "国风水墨/古风"
    brief["normalized"]["final_output"] = "生成关键帧图片素材包"
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    keyframe = json.loads((TEMPLATES / "keyframe_prompts.example.json").read_text(encoding="utf-8"))
    keyframe["project_id"] = project_dir.name
    keyframe["source_brief"] = str(locked_brief).replace("\\", "/")
    keyframe["shot_prompts"] = keyframe["shot_prompts"][:1]
    keyframe["shot_prompts"][0]["start_keyframe_prompt"] = "ancient Chinese woman holding one oil-paper umbrella in misty rain"
    keyframe["shot_prompts"][0]["end_keyframe_prompt"] = "the same woman turns slightly while holding the same oil-paper umbrella"
    keyframe_json = keyframe_dir / "keyframe_prompts.json"
    keyframe_json.write_text(json.dumps(keyframe, ensure_ascii=False, indent=2), encoding="utf-8")

    manifest_json = images_dir / "keyframe_image_manifest.json"
    assert new_keyframe_image_jobs.main(["new_keyframe_image_jobs.py", str(locked_brief), str(keyframe_json), str(manifest_json)]) == 0

    manifest = json.loads(manifest_json.read_text(encoding="utf-8"))
    for job in manifest["jobs"]:
        output_path = Path(job["output_path"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"png")
        job["quality_gate"] = {
            "risk_tags": ["umbrella_prop_contact"],
            "control_mode": "reference_guided",
            "requires_manual_review": True,
            "manual_review_status": "pending",
            "reason": "high-risk shot",
        }
        job["stage06_route_hint"] = "interaction_handoff"
    manifest_json.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    assert sync_keyframe_image_manifest.main([str(manifest_json)]) == 0

    invoked: list[list[str]] = []

    def fake_rerun(argv: list[str] | None = None) -> int:
        assert argv is not None
        invoked.append(list(argv))
        return 0

    monkeypatch.setattr(serve_stage05_review_workbench.rerun_top_prompt_patches, "main", fake_rerun)

    server = serve_stage05_review_workbench.build_server(manifest_json.resolve(), host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address[:2]
        base_url = f"http://{host}:{port}"
        state = json.loads(request.urlopen(f"{base_url}/api/state").read().decode("utf-8"))
        assert state["cards"][0]["image_id"] == "IMG_S001_START"

        html_text = request.urlopen(f"{base_url}/").read().decode("utf-8")
        assert "Stage 05 审图工作台" in html_text
        assert "runWorkbenchAction" in html_text

        image_path = Path(manifest["jobs"][0]["output_path"]).resolve()
        image_bytes = request.urlopen(f"{base_url}/api/file?path={quote(str(image_path))}").read()
        assert image_bytes == b"png"

        approve_request = request.Request(
            f"{base_url}/api/action",
            data=json.dumps({"action": "approve_image", "image_id": "IMG_S001_START"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        approve_payload = json.loads(request.urlopen(approve_request).read().decode("utf-8"))
        assert approve_payload["ok"] is True
        assert approve_payload["state"]["quality_review"]["pending_count"] == 1

        rerun_request = request.Request(
            f"{base_url}/api/action",
            data=json.dumps({"action": "auto_repair_image", "image_id": "IMG_S001_END"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        rerun_payload = json.loads(request.urlopen(rerun_request).read().decode("utf-8"))
        assert rerun_payload["ok"] is True
        assert invoked and "--allow-beyond-requested-scope" in invoked[0]
        assert invoked[0][2] == "IMG_S001_END"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_validate_video_clip_manifest_example_final() -> None:
    data = json.loads((TEMPLATES / "video_clip_manifest.example.json").read_text(encoding="utf-8"))
    ok, errors, warnings = validate_video_clip_manifest.validate(data, TEMPLATES / "video_clip_manifest.example.json", mode="final")
    assert ok, errors


def test_new_video_clip_jobs_passes_draft_then_placeholder_passes_final(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260528_103000_sunset_beach_girl"
    intake_dir = project_dir / "00_intake"
    storyboard_dir = project_dir / "02_storyboard"
    keyframe_dir = project_dir / "04_keyframes"
    images_dir = project_dir / "05_images"
    video_dir = project_dir / "06_video_clips"
    intake_dir.mkdir(parents=True)
    storyboard_dir.mkdir(parents=True)
    keyframe_dir.mkdir(parents=True)
    images_dir.mkdir(parents=True)
    video_dir.mkdir(parents=True)

    brief = load_example_brief()
    brief.update({
        "schema_version": "0.7.0",
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "aspect_ratio": "9:16",
        "resolution": "1080P",
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-28T10:35:00+08:00",
    })
    brief["normalized"]["final_output"] = "生成视频片段素材包"
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    storyboard = json.loads((TEMPLATES / "storyboard.example.json").read_text(encoding="utf-8"))
    storyboard["project_id"] = project_dir.name
    storyboard_json = storyboard_dir / "storyboard.json"
    storyboard_json.write_text(json.dumps(storyboard, ensure_ascii=False, indent=2), encoding="utf-8")

    keyframe = json.loads((TEMPLATES / "keyframe_prompts.example.json").read_text(encoding="utf-8"))
    keyframe["project_id"] = project_dir.name
    keyframe["source_brief"] = str(locked_brief).replace("\\", "/")
    keyframe_json = keyframe_dir / "keyframe_prompts.json"
    keyframe_json.write_text(json.dumps(keyframe, ensure_ascii=False, indent=2), encoding="utf-8")

    image_manifest_json = images_dir / "keyframe_image_manifest.json"
    assert new_keyframe_image_jobs.main(["new_keyframe_image_jobs.py", str(locked_brief), str(keyframe_json), str(image_manifest_json)]) == 0
    old_argv = sys.argv[:]
    try:
        sys.argv = ["generate_placeholder_keyframe_images.py", str(image_manifest_json), "--width", "64", "--height", "96"]
        assert generate_placeholder_keyframe_images.main() == 0
    finally:
        sys.argv = old_argv
    image_manifest = json.loads(image_manifest_json.read_text(encoding="utf-8"))
    image_manifest["status"] = "confirmed"
    image_manifest_json.write_text(json.dumps(image_manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    clip_manifest_json = video_dir / "video_clip_manifest.json"
    assert new_video_clip_jobs.main([
        "new_video_clip_jobs.py", str(locked_brief), str(storyboard_json), str(keyframe_json), str(image_manifest_json), str(clip_manifest_json)
    ]) == 0
    data = json.loads(clip_manifest_json.read_text(encoding="utf-8"))
    ok, errors, warnings = validate_video_clip_manifest.validate(data, clip_manifest_json, mode="draft")
    assert ok, errors
    assert warnings
    assert len(data["jobs"]) == len(keyframe["shot_prompts"])

    ok, errors, warnings = validate_video_clip_manifest.validate(data, clip_manifest_json, mode="final")
    assert not ok
    assert any("status must be succeeded" in e or "clip file does not exist" in e for e in errors)

    old_argv = sys.argv[:]
    try:
        sys.argv = ["generate_placeholder_video_clips.py", str(clip_manifest_json)]
        assert generate_placeholder_video_clips.main() == 0
    finally:
        sys.argv = old_argv
    data = json.loads(clip_manifest_json.read_text(encoding="utf-8"))
    ok, errors, warnings = validate_video_clip_manifest.validate(data, clip_manifest_json, mode="final")
    assert ok, errors


def test_sync_video_clip_manifest_demotes_placeholder_clips_from_ready_state(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260530_placeholder_demote"
    intake_dir = project_dir / "00_intake"
    storyboard_dir = project_dir / "02_storyboard"
    keyframe_dir = project_dir / "04_keyframes"
    images_dir = project_dir / "05_images"
    video_dir = project_dir / "06_video_clips"
    for folder in [intake_dir, storyboard_dir, keyframe_dir, images_dir, video_dir]:
        folder.mkdir(parents=True, exist_ok=True)

    brief = load_example_brief()
    brief.update({
        "schema_version": "0.7.0",
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-30T10:35:00+08:00",
    })
    brief["normalized"]["final_output"] = "生成视频片段素材包"
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    storyboard = json.loads((TEMPLATES / "storyboard.example.json").read_text(encoding="utf-8"))
    storyboard["project_id"] = project_dir.name
    storyboard_json = storyboard_dir / "storyboard.json"
    storyboard_json.write_text(json.dumps(storyboard, ensure_ascii=False, indent=2), encoding="utf-8")

    keyframe = json.loads((TEMPLATES / "keyframe_prompts.example.json").read_text(encoding="utf-8"))
    keyframe["project_id"] = project_dir.name
    keyframe["source_brief"] = str(locked_brief).replace("\\", "/")
    keyframe_json = keyframe_dir / "keyframe_prompts.json"
    keyframe_json.write_text(json.dumps(keyframe, ensure_ascii=False, indent=2), encoding="utf-8")

    image_manifest_json = images_dir / "keyframe_image_manifest.json"
    assert new_keyframe_image_jobs.main(["new_keyframe_image_jobs.py", str(locked_brief), str(keyframe_json), str(image_manifest_json)]) == 0
    old_argv = sys.argv[:]
    try:
        sys.argv = ["generate_placeholder_keyframe_images.py", str(image_manifest_json), "--width", "64", "--height", "96"]
        assert generate_placeholder_keyframe_images.main() == 0
    finally:
        sys.argv = old_argv
    image_manifest = json.loads(image_manifest_json.read_text(encoding="utf-8"))
    image_manifest["status"] = "confirmed"
    image_manifest_json.write_text(json.dumps(image_manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    clip_manifest_json = video_dir / "video_clip_manifest.json"
    assert new_video_clip_jobs.main([
        "new_video_clip_jobs.py", str(locked_brief), str(storyboard_json), str(keyframe_json), str(image_manifest_json), str(clip_manifest_json)
    ]) == 0
    old_argv = sys.argv[:]
    try:
        sys.argv = ["generate_placeholder_video_clips.py", str(clip_manifest_json)]
        assert generate_placeholder_video_clips.main() == 0
    finally:
        sys.argv = old_argv
    old_argv = sys.argv[:]
    try:
        sys.argv = ["sync_video_clip_manifest.py", str(clip_manifest_json)]
        assert sync_video_clip_manifest.main() == 0
    finally:
        sys.argv = old_argv

    data = json.loads(clip_manifest_json.read_text(encoding="utf-8"))
    assert data["status"] == "draft"
    assert data["summary"]["generated_clip_count"] == 0
    assert data["self_check"]["all_required_clips_exist"] is False
    assert data["self_check"]["ready_for_audio_stage"] is False
    assert all(job["status"] == "failed" for job in data["jobs"])
    assert any("non-production clip evidence" in (job.get("notes") or "") for job in data["jobs"])


def test_stage05_placeholder_generation_auto_advances_project_manifest_and_unblocks_stage06(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260529_190842_project"
    intake_dir = project_dir / "00_intake"
    storyboard_dir = project_dir / "02_storyboard"
    keyframe_dir = project_dir / "04_keyframes"
    images_dir = project_dir / "05_images"
    video_dir = project_dir / "06_video_clips"
    for d in [intake_dir, storyboard_dir, keyframe_dir, images_dir, video_dir]:
        d.mkdir(parents=True, exist_ok=True)

    manifest_path = project_dir / "project_manifest.json"
    manifest_path.write_text(json.dumps({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "current_stage": "STAGE_00_BRIEF_LOCKED",
        "brief_locked": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    brief = load_example_brief()
    brief.update({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-29T19:08:42+08:00",
    })
    brief["normalized"]["final_output"] = "生成视频片段素材包"
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    storyboard = json.loads((TEMPLATES / "storyboard.example.json").read_text(encoding="utf-8"))
    storyboard["project_id"] = project_dir.name
    storyboard_json = storyboard_dir / "storyboard.json"
    storyboard_json.write_text(json.dumps(storyboard, ensure_ascii=False, indent=2), encoding="utf-8")

    keyframe = json.loads((TEMPLATES / "keyframe_prompts.example.json").read_text(encoding="utf-8"))
    keyframe["project_id"] = project_dir.name
    keyframe["source_brief"] = str(locked_brief).replace("\\", "/")
    keyframe_json = keyframe_dir / "keyframe_prompts.json"
    keyframe_json.write_text(json.dumps(keyframe, ensure_ascii=False, indent=2), encoding="utf-8")

    image_manifest_json = images_dir / "keyframe_image_manifest.json"
    assert new_keyframe_image_jobs.main(["new_keyframe_image_jobs.py", str(locked_brief), str(keyframe_json), str(image_manifest_json)]) == 0

    old_argv = sys.argv[:]
    try:
        sys.argv = ["generate_placeholder_keyframe_images.py", str(image_manifest_json), "--width", "64", "--height", "96"]
        assert generate_placeholder_keyframe_images.main() == 0
    finally:
        sys.argv = old_argv

    image_manifest = json.loads(image_manifest_json.read_text(encoding="utf-8"))
    project_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert image_manifest["status"] == "generated"
    assert image_manifest["allowed_next_stage"] == "STAGE_06_VIDEO_CLIPS"
    assert project_manifest["current_stage"] == "STAGE_05_KEYFRAME_IMAGES_CONFIRMED"
    assert project_manifest["keyframe_images_confirmed"] is True
    assert project_manifest["allowed_next_stage"] == "STAGE_06_VIDEO_CLIPS"

    clip_manifest_json = video_dir / "video_clip_manifest.json"
    assert new_video_clip_jobs.main([
        "new_video_clip_jobs.py",
        str(locked_brief),
        str(storyboard_json),
        str(keyframe_json),
        str(image_manifest_json),
        str(clip_manifest_json),
    ]) == 0


def test_new_video_clip_jobs_blocks_when_requested_scope_stops_at_keyframe_prompts(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260529_190842_project"
    intake_dir = project_dir / "00_intake"
    storyboard_dir = project_dir / "02_storyboard"
    keyframe_dir = project_dir / "04_keyframes"
    images_dir = project_dir / "05_images"
    video_dir = project_dir / "06_video_clips"
    for d in [intake_dir, storyboard_dir, keyframe_dir, images_dir, video_dir]:
        d.mkdir(parents=True, exist_ok=True)

    brief = load_example_brief()
    brief.update({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-29T19:08:42+08:00",
    })
    brief["normalized"]["final_output"] = "剧本 + 分镜 + 关键帧提示词"
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    storyboard = json.loads((TEMPLATES / "storyboard.example.json").read_text(encoding="utf-8"))
    storyboard["project_id"] = project_dir.name
    storyboard_json = storyboard_dir / "storyboard.json"
    storyboard_json.write_text(json.dumps(storyboard, ensure_ascii=False, indent=2), encoding="utf-8")

    keyframe = json.loads((TEMPLATES / "keyframe_prompts.example.json").read_text(encoding="utf-8"))
    keyframe["project_id"] = project_dir.name
    keyframe["source_brief"] = str(locked_brief).replace("\\", "/")
    keyframe_json = keyframe_dir / "keyframe_prompts.json"
    keyframe_json.write_text(json.dumps(keyframe, ensure_ascii=False, indent=2), encoding="utf-8")

    image_manifest_json = images_dir / "keyframe_image_manifest.json"
    assert new_keyframe_image_jobs.main(["new_keyframe_image_jobs.py", str(locked_brief), str(keyframe_json), str(image_manifest_json), "--allow-beyond-requested-scope"]) == 0
    old_argv = sys.argv[:]
    try:
        sys.argv = ["generate_placeholder_keyframe_images.py", str(image_manifest_json), "--width", "64", "--height", "96"]
        assert generate_placeholder_keyframe_images.main() == 0
    finally:
        sys.argv = old_argv

    clip_manifest_json = video_dir / "video_clip_manifest.json"
    assert new_video_clip_jobs.main([
        "new_video_clip_jobs.py",
        str(locked_brief),
        str(storyboard_json),
        str(keyframe_json),
        str(image_manifest_json),
        str(clip_manifest_json),
    ]) == 1
    assert new_video_clip_jobs.main([
        "new_video_clip_jobs.py",
        str(locked_brief),
        str(storyboard_json),
        str(keyframe_json),
        str(image_manifest_json),
        str(clip_manifest_json),
        "--allow-beyond-requested-scope",
    ]) == 0



def test_validate_audio_manifest_example_final() -> None:
    data = json.loads((TEMPLATES / "audio_manifest.example.json").read_text(encoding="utf-8"))
    ok, errors, warnings = validate_audio_manifest.validate(data, TEMPLATES / "audio_manifest.example.json", mode="final")
    assert ok, errors


def test_new_audio_jobs_passes_draft_then_placeholder_passes_final(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260528_103000_sunset_beach_girl"
    intake_dir = project_dir / "00_intake"
    script_dir = project_dir / "01_script"
    storyboard_dir = project_dir / "02_storyboard"
    character_dir = project_dir / "03_characters"
    keyframe_dir = project_dir / "04_keyframes"
    images_dir = project_dir / "05_images"
    video_dir = project_dir / "06_video_clips"
    audio_dir = project_dir / "07_audio"
    for d in [intake_dir, script_dir, storyboard_dir, character_dir, keyframe_dir, images_dir, video_dir, audio_dir]:
        d.mkdir(parents=True, exist_ok=True)

    brief = load_example_brief()
    brief.update({
        "schema_version": "0.8.0",
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-28T10:35:00+08:00",
    })
    brief["normalized"]["final_output"] = "合成粗剪成片"
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    script = json.loads((TEMPLATES / "script.example.json").read_text(encoding="utf-8"))
    script["project_id"] = project_dir.name
    script_json = script_dir / "script.json"
    script_json.write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")

    storyboard = json.loads((TEMPLATES / "storyboard.example.json").read_text(encoding="utf-8"))
    storyboard["project_id"] = project_dir.name
    storyboard_json = storyboard_dir / "storyboard.json"
    storyboard_json.write_text(json.dumps(storyboard, ensure_ascii=False, indent=2), encoding="utf-8")

    character = json.loads((TEMPLATES / "character_bible.example.json").read_text(encoding="utf-8"))
    character["project_id"] = project_dir.name
    character_json = character_dir / "character_bible.json"
    character_json.write_text(json.dumps(character, ensure_ascii=False, indent=2), encoding="utf-8")

    keyframe = json.loads((TEMPLATES / "keyframe_prompts.example.json").read_text(encoding="utf-8"))
    keyframe["project_id"] = project_dir.name
    keyframe_json = keyframe_dir / "keyframe_prompts.json"
    keyframe_json.write_text(json.dumps(keyframe, ensure_ascii=False, indent=2), encoding="utf-8")

    image_manifest_json = images_dir / "keyframe_image_manifest.json"
    assert new_keyframe_image_jobs.main(["new_keyframe_image_jobs.py", str(locked_brief), str(keyframe_json), str(image_manifest_json)]) == 0
    old_argv = sys.argv[:]
    try:
        sys.argv = ["generate_placeholder_keyframe_images.py", str(image_manifest_json), "--width", "64", "--height", "96"]
        assert generate_placeholder_keyframe_images.main() == 0
    finally:
        sys.argv = old_argv
    image_manifest = json.loads(image_manifest_json.read_text(encoding="utf-8"))
    image_manifest["status"] = "confirmed"
    image_manifest_json.write_text(json.dumps(image_manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    clip_manifest_json = video_dir / "video_clip_manifest.json"
    assert new_video_clip_jobs.main(["new_video_clip_jobs.py", str(locked_brief), str(storyboard_json), str(keyframe_json), str(image_manifest_json), str(clip_manifest_json)]) == 0
    old_argv = sys.argv[:]
    try:
        sys.argv = ["generate_placeholder_video_clips.py", str(clip_manifest_json)]
        assert generate_placeholder_video_clips.main() == 0
    finally:
        sys.argv = old_argv
    clip_manifest = json.loads(clip_manifest_json.read_text(encoding="utf-8"))
    clip_manifest["status"] = "confirmed"
    clip_manifest_json.write_text(json.dumps(clip_manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    audio_manifest_json = audio_dir / "audio_manifest.json"
    assert new_audio_jobs.main([
        "new_audio_jobs.py", str(locked_brief), str(script_json), str(storyboard_json), str(character_json), str(clip_manifest_json), str(audio_manifest_json)
    ]) == 0
    data = json.loads(audio_manifest_json.read_text(encoding="utf-8"))
    ok, errors, warnings = validate_audio_manifest.validate(data, audio_manifest_json, mode="draft")
    assert ok, errors
    assert warnings
    assert data["summary"]["expected_voice_count"] > 0
    assert data["summary"]["expected_music_count"] == 1

    ok, errors, warnings = validate_audio_manifest.validate(data, audio_manifest_json, mode="final")
    assert not ok
    assert any("status must be succeeded" in e or "audio file does not exist" in e for e in errors)

    old_argv = sys.argv[:]
    try:
        sys.argv = ["generate_placeholder_audio.py", str(audio_manifest_json)]
        assert generate_placeholder_audio.main() == 0
    finally:
        sys.argv = old_argv
    data = json.loads(audio_manifest_json.read_text(encoding="utf-8"))
    ok, errors, warnings = validate_audio_manifest.validate(data, audio_manifest_json, mode="final")
    assert ok, errors



def test_validate_assembly_manifest_example_final() -> None:
    data = json.loads((TEMPLATES / "assembly_manifest.example.json").read_text(encoding="utf-8"))
    ok, errors, warnings = validate_assembly_manifest.validate(data, TEMPLATES / "assembly_manifest.example.json", mode="final")
    assert ok, errors


def test_new_assembly_manifest_passes_draft_then_placeholder_is_blocked_from_final(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260528_103000_sunset_beach_girl"
    intake_dir = project_dir / "00_intake"
    storyboard_dir = project_dir / "02_storyboard"
    keyframe_dir = project_dir / "04_keyframes"
    images_dir = project_dir / "05_images"
    video_dir = project_dir / "06_video_clips"
    audio_dir = project_dir / "07_audio"
    assembly_dir = project_dir / "08_assembly"
    for d in [intake_dir, storyboard_dir, keyframe_dir, images_dir, video_dir, audio_dir, assembly_dir]:
        d.mkdir(parents=True, exist_ok=True)

    brief = load_example_brief()
    brief.update({
        "schema_version": "0.9.0",
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-28T10:35:00+08:00",
    })
    brief["normalized"]["final_output"] = "合成粗剪成片"
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    storyboard = json.loads((TEMPLATES / "storyboard.example.json").read_text(encoding="utf-8"))
    storyboard["project_id"] = project_dir.name
    storyboard_json = storyboard_dir / "storyboard.json"
    storyboard_json.write_text(json.dumps(storyboard, ensure_ascii=False, indent=2), encoding="utf-8")

    keyframe = json.loads((TEMPLATES / "keyframe_prompts.example.json").read_text(encoding="utf-8"))
    keyframe["project_id"] = project_dir.name
    keyframe_json = keyframe_dir / "keyframe_prompts.json"
    keyframe_json.write_text(json.dumps(keyframe, ensure_ascii=False, indent=2), encoding="utf-8")

    image_manifest_json = images_dir / "keyframe_image_manifest.json"
    assert new_keyframe_image_jobs.main(["new_keyframe_image_jobs.py", str(locked_brief), str(keyframe_json), str(image_manifest_json)]) == 0
    old_argv = sys.argv[:]
    try:
        sys.argv = ["generate_placeholder_keyframe_images.py", str(image_manifest_json), "--width", "64", "--height", "96"]
        assert generate_placeholder_keyframe_images.main() == 0
    finally:
        sys.argv = old_argv
    image_manifest = json.loads(image_manifest_json.read_text(encoding="utf-8"))
    image_manifest["status"] = "confirmed"
    image_manifest_json.write_text(json.dumps(image_manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    clip_manifest_json = video_dir / "video_clip_manifest.json"
    assert new_video_clip_jobs.main(["new_video_clip_jobs.py", str(locked_brief), str(storyboard_json), str(keyframe_json), str(image_manifest_json), str(clip_manifest_json)]) == 0
    old_argv = sys.argv[:]
    try:
        sys.argv = ["generate_placeholder_video_clips.py", str(clip_manifest_json)]
        assert generate_placeholder_video_clips.main() == 0
    finally:
        sys.argv = old_argv
    clip_manifest = json.loads(clip_manifest_json.read_text(encoding="utf-8"))
    clip_manifest["status"] = "confirmed"
    clip_manifest_json.write_text(json.dumps(clip_manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    # Build a minimal script/character file only because Stage 07 scaffolder requires them.
    script_dir = project_dir / "01_script"
    character_dir = project_dir / "03_characters"
    script_dir.mkdir(parents=True, exist_ok=True)
    character_dir.mkdir(parents=True, exist_ok=True)
    script = json.loads((TEMPLATES / "script.example.json").read_text(encoding="utf-8"))
    script["project_id"] = project_dir.name
    script_json = script_dir / "script.json"
    script_json.write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")
    character = json.loads((TEMPLATES / "character_bible.example.json").read_text(encoding="utf-8"))
    character["project_id"] = project_dir.name
    character_json = character_dir / "character_bible.json"
    character_json.write_text(json.dumps(character, ensure_ascii=False, indent=2), encoding="utf-8")

    audio_manifest_json = audio_dir / "audio_manifest.json"
    assert new_audio_jobs.main(["new_audio_jobs.py", str(locked_brief), str(script_json), str(storyboard_json), str(character_json), str(clip_manifest_json), str(audio_manifest_json)]) == 0
    old_argv = sys.argv[:]
    try:
        sys.argv = ["generate_placeholder_audio.py", str(audio_manifest_json)]
        assert generate_placeholder_audio.main() == 0
    finally:
        sys.argv = old_argv
    audio_manifest = json.loads(audio_manifest_json.read_text(encoding="utf-8"))
    audio_manifest["status"] = "confirmed"
    audio_manifest_json.write_text(json.dumps(audio_manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    assembly_manifest_json = assembly_dir / "assembly_manifest.json"
    assert new_assembly_manifest.main(["new_assembly_manifest.py", str(locked_brief), str(storyboard_json), str(clip_manifest_json), str(audio_manifest_json), str(assembly_manifest_json)]) == 0
    data = json.loads(assembly_manifest_json.read_text(encoding="utf-8"))
    ok, errors, warnings = validate_assembly_manifest.validate(data, assembly_manifest_json, mode="draft")
    assert ok, errors
    assert warnings

    ok, errors, warnings = validate_assembly_manifest.validate(data, assembly_manifest_json, mode="final")
    assert not ok
    assert any("final output file does not exist" in e or "final output file is empty" in e for e in errors)

    old_argv = sys.argv[:]
    try:
        sys.argv = ["assemble_with_ffmpeg.py", str(assembly_manifest_json), "--placeholder-test"]
        assert assemble_with_ffmpeg.main() == 0
    finally:
        sys.argv = old_argv
    data = json.loads(assembly_manifest_json.read_text(encoding="utf-8"))
    ok, errors, warnings = validate_assembly_manifest.validate(data, assembly_manifest_json, mode="final")
    assert not ok
    assert any("placeholder" in e or "too small" in e for e in errors)



def test_validate_qa_manifest_example_final() -> None:
    data = json.loads((TEMPLATES / "qa_manifest.example.json").read_text(encoding="utf-8"))
    ok, errors, warnings = validate_qa_manifest.validate(data, TEMPLATES / "qa_manifest.example.json", mode="final")
    assert ok, errors


def test_new_qa_manifest_passes_draft_then_package_delivery_passes_final(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260528_103000_sunset_beach_girl"
    intake_dir = project_dir / "00_intake"
    assembly_dir = project_dir / "08_assembly"
    qa_dir = project_dir / "09_qa"
    intake_dir.mkdir(parents=True, exist_ok=True)
    assembly_dir.mkdir(parents=True, exist_ok=True)
    qa_dir.mkdir(parents=True, exist_ok=True)

    brief = load_example_brief()
    brief.update({
        "schema_version": "1.0.0",
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-28T10:35:00+08:00",
    })
    brief["normalized"]["final_output"] = "输出完整素材工程包，方便人工剪辑"
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest_path = project_dir / "project_manifest.json"
    manifest_path.write_text(json.dumps({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "current_stage": "STAGE_08_ASSEMBLY_CONFIRMED",
        "assembly_confirmed": True,
        "allowed_next_stage": "STAGE_09_QA",
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    # Create a minimal Stage 08 assembly manifest with real rough_cut evidence.
    rough_cut = assembly_dir / "rough_cut" / "rough_cut.mp4"
    rough_cut.parent.mkdir(parents=True, exist_ok=True)
    rough_cut.write_bytes(b"\x00\x00\x00\x18ftypmp42QA" + (b"1" * 140))
    assembly_manifest = {
        "schema_version": "0.9.0",
        "stage": "STAGE_08_ASSEMBLY",
        "status": "generated",
        "project_id": project_dir.name,
        "source_brief": str(locked_brief).replace("\\", "/"),
        "source_storyboard": "",
        "source_video_clip_manifest": "",
        "source_audio_manifest": "",
        "assembly_provider_strategy": {"primary": "placeholder"},
        "output_root": str(assembly_dir).replace("\\", "/"),
        "rough_cut_dir": str(rough_cut.parent).replace("\\", "/"),
        "temp_dir": str((assembly_dir / "temp")).replace("\\", "/"),
        "concat_list_path": str((assembly_dir / "ffmpeg_concat_list.txt")).replace("\\", "/"),
        "edit_decision_list_path": str((assembly_dir / "edit_decision_list.json")).replace("\\", "/"),
        "audio_mix_plan_path": str((assembly_dir / "audio_mix_plan.json")).replace("\\", "/"),
        "subtitle_path": str((assembly_dir / "subtitles.srt")).replace("\\", "/"),
        "final_output_path": str(rough_cut).replace("\\", "/"),
        "timeline": [{"shot_id": "S001", "clip_path": str(rough_cut).replace("\\", "/"), "start_sec": 0, "duration_sec": 5, "source_clip_id": "CLIP_S001"}],
        "audio_tracks": [],
        "subtitle_tracks": [],
        "ffmpeg_commands": [{
            "command": ["ffmpeg"],
            "provider": "ffmpeg",
            "strategy": "reencode_mix",
            "return_code": 0,
            "stdout_excerpt": "",
            "stderr_excerpt": "",
            "ran_at": "2026-05-28T10:40:00+08:00",
        }],
        "assembly_provider": "ffmpeg",
        "evidence": {"file_path": str(rough_cut).replace("\\", "/"), "file_exists": True, "file_size_bytes": rough_cut.stat().st_size, "created_at": "2026-05-28T10:40:00+08:00"},
        "summary": {"timeline_clip_count": 1, "audio_track_count": 0, "rough_cut_duration_sec": 5},
        "self_check": {"has_timeline_from_confirmed_clips": True, "has_audio_mix_plan": True, "has_edit_decision_list": True, "has_final_output_file": True, "ready_for_qa_stage": True},
        "allowed_next_stage": "STAGE_09_QA",
        "errors": [],
    }
    assembly_manifest_json = assembly_dir / "assembly_manifest.json"
    assembly_manifest_json.write_text(json.dumps(assembly_manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    qa_manifest_json = qa_dir / "qa_manifest.json"
    assert new_qa_manifest.main(["new_qa_manifest.py", str(locked_brief), str(assembly_manifest_json), str(qa_manifest_json)]) == 0
    data = json.loads(qa_manifest_json.read_text(encoding="utf-8"))
    check_ids = {item["check_id"] for item in data["qa_checks"]}
    assert {"intent_alignment", "visual_continuity_contract", "performance_direction_contract", "audio_direction_contract", "format_fit_contract"}.issubset(check_ids)
    ok, errors, warnings = validate_qa_manifest.validate(data, qa_manifest_json, mode="draft")
    assert ok, errors
    assert warnings

    ok, errors, warnings = validate_qa_manifest.validate(data, qa_manifest_json, mode="final")
    assert not ok
    assert any("qa_checks" in e or "delivery_package" in e for e in errors)

    assert package_delivery.main(["package_delivery.py", str(qa_manifest_json)]) == 1
    assert package_delivery.main([
        "package_delivery.py",
        str(qa_manifest_json),
        "--content-aligned",
        "--content-alignment-note",
        "QA reviewer confirmed the delivered rough cut matches the script, storyboard, and prompt intent.",
    ]) == 0
    data = json.loads(qa_manifest_json.read_text(encoding="utf-8"))
    check_status = {item["check_id"]: item["status"] for item in data["qa_checks"]}
    assert check_status["intent_alignment"] == "pass"
    assert check_status["content_text_alignment"] == "pass"
    assert check_status["visual_continuity_contract"] in {"pass", "waived"}
    ok, errors, warnings = validate_qa_manifest.validate(data, qa_manifest_json, mode="final")
    assert ok, errors
    assert data["content_alignment_review"]["confirmed"] is True
    assert data["content_alignment_review"]["status"] == "pass"
    project_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert project_manifest["current_stage"] == "STAGE_09_QA_CONFIRMED"
    assert project_manifest["qa_confirmed"] is True
    assert project_manifest["delivery_complete"] is True
    assert project_manifest["allowed_next_stage"] == "PROJECT_DELIVERED"


def test_package_delivery_blocks_when_requested_scope_stops_at_rough_cut(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260528_103000_scope_blocked_qa"
    intake_dir = project_dir / "00_intake"
    assembly_dir = project_dir / "08_assembly"
    qa_dir = project_dir / "09_qa"
    intake_dir.mkdir(parents=True, exist_ok=True)
    assembly_dir.mkdir(parents=True, exist_ok=True)
    qa_dir.mkdir(parents=True, exist_ok=True)

    brief = load_example_brief()
    brief.update({
        "schema_version": "1.0.0",
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-28T10:35:00+08:00",
    })
    brief["normalized"]["final_output"] = "合成粗剪成片"
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    rough_cut = assembly_dir / "rough_cut" / "rough_cut.mp4"
    rough_cut.parent.mkdir(parents=True, exist_ok=True)
    rough_cut.write_bytes(b"\x00\x00\x00\x18ftypmp42QB" + (b"2" * 140))
    assembly_manifest = {
        "schema_version": "0.9.0",
        "stage": "STAGE_08_ASSEMBLY",
        "status": "generated",
        "project_id": project_dir.name,
        "source_brief": str(locked_brief).replace("\\", "/"),
        "source_storyboard": "",
        "source_video_clip_manifest": "",
        "source_audio_manifest": "",
        "assembly_provider_strategy": {"primary": "placeholder"},
        "output_root": str(assembly_dir).replace("\\", "/"),
        "rough_cut_dir": str(rough_cut.parent).replace("\\", "/"),
        "temp_dir": str((assembly_dir / "temp")).replace("\\", "/"),
        "concat_list_path": str((assembly_dir / "ffmpeg_concat_list.txt")).replace("\\", "/"),
        "edit_decision_list_path": str((assembly_dir / "edit_decision_list.json")).replace("\\", "/"),
        "audio_mix_plan_path": str((assembly_dir / "audio_mix_plan.json")).replace("\\", "/"),
        "subtitle_path": str((assembly_dir / "subtitles.srt")).replace("\\", "/"),
        "final_output_path": str(rough_cut).replace("\\", "/"),
        "timeline": [{"shot_id": "S001", "clip_path": str(rough_cut).replace("\\", "/"), "start_sec": 0, "duration_sec": 5, "source_clip_id": "CLIP_S001"}],
        "audio_tracks": [],
        "subtitle_tracks": [],
        "ffmpeg_commands": [{
            "command": ["ffmpeg"],
            "provider": "ffmpeg",
            "strategy": "reencode_mix",
            "return_code": 0,
            "stdout_excerpt": "",
            "stderr_excerpt": "",
            "ran_at": "2026-05-28T10:40:00+08:00",
        }],
        "assembly_provider": "ffmpeg",
        "evidence": {"file_path": str(rough_cut).replace("\\", "/"), "file_exists": True, "file_size_bytes": rough_cut.stat().st_size, "created_at": "2026-05-28T10:40:00+08:00"},
        "summary": {"timeline_clip_count": 1, "audio_track_count": 0, "rough_cut_duration_sec": 5},
        "self_check": {"has_timeline_from_confirmed_clips": True, "has_audio_mix_plan": True, "has_edit_decision_list": True, "has_final_output_file": True, "ready_for_qa_stage": True},
        "allowed_next_stage": "STAGE_09_QA",
        "errors": [],
    }
    assembly_manifest_json = assembly_dir / "assembly_manifest.json"
    assembly_manifest_json.write_text(json.dumps(assembly_manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    qa_manifest_json = qa_dir / "qa_manifest.json"
    assert new_qa_manifest.main([
        "new_qa_manifest.py",
        str(locked_brief),
        str(assembly_manifest_json),
        str(qa_manifest_json),
        "--allow-beyond-requested-scope",
    ]) == 0

    assert package_delivery.main(["package_delivery.py", str(qa_manifest_json)]) == 1
    assert package_delivery.main([
        "package_delivery.py",
        str(qa_manifest_json),
        "--allow-beyond-requested-scope",
        "--content-aligned",
        "--content-alignment-note",
        "Scope override run also includes manual confirmation that content matches the text description.",
    ]) == 0


def test_new_video_clip_jobs_ignores_template_leaked_story_anchors(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "creator_trial_20260530_rainy_store"
    intake_dir = project_dir / "00_intake"
    storyboard_dir = project_dir / "02_storyboard"
    keyframe_dir = project_dir / "04_keyframes"
    image_dir = project_dir / "05_images"
    clip_dir = project_dir / "06_video_clips"
    intake_dir.mkdir(parents=True, exist_ok=True)
    storyboard_dir.mkdir(parents=True, exist_ok=True)
    keyframe_dir.mkdir(parents=True, exist_ok=True)
    image_dir.mkdir(parents=True, exist_ok=True)
    clip_dir.mkdir(parents=True, exist_ok=True)

    brief = load_rainy_store_brief(project_dir)
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    storyboard = {
        "stage": "STAGE_02_STORYBOARD_GENERATION",
        "project_id": project_dir.name,
        "shots": [{
            "shot_id": "S001",
            "duration_sec": 4,
            "scene": "雨夜便利店门口",
            "location": "便利店门口",
            "weather": "雨夜",
            "key_prop": "最后一把伞",
            "action": "20岁出头的女孩把最后一把伞留给陌生人",
            "emotion": "克制善意",
        }],
        "story_anchors": {
            "subject": "海边女孩",
            "location": "核心场景",
            "weather": "雨夜",
            "scene_label": "核心场景",
            "key_props": ["最后一把伞", "热可可"],
            "action_beats": ["动作与情绪逐步变化"],
            "emotion_beats": ["克制善意"],
            "composition_beats": ["进入故事空间"],
        },
    }
    storyboard_json = storyboard_dir / "storyboard.json"
    storyboard_json.write_text(json.dumps(storyboard, ensure_ascii=False, indent=2), encoding="utf-8")

    prompts = {
        "stage": "STAGE_04_KEYFRAME_PROMPTS",
        "project_id": project_dir.name,
        "shot_prompts": [{
            "shot_id": "S001",
            "duration_sec": 4,
            "motion_prompt": "",
            "performance_prompt": "",
            "dialogue_delivery_prompt": "",
            "consistency_prompt": "",
            "negative_prompt": "多手，额外人物",
        }],
        "global_negative_prompt": "多手，额外人物",
    }
    prompts_json = keyframe_dir / "keyframe_prompts.json"
    prompts_json.write_text(json.dumps(prompts, ensure_ascii=False, indent=2), encoding="utf-8")

    start_image = image_dir / "S001_start.png"
    end_image = image_dir / "S001_end.png"
    start_image.write_bytes(b"png-start")
    end_image.write_bytes(b"png-end")
    image_manifest = {
        "stage": "STAGE_05_KEYFRAME_IMAGES",
        "status": "generated",
        "project_id": project_dir.name,
        "jobs": [
            {"image_id": "IMG_S001_START", "shot_id": "S001", "frame_role": "start", "output_path": str(start_image).replace("\\", "/"), "evidence": {"file_path": str(start_image).replace("\\", "/")}},
            {"image_id": "IMG_S001_END", "shot_id": "S001", "frame_role": "end", "output_path": str(end_image).replace("\\", "/"), "evidence": {"file_path": str(end_image).replace("\\", "/")}},
        ],
    }
    image_manifest_json = image_dir / "keyframe_image_manifest.json"
    image_manifest_json.write_text(json.dumps(image_manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    clip_manifest_json = clip_dir / "video_clip_manifest.json"
    assert new_video_clip_jobs.main([
        "new_video_clip_jobs.py",
        str(locked_brief),
        str(storyboard_json),
        str(prompts_json),
        str(image_manifest_json),
        str(clip_manifest_json),
    ]) == 0

    data = json.loads(clip_manifest_json.read_text(encoding="utf-8"))
    assert data["story_anchors"]["subject"] == "20岁出头的女孩"
    assert data["story_anchors"]["scene_label"] == "雨夜便利店门口"
    assert "海边女孩" not in data["jobs"][0]["consistency_prompt"]
    assert "核心场景" not in data["jobs"][0]["consistency_prompt"]
    assert "20岁出头的女孩" in data["jobs"][0]["consistency_prompt"]
    assert "雨夜便利店门口" in data["jobs"][0]["consistency_prompt"]
    assert "gentle camera movement" not in data["jobs"][0]["motion_prompt"]
    assert "可见的身体位移" in data["jobs"][0]["motion_prompt"]
    assert "最后一把伞" in data["jobs"][0]["motion_prompt"]
