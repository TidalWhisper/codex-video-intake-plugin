#!/usr/bin/env python3
from __future__ import annotations

import importlib
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
INTAKE = ROOT / "skills" / "video-project-intake" / "scripts"
PIPELINE = ROOT / "skills" / "video-production-pipeline" / "scripts"
SCRIPT = ROOT / "skills" / "video-script-generation" / "scripts"
sys.path.insert(0, str(ROOT / "scripts"))


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


build_stage00_intake_prompt_packet = load_module(
    "build_stage00_intake_prompt_packet_for_test",
    INTAKE / "build_stage00_intake_prompt_packet.py",
)
build_stage00_brief_prompt_packet = load_module(
    "build_stage00_brief_prompt_packet_for_test",
    INTAKE / "build_stage00_brief_prompt_packet.py",
)
validate_stage00_intake_state = load_module(
    "validate_stage00_intake_state_for_test",
    INTAKE / "validate_stage00_intake_state.py",
)
write_stage00_intake_state = load_module(
    "write_stage00_intake_state_for_test",
    INTAKE / "write_stage00_intake_state.py",
)
run_stage00_intake_turn_codex_flow = load_module(
    "run_stage00_intake_turn_codex_flow_for_test",
    INTAKE / "run_stage00_intake_turn_codex_flow.py",
)
write_stage00_brief_outputs = load_module(
    "write_stage00_brief_outputs_for_test",
    INTAKE / "write_stage00_brief_outputs.py",
)
run_stage00_brief_codex_flow = load_module(
    "run_stage00_brief_codex_flow_for_test",
    INTAKE / "run_stage00_brief_codex_flow.py",
)
run_stage00_intake_turn_wrapper = load_module(
    "run_stage00_intake_turn_wrapper_for_test",
    PIPELINE / "run_stage00_intake_turn.py",
)
run_stage00_brief_from_intake = load_module(
    "run_stage00_brief_from_intake_for_test",
    PIPELINE / "run_stage00_brief_from_intake.py",
)
run_stage00_controller = load_module(
    "run_stage00_controller_for_test",
    PIPELINE / "run_stage00_controller.py",
)
continue_pipeline = load_module(
    "continue_pipeline_stage00_for_test",
    PIPELINE / "continue_pipeline.py",
)
validate_project_brief = load_module(
    "validate_project_brief_stage00_for_test",
    INTAKE / "validate_project_brief.py",
)
create_project_folder = load_module(
    "create_project_folder_stage00_for_test",
    INTAKE / "create_project_folder.py",
)
new_script_template = load_module(
    "new_script_template_stage00_for_test",
    SCRIPT / "new_script_template.py",
)
stage01_local_semantics = load_module(
    "stage01_local_semantics_stage00_for_test",
    SCRIPT / "stage01_local_semantics.py",
)
stage01_stage_tests = load_module(
    "stage00_stage01_shared_helpers_for_test",
    ROOT / "tests" / "test_stage00_stage01.py",
)
stage00_intake_common = load_module(
    "stage00_intake_common_for_test",
    INTAKE / "stage00_intake_common.py",
)
project_state = importlib.import_module("pipeline_core.project_state")


class _FakeCompletedProcess:
    def __init__(self, returncode: int = 0) -> None:
        self.returncode = returncode
        self.stdout = ""
        self.stderr = ""


def make_stage00_turn_output_for_idea() -> dict:
    return {
        "answered_question_key": "idea",
        "user_answer_entry": {
            "raw_input": "一位年轻的女性穿着裙子，在黄昏的海滩上散步、放空自己。",
            "selected_option": "",
            "free_text_notes": "氛围短片，独自散步，黄昏海滩",
        },
        "user_answers_patch": {
            "idea": "一位年轻的女性穿着裙子，在黄昏的海滩上散步、放空自己。"
        },
        "normalized_patch": {
            "idea": "一位年轻的女性穿着裙子，在黄昏的海滩上散步、放空自己。"
        },
        "missing_required_fields": [
            "target_duration",
            "genre",
            "style",
            "visual_spec",
            "characters",
            "voice",
            "music",
            "final_output"
        ],
        "required_fields_complete": False,
        "status": "collecting",
        "next_question_key": "target_duration",
        "next_prompt_text": stage00_intake_common.canonical_question_block("target_duration"),
        "needs_followup": False,
        "followup_reason": "",
        "completion_summary": "故事想法已记录，继续询问目标时长。"
    }


def make_stage00_draft_ready_state(state_path: Path) -> dict:
    project_dir = state_path.parent.parent
    return {
        "schema_version": "0.4.0",
        "stage": "STAGE_00_INTAKE",
        "status": "draft_ready",
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "current_question": 9,
        "current_question_key": "final_output",
        "answers": {
            "idea": {"raw_input": "一位年轻的女性穿着裙子，在黄昏的海滩上散步、放空自己。"},
            "target_duration": {"raw_input": "B"},
            "genre": {"raw_input": "G"},
            "style": {"raw_input": "I"},
            "visual_spec": {"raw_input": "A2"},
            "characters": {"raw_input": "A"},
            "voice": {"raw_input": "A"},
            "music": {"raw_input": "B3"},
            "final_output": {"raw_input": "C"},
        },
        "user_answers": {
            "idea": "一位年轻的女性穿着裙子，在黄昏的海滩上散步、放空自己。",
            "target_duration": "B",
            "genre": "G",
            "style": "I",
            "visual_spec": "A2",
            "characters": "A",
            "voice": "A",
            "music": "B3",
            "final_output": "C",
        },
        "normalized": {
            "idea": "一位年轻的女性穿着裙子，在黄昏的海滩上散步、放空自己。",
            "target_duration_sec": 30,
            "target_duration_label": "30秒",
            "genre": "治愈",
            "style": "温暖治愈",
            "aspect_ratio": "9:16",
            "aspect_ratio_label": "9:16 竖屏",
            "resolution": "1080P",
            "resolution_label": "1080P",
            "characters_mode": "有固定主角/人物",
            "characters_required": True,
            "voice_mode": "不需要配音",
            "voice_required": False,
            "music_mode": "需要",
            "music_profile": "underscore",
            "music_required": True,
            "final_output": "剧本 + 分镜 + 关键帧提示词",
        },
        "missing_required_fields": [],
        "required_fields_complete": True,
        "next_question_key": "",
        "next_prompt_text": stage00_intake_common.canonical_question_block("final_confirmation"),
        "ready_for_brief_generation": True,
        "last_user_reply": "C",
        "updated_at": stage00_intake_common.utc_now(),
    }


def make_stage00_brief_llm_output_valid() -> dict:
    return {
        "source": "Created from user-supplied Stage 00 intake answers.",
        "user_answers": {
            "idea": "一位年轻的女性穿着裙子，在黄昏的海滩上散步、放空自己。",
            "target_duration": "B",
            "genre": "G",
            "style": "I",
            "visual_spec": "A2",
            "characters": "A",
            "voice": "A",
            "music": "B3",
            "final_output": "C",
        },
        "normalized": {
            "idea": "一位年轻的女性穿着裙子，在黄昏的海滩上散步、放空自己。",
            "target_duration_sec": 30,
            "target_duration_label": "30秒",
            "genre": "治愈",
            "style": "温暖治愈",
            "aspect_ratio": "9:16",
            "aspect_ratio_label": "9:16 竖屏",
            "resolution": "1080P",
            "resolution_label": "1080P",
            "characters_mode": "有固定主角/人物",
            "characters_required": True,
            "voice_mode": "不需要配音",
            "voice_required": False,
            "music_mode": "需要",
            "music_profile": "underscore",
            "music_required": True,
            "final_output": "剧本 + 分镜 + 关键帧提示词",
        },
        "required_fields_complete": True,
        "missing_required_fields": [],
        "brief_confirmation_summary": {
            "idea": "一位年轻的女性穿着裙子，在黄昏的海滩上散步、放空自己。",
            "target_duration": "30秒",
            "genre": "治愈",
            "style": "温暖治愈",
            "visual_spec": "9:16 竖屏 + 1080P",
            "characters": "有固定主角/人物",
            "voice": "不需要配音",
            "music": "需要，背景配乐（underscore）",
            "final_output": "剧本 + 分镜 + 关键帧提示词",
        },
    }


def make_stage00_brief_llm_output_invalid_music() -> dict:
    data = make_stage00_brief_llm_output_valid()
    data["normalized"]["music_profile"] = ""
    return data


def test_build_stage00_intake_prompt_packet_uses_canonical_opening_for_new_state(tmp_path: Path) -> None:
    state_path = tmp_path / ".video_project" / "intake" / "intake_state.json"
    packet_path = tmp_path / ".video_project" / "intake" / "stage00_intake_prompt_packet.json"
    assert build_stage00_intake_prompt_packet.main([
        str(state_path),
        str(packet_path),
        "--user-reply",
        "一位年轻的女性穿着裙子，在黄昏的海滩上散步、放空自己。",
    ]) == 0

    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    assert packet["current_state"]["current_question_key"] == "idea"
    assert packet["canonical_context"]["current_question_block"] == stage00_intake_common.canonical_question_block("idea")
    assert packet["user_reply_raw"] == "一位年轻的女性穿着裙子，在黄昏的海滩上散步、放空自己。"


def test_write_stage00_intake_state_advances_to_next_question(tmp_path: Path) -> None:
    state_path = tmp_path / ".video_project" / "intake" / "intake_state.json"
    llm_output_path = tmp_path / ".video_project" / "intake" / "stage00_intake_turn_llm_output.json"
    llm_output_path.parent.mkdir(parents=True, exist_ok=True)
    llm_output_path.write_text(json.dumps(make_stage00_turn_output_for_idea(), ensure_ascii=False, indent=2), encoding="utf-8")

    assert write_stage00_intake_state.main([
        "write_stage00_intake_state.py",
        str(state_path),
        str(llm_output_path),
    ]) == 0

    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["current_question"] == 2
    assert state["current_question_key"] == "target_duration"
    assert state["next_question_key"] == "target_duration"
    assert state["next_prompt_text"] == stage00_intake_common.canonical_question_block("target_duration")
    assert state["user_answers"]["idea"] == "一位年轻的女性穿着裙子，在黄昏的海滩上散步、放空自己。"
    ok, errors, warnings = validate_stage00_intake_state.validate(state, state_path)
    assert ok, errors


def test_write_stage00_intake_state_preserves_prior_answers_when_patch_contains_nulls(tmp_path: Path) -> None:
    state_path = tmp_path / ".video_project" / "intake" / "intake_state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps({
        "schema_version": "0.4.0",
        "stage": "STAGE_00_INTAKE",
        "status": "collecting",
        "project_id": "video_intake_project",
        "project_dir": str((tmp_path / ".video_project" / "intake").resolve()).replace("\\", "/"),
        "current_question": 7,
        "current_question_key": "voice",
        "answers": {
            "idea": {"raw_input": "一个暴雨夜追纸鹤的女生。"},
            "target_duration": {"raw_input": "C"},
            "genre": {"raw_input": "B"},
            "style": {"raw_input": "C"},
            "visual_spec": {"raw_input": "B2"},
            "characters": {"raw_input": "A"},
        },
        "user_answers": {
            "idea": "一个暴雨夜追纸鹤的女生。",
            "target_duration": "C",
            "genre": "B",
            "style": "C",
            "visual_spec": "B2",
            "characters": "A",
        },
        "normalized": {
            "idea": "一个暴雨夜追纸鹤的女生。",
            "target_duration_sec": 60,
            "target_duration_label": "60秒",
            "genre": "悬疑",
            "style": "日系动画风（日本动漫感）",
            "aspect_ratio": "16:9",
            "aspect_ratio_label": "16:9 横屏",
            "resolution": "1080P",
            "resolution_label": "1080P",
            "characters_mode": "有固定主角/人物",
            "characters_required": True,
        },
        "missing_required_fields": ["voice", "music", "final_output"],
        "required_fields_complete": False,
        "next_question_key": "voice",
        "next_prompt_text": stage00_intake_common.canonical_question_block("voice"),
        "ready_for_brief_generation": False,
        "last_user_reply": "A",
        "updated_at": stage00_intake_common.utc_now(),
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    llm_output_path = state_path.parent / "stage00_intake_turn_llm_output.json"
    llm_output_path.write_text(json.dumps({
        "answered_question_key": "voice",
        "user_answer_entry": {
            "raw_input": "A",
            "selected_option": "A",
            "free_text_notes": "",
        },
        "user_answers_patch": {
            "idea": None,
            "target_duration": None,
            "genre": None,
            "style": None,
            "visual_spec": None,
            "characters": None,
            "characters_note": None,
            "voice": "A",
            "music": None,
            "final_output": None,
        },
        "normalized_patch": {
            "idea": None,
            "target_duration_sec": None,
            "target_duration_label": None,
            "genre": None,
            "style": None,
            "aspect_ratio": None,
            "aspect_ratio_label": None,
            "resolution": None,
            "resolution_label": None,
            "characters_mode": None,
            "characters_required": None,
            "voice_mode": "不需要配音",
            "voice_required": False,
            "music_mode": None,
            "music_profile": None,
            "music_required": None,
            "final_output": None,
        },
        "missing_required_fields": ["music", "final_output"],
        "required_fields_complete": False,
        "status": "collecting",
        "next_question_key": "music",
        "next_prompt_text": stage00_intake_common.canonical_question_block("music"),
        "needs_followup": False,
        "followup_reason": "",
        "completion_summary": "已记录问题 7：配音选择为 A（不需要配音），进入问题 8。",
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    assert write_stage00_intake_state.main([
        "write_stage00_intake_state.py",
        str(state_path),
        str(llm_output_path),
    ]) == 0

    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["current_question_key"] == "music"
    assert state["user_answers"]["idea"] == "一个暴雨夜追纸鹤的女生。"
    assert state["user_answers"]["characters"] == "A"
    assert state["user_answers"]["voice"] == "A"
    assert state["normalized"]["target_duration_sec"] == 60
    assert state["normalized"]["characters_required"] is True
    assert state["normalized"]["voice_required"] is False
    ok, errors, warnings = validate_stage00_intake_state.validate(state, state_path)
    assert ok, errors


def test_run_stage00_intake_turn_codex_flow_writes_packet_llm_output_and_state(tmp_path: Path, monkeypatch) -> None:
    state_path = tmp_path / ".video_project" / "intake" / "intake_state.json"

    assert run_stage00_intake_turn_codex_flow.main([
        str(state_path),
        "--user-reply",
        "一位年轻的女性穿着裙子，在黄昏的海滩上散步、放空自己。",
    ]) == 0

    intake_dir = state_path.parent
    assert (intake_dir / "stage00_intake_prompt_packet.json").exists()
    assert (intake_dir / "stage00_intake_turn_llm_output.json").exists()
    assert (intake_dir / "stage00_intake_codex_generation_request.txt").exists()
    assert (intake_dir / "stage00_intake_codex_last_message.txt").exists()
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["current_question_key"] == "target_duration"


def test_build_stage00_brief_prompt_packet_uses_draft_ready_state(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260603_000001_stage00b"
    intake_dir = project_dir / "00_intake"
    intake_dir.mkdir(parents=True, exist_ok=True)
    state_path = intake_dir / "intake_state.json"
    state_path.write_text(json.dumps(make_stage00_draft_ready_state(state_path), ensure_ascii=False, indent=2), encoding="utf-8")
    draft_path = intake_dir / "project_brief.draft.json"
    packet_path = intake_dir / "stage00_brief_prompt_packet.json"

    assert build_stage00_brief_prompt_packet.main([
        str(state_path),
        str(draft_path),
        str(packet_path),
    ]) == 0

    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    assert packet["stage_label"] == "Stage 00-B"
    assert packet["intake_completion_state"]["ready_for_brief_generation"] is True
    assert packet["normalized"]["style"] == "温暖治愈"


def test_write_stage00_brief_outputs_generates_valid_draft(tmp_path: Path) -> None:
    project_root = tmp_path / "video_projects"
    old_argv = sys.argv[:]
    try:
        sys.argv = [
            "create_project_folder.py",
            "--root",
            str(project_root),
            "--title",
            "黄昏海滩散步",
        ]
        assert create_project_folder.main() == 0
    finally:
        sys.argv = old_argv
    project_dir = next(project_root.iterdir())
    intake_dir = project_dir / "00_intake"
    state_path = intake_dir / "intake_state.json"
    llm_output_path = intake_dir / "stage00_brief_llm_output.json"
    draft_path = intake_dir / "project_brief.draft.json"
    state = make_stage00_draft_ready_state(state_path)
    state["project_id"] = project_dir.name
    state["project_dir"] = str(project_dir).replace("\\", "/")
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    llm_output_path.write_text(json.dumps(make_stage00_brief_llm_output_valid(), ensure_ascii=False, indent=2), encoding="utf-8")

    assert write_stage00_brief_outputs.main([
        "write_stage00_brief_outputs.py",
        str(state_path),
        str(llm_output_path),
        str(draft_path),
    ]) == 0

    draft = json.loads(draft_path.read_text(encoding="utf-8"))
    ok, errors, warnings = validate_project_brief.validate(draft, draft_path)
    assert ok, errors
    assert draft["status"] == "draft"
    assert (intake_dir / "stage00_brief_confirmation_summary.md").exists()


def test_run_stage00_brief_codex_flow_generates_valid_draft_locally(tmp_path: Path) -> None:
    project_root = tmp_path / "video_projects"
    old_argv = sys.argv[:]
    try:
        sys.argv = [
            "create_project_folder.py",
            "--root",
            str(project_root),
            "--title",
            "黄昏海滩散步",
        ]
        assert create_project_folder.main() == 0
    finally:
        sys.argv = old_argv
    project_dir = next(project_root.iterdir())
    intake_dir = project_dir / "00_intake"
    state_path = intake_dir / "intake_state.json"
    draft_path = intake_dir / "project_brief.draft.json"
    state = make_stage00_draft_ready_state(state_path)
    state["project_id"] = project_dir.name
    state["project_dir"] = str(project_dir).replace("\\", "/")
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    assert run_stage00_brief_codex_flow.main([
        str(state_path),
        str(draft_path),
    ]) == 0

    assert (intake_dir / "stage00_brief_prompt_packet.json").exists()
    assert (intake_dir / "stage00_brief_llm_output.json").exists()
    assert (intake_dir / "stage00_brief_codex_last_message.txt").exists()
    assert not (intake_dir / "stage00_brief_validation_errors.json").exists()
    assert not (intake_dir / "stage00_brief_repair_packet.json").exists()
    draft = json.loads(draft_path.read_text(encoding="utf-8"))
    assert draft["normalized"]["music_profile"] == "underscore"


def test_pipeline_stage00_intake_wrapper_prints_current_prompt_without_user_reply(tmp_path: Path, capsys) -> None:
    state_path = tmp_path / ".video_project" / "intake" / "intake_state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(make_stage00_draft_ready_state(state_path) | {
        "status": "collecting",
        "current_question": 1,
        "current_question_key": "idea",
        "next_question_key": "idea",
        "next_prompt_text": stage00_intake_common.canonical_question_block("idea"),
        "required_fields_complete": False,
        "ready_for_brief_generation": False,
        "missing_required_fields": stage00_intake_common.QUESTION_KEYS,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    assert run_stage00_intake_turn_wrapper.main([
        "--state-json",
        str(state_path),
    ]) == 0
    output = capsys.readouterr().out
    assert "PIPELINE_STAGE00_CURRENT_QUESTION_KEY: idea" in output
    assert "问题 1：你的故事想法/创意是什么？" in output


def test_stage00_controller_collecting_reply_surfaces_next_prompt_in_same_call(tmp_path: Path, monkeypatch, capsys) -> None:
    state_path = tmp_path / ".video_project" / "intake" / "intake_state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps({
        "schema_version": "0.4.0",
        "stage": "STAGE_00_INTAKE",
        "status": "collecting",
        "project_id": ".video_project",
        "project_dir": str((tmp_path / ".video_project").resolve()).replace("\\", "/"),
        "current_question": 2,
        "current_question_key": "target_duration",
        "answers": {
            "idea": {
                "raw_input": "一个年轻女生深夜独自下班，在回家路上被一盏深夜便利店的暖光轻轻治愈。",
                "selected_option": "",
                "free_text_notes": "深夜便利店暖光治愈",
                "question_key": "idea",
            },
        },
        "user_answers": {
            "idea": "一个年轻女生深夜独自下班，在回家路上被一盏深夜便利店的暖光轻轻治愈。",
        },
        "normalized": {
            "idea": "一个年轻女生深夜独自下班，在回家路上被一盏深夜便利店的暖光轻轻治愈。",
        },
        "missing_required_fields": [
            "target_duration",
            "genre",
            "style",
            "visual_spec",
            "characters",
            "voice",
            "music",
            "final_output",
        ],
        "required_fields_complete": False,
        "next_question_key": "target_duration",
        "next_prompt_text": stage00_intake_common.canonical_question_block("target_duration"),
        "ready_for_brief_generation": False,
        "last_user_reply": "",
        "updated_at": stage00_intake_common.utc_now(),
        "needs_followup": False,
        "followup_reason": "",
        "completion_summary": "",
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    def fake_codex_flow(argv: list[str] | None = None) -> int:
        del argv
        current = json.loads(state_path.read_text(encoding="utf-8"))
        current["answers"]["target_duration"] = {
            "raw_input": "A",
            "selected_option": "A",
            "free_text_notes": "",
            "question_key": "target_duration",
        }
        current["user_answers"]["target_duration"] = "A"
        current["normalized"]["target_duration_sec"] = 15
        current["normalized"]["target_duration_label"] = "15秒"
        current["missing_required_fields"] = [
            "genre",
            "style",
            "visual_spec",
            "characters",
            "voice",
            "music",
            "final_output",
        ]
        current["current_question"] = 3
        current["current_question_key"] = "genre"
        current["next_question_key"] = "genre"
        current["next_prompt_text"] = stage00_intake_common.canonical_question_block("genre")
        current["last_user_reply"] = "A"
        current["completion_summary"] = "目标时长已记录为15秒，继续询问视频题材。"
        current["updated_at"] = stage00_intake_common.utc_now()
        state_path.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
        return 0

    monkeypatch.setattr(
        run_stage00_controller.run_stage00_intake_turn,
        "run_stage00_intake_turn_codex_flow_main",
        fake_codex_flow,
    )

    assert run_stage00_controller.main([
        "--state-json",
        str(state_path),
        "--user-reply",
        "A",
    ]) == 0

    output = capsys.readouterr().out
    assert "PIPELINE_STAGE00_STATE: collecting" in output
    assert "PIPELINE_STAGE00_CURRENT_QUESTION_KEY: genre" in output
    assert "问题 3：视频题材是什么？" in output


def test_stage00_controller_confirmation_a_dispatches_lock_and_continue(tmp_path: Path, monkeypatch) -> None:
    project_dir = create_project_folder.create_project(tmp_path / "video_projects", title="黄昏海滩散步")
    intake_dir = project_dir / "00_intake"
    state_path = intake_dir / "intake_state.json"
    state = make_stage00_draft_ready_state(state_path)
    state["project_id"] = project_dir.name
    state["project_dir"] = str(project_dir).replace("\\", "/")
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    (intake_dir / "project_brief.draft.json").write_text(json.dumps({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "stage": "STAGE_00_INTAKE",
        "status": "draft",
        "confirmed_by_user": False,
        "required_fields_complete": True,
        "missing_required_fields": [],
        "source": "test",
        "normalized": make_stage00_brief_llm_output_valid()["normalized"],
        "schema_version": "0.3.0",
        "allowed_next_stage": None,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    (intake_dir / "stage00_brief_confirmation_summary.md").write_text("summary", encoding="utf-8")

    called: dict[str, object] = {}

    def fake_lock(argv=None):  # noqa: ANN001
        called["argv"] = list(argv or [])
        return 0

    monkeypatch.setattr(run_stage00_controller.run_stage00_lock_and_continue, "main", fake_lock)
    assert run_stage00_controller.main([
        "--state-json",
        str(state_path),
        "--user-reply",
        "A",
        "--project-dir",
        str(project_dir),
    ]) == 0
    assert called["argv"] == [str(project_dir)]


def test_stage00_controller_confirmation_b_rewinds_selected_item_and_clears_draft(tmp_path: Path, capsys) -> None:
    project_dir = create_project_folder.create_project(tmp_path / "video_projects", title="黄昏海滩散步")
    intake_dir = project_dir / "00_intake"
    state_path = intake_dir / "intake_state.json"
    state = make_stage00_draft_ready_state(state_path)
    state["project_id"] = project_dir.name
    state["project_dir"] = str(project_dir).replace("\\", "/")
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    (intake_dir / "project_brief.draft.json").write_text("{}", encoding="utf-8")
    (intake_dir / "stage00_brief_confirmation_summary.md").write_text("summary", encoding="utf-8")

    assert run_stage00_controller.main([
        "--state-json",
        str(state_path),
        "--user-reply",
        "B",
        "--project-dir",
        str(project_dir),
    ]) == 0
    state_after_b = json.loads(state_path.read_text(encoding="utf-8"))
    assert state_after_b["confirmation_mode"] == "await_modify_item"

    assert run_stage00_controller.main([
        "--state-json",
        str(state_path),
        "--user-reply",
        "4",
        "--project-dir",
        str(project_dir),
    ]) == 0
    output = capsys.readouterr().out
    rewound = json.loads(state_path.read_text(encoding="utf-8"))
    assert rewound["status"] == "collecting"
    assert rewound["current_question"] == 4
    assert rewound["current_question_key"] == "style"
    assert rewound["next_prompt_text"] == stage00_intake_common.canonical_question_block("style")
    assert rewound["missing_required_fields"] == ["style", "visual_spec", "characters", "voice", "music", "final_output"]
    assert "idea" in rewound["user_answers"]
    assert "genre" in rewound["user_answers"]
    assert "style" not in rewound["user_answers"]
    assert not (intake_dir / "project_brief.draft.json").exists()
    assert "问题 4：视频风格是什么？" in output


def test_stage00_controller_confirmation_c_resets_to_question_one_and_clears_stage00_artifacts(tmp_path: Path, capsys) -> None:
    project_dir = create_project_folder.create_project(tmp_path / "video_projects", title="黄昏海滩散步")
    intake_dir = project_dir / "00_intake"
    state_path = intake_dir / "intake_state.json"
    state = make_stage00_draft_ready_state(state_path)
    state["project_id"] = project_dir.name
    state["project_dir"] = str(project_dir).replace("\\", "/")
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    (intake_dir / "project_brief.draft.json").write_text("{}", encoding="utf-8")
    (intake_dir / "project_brief.locked.json").write_text("{}", encoding="utf-8")
    (intake_dir / "stage00_brief_confirmation_summary.md").write_text("summary", encoding="utf-8")

    assert run_stage00_controller.main([
        "--state-json",
        str(state_path),
        "--user-reply",
        "C",
        "--project-dir",
        str(project_dir),
    ]) == 0
    output = capsys.readouterr().out
    reset = json.loads(state_path.read_text(encoding="utf-8"))
    assert reset["status"] == "collecting"
    assert reset["current_question"] == 1
    assert reset["current_question_key"] == "idea"
    assert reset["missing_required_fields"] == stage00_intake_common.QUESTION_KEYS
    assert reset["answers"] == {}
    assert reset["user_answers"] == {}
    assert not (intake_dir / "project_brief.draft.json").exists()
    assert not (intake_dir / "project_brief.locked.json").exists()
    assert "问题 1：你的故事想法/创意是什么？" in output


def test_continue_pipeline_uses_workspace_stage00_prompt_when_no_project_exists(tmp_path: Path, monkeypatch, capsys) -> None:
    state_path = tmp_path / ".video_project" / "intake" / "intake_state.json"
    state = make_stage00_draft_ready_state(state_path)
    state.update({
        "status": "collecting",
        "current_question": 1,
        "current_question_key": "idea",
        "next_question_key": "idea",
        "next_prompt_text": stage00_intake_common.canonical_question_block("idea"),
        "required_fields_complete": False,
        "ready_for_brief_generation": False,
        "missing_required_fields": stage00_intake_common.QUESTION_KEYS,
        "project_dir": "",
        "project_id": "video_intake_project",
    })
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    called: dict[str, object] = {}

    def fake_stage00(argv=None):  # noqa: ANN001
        called["argv"] = list(argv or [])
        print("PIPELINE_STAGE00_PROMPT_BEGIN")
        print(stage00_intake_common.canonical_question_block("idea"))
        print("PIPELINE_STAGE00_PROMPT_END")
        return 0

    monkeypatch.setattr(continue_pipeline.run_stage00_controller, "main", fake_stage00)
    assert continue_pipeline.main([
        "--root",
        str(tmp_path / "video_projects"),
        "--stage00-state",
        str(state_path),
    ]) == 0
    output = capsys.readouterr().out
    assert "PIPELINE_STAGE00_PROMPT_BEGIN" in output
    assert "问题 1：你的故事想法/创意是什么？" in output
    assert called["argv"] == ["--state-json", str(state_path)]


def test_continue_pipeline_dispatches_stage00_draft_ready_project_to_stage00b(tmp_path: Path, monkeypatch) -> None:
    project_root = tmp_path / "video_projects"
    project_dir = create_project_folder.create_project(project_root, title="黄昏海滩散步")
    intake_dir = project_dir / "00_intake"
    state_path = intake_dir / "intake_state.json"
    state = make_stage00_draft_ready_state(state_path)
    state["project_id"] = project_dir.name
    state["project_dir"] = str(project_dir).replace("\\", "/")
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    called: dict[str, object] = {}

    def fake_stage00b(argv=None):  # noqa: ANN001
        called["argv"] = list(argv or [])
        return 0

    monkeypatch.setattr(continue_pipeline.run_stage00_controller, "main", fake_stage00b)
    assert continue_pipeline.main(["--project-dir", str(project_dir)]) == 0
    assert called["argv"] == [
        "--state-json",
        str(state_path),
        "--project-dir",
        str(project_dir),
    ]


def test_project_state_recommended_entry_prefers_stage00_command_when_brief_not_locked(tmp_path: Path) -> None:
    project_dir = create_project_folder.create_project(tmp_path / "video_projects", title="黄昏海滩散步")
    manifest_path = project_dir / "project_manifest.json"
    intake_state = make_stage00_draft_ready_state(project_dir / "00_intake" / "intake_state.json")
    intake_state["project_id"] = project_dir.name
    intake_state["project_dir"] = str(project_dir).replace("\\", "/")
    (project_dir / "00_intake" / "intake_state.json").write_text(json.dumps(intake_state, ensure_ascii=False, indent=2), encoding="utf-8")

    assert project_state.sync_project_manifest_truth(manifest_path) == manifest_path
    synced = json.loads(manifest_path.read_text(encoding="utf-8"))
    recommended = synced["creator_status_overview"]["recommended_entry"]
    assert recommended["label"] == "继续 Stage 00 立项流程"
    assert "run_stage00_controller.py" in recommended["command"]


def test_official_pipeline_blank_project_reaches_stage01_without_rainy_store_phrase_regression(tmp_path: Path) -> None:
    state_path = tmp_path / ".video_project" / "intake" / "intake_state.json"
    project_root = tmp_path / "video_projects"
    replies = [
        "雨夜便利店门口，一个年轻女孩把伞留给没带伞的陌生人，然后自己走进雨里，回头发现门口多了一杯热可可。",
        "B",
        "G",
        "M",
        "B2",
        "A，主角是二十多岁的年轻女性，穿浅色衬衫和深色长裤，手里拿一把黑伞。",
        "B",
        "B3",
        "F",
        "A",
    ]

    original_stage01_main = run_stage00_controller.run_stage00_lock_and_continue.run_stage01_from_locked_brief.main

    def fake_stage01_main(argv: list[str] | None = None) -> int:
        assert argv is not None
        locked_brief = Path(argv[0])
        script_json = Path(argv[1])
        script_json.parent.mkdir(parents=True, exist_ok=True)
        llm_output = stage01_stage_tests.make_stage01_llm_output_for_rainy_store()
        (script_json.parent / "stage01_llm_output.json").write_text(
            json.dumps(llm_output, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return new_script_template.main([
            "new_script_template.py",
            str(locked_brief),
            str(script_json),
        ])

    run_stage00_controller.run_stage00_lock_and_continue.run_stage01_from_locked_brief.main = fake_stage01_main

    try:
        assert run_stage00_controller.main([
            "--state-json",
            str(state_path),
            "--project-root",
            str(project_root),
        ]) == 0
        for reply in replies:
            assert run_stage00_controller.main([
                "--state-json",
                str(state_path),
                "--project-root",
                str(project_root),
                "--user-reply",
                reply,
            ]) == 0
    finally:
        run_stage00_controller.run_stage00_lock_and_continue.run_stage01_from_locked_brief.main = original_stage01_main

    projects = [item for item in project_root.iterdir() if item.is_dir()]
    assert len(projects) == 1
    project_dir = projects[0]
    manifest = json.loads((project_dir / "project_manifest.json").read_text(encoding="utf-8"))
    assert manifest["current_stage"] == "STAGE_01_SCRIPT_GENERATION"
    assert manifest["brief_locked"] is True
    assert manifest["script_confirmed"] is False

    summary_path = project_dir / "00_intake" / "stage00_brief_confirmation_summary.md"
    assert summary_path.exists()
    assert "背景配乐（underscore）" in summary_path.read_text(encoding="utf-8")

    script_path = project_dir / "01_script" / "script.json"
    assert script_path.exists()
    script = json.loads(script_path.read_text(encoding="utf-8-sig"))
    assert script["title"] == "雨夜留下的伞"
    assert "热可可" in script["logline"]

    beat_summaries = [str(beat.get("summary") or "") for beat in script["duration_plan"]["beats"]]
    visuals = [str(section.get("visual") or "") for section in script["script"]["sections"]]
    assert any("最后一把伞" in summary or "淋着雨" in summary for summary in beat_summaries)
    assert any("热可可" in summary for summary in beat_summaries)
    assert all("年轻女孩雨夜便利店门口" not in summary for summary in beat_summaries)
    assert all("雨夜便利店门口里，年轻女孩雨夜便利店门口" not in visual for visual in visuals)
