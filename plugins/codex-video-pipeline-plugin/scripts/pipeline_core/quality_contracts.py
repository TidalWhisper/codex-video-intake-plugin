from __future__ import annotations

from typing import Any

from .requirement_compiler import compile_requirements, normal_brief


def build_quality_contract(brief: dict[str, Any], compiled: dict[str, Any] | None = None) -> dict[str, Any]:
    compiled = compiled or compile_requirements(brief)
    normalized = normal_brief(brief)
    shape = str(compiled.get("project_shape") or "narrative_short")
    music_profile = str((compiled.get("audio_mode") or {}).get("music_profile") or "")
    requires_voice = (compiled.get("audio_mode") or {}).get("voice_mode") not in {"", "不需要配音"}
    human_review_flags = list(((compiled.get("qa_profile") or {}).get("human_review_flags")) or [])

    axes = [
        {
            "axis_id": "intent_alignment",
            "label": "需求意图对齐",
            "description": "最终输出阶段、镜头组织和素材包类型应与锁定 brief 的交付意图一致。",
            "severity": "blocker",
            "stages": ["STAGE_05", "STAGE_06", "STAGE_07", "STAGE_08", "STAGE_09"],
        },
        {
            "axis_id": "visual_continuity",
            "label": "视觉连续性",
            "description": "人物/主体、风格路线、关键帧与片段之间应保持一致的 continuity anchors。",
            "severity": "major",
            "stages": ["STAGE_05", "STAGE_06", "STAGE_09"],
        },
        {
            "axis_id": "performance_direction",
            "label": "表演与镜头方向",
            "description": "动作幅度、情绪推进、镜头说明和对白承接应在提示词与片段阶段保持一致。",
            "severity": "major",
            "stages": ["STAGE_04", "STAGE_06", "STAGE_07", "STAGE_09"],
        },
        {
            "axis_id": "audio_direction",
            "label": "声音方向",
            "description": "配音、旁白和音乐模式应与 brief 中的声音策略一致。",
            "severity": "major",
            "stages": ["STAGE_07", "STAGE_08", "STAGE_09"],
        },
        {
            "axis_id": "delivery_readiness",
            "label": "交付完整性",
            "description": "最终粗剪、交付说明和资产索引应完整可追踪。",
            "severity": "blocker",
            "stages": ["STAGE_08", "STAGE_09"],
        },
    ]
    if shape in {"brand_promo", "factual_explainer"}:
        axes.append({
            "axis_id": "message_accuracy",
            "label": "信息准确性",
            "description": "品牌表达或事实说明需要在交付前经过人工复核。",
            "severity": "major",
            "stages": ["STAGE_01", "STAGE_09"],
            "review_mode": "human_review",
        })
    if music_profile == "song" or shape == "music_video":
        axes.append({
            "axis_id": "music_sync",
            "label": "音乐节奏匹配",
            "description": "画面节奏和音乐模式应适合 MV / 歌曲驱动项目。",
            "severity": "major",
            "stages": ["STAGE_07", "STAGE_08", "STAGE_09"],
        })
    if requires_voice:
        axes.append({
            "axis_id": "spoken_line_coverage",
            "label": "台词覆盖",
            "description": "需要配音时，旁白/对白对应的音频 job 和字幕覆盖应完整。",
            "severity": "major",
            "stages": ["STAGE_07", "STAGE_08", "STAGE_09"],
        })

    return {
        "schema_version": "0.1.0",
        "contract_id": f"{shape}:{normalized.get('final_output') or ''}",
        "project_shape": shape,
        "creative_focus": compiled.get("creative_focus"),
        "continuity_mode": compiled.get("continuity_mode"),
        "axes": axes,
        "human_review_flags": human_review_flags,
    }


def build_stage_quality_targets(stage: str, contract: dict[str, Any]) -> list[dict[str, Any]]:
    targets = []
    prefix = stage.split("_", 2)[0:2]
    stage_short = "_".join(prefix) if prefix else stage
    for axis in contract.get("axes") or []:
        if not isinstance(axis, dict):
            continue
        stages = axis.get("stages") or []
        if stage_short in stages or stage in stages:
            targets.append({
                "axis_id": axis.get("axis_id"),
                "label": axis.get("label"),
                "severity": axis.get("severity"),
                "review_mode": axis.get("review_mode", "auto_contract"),
                "description": axis.get("description"),
            })
    return targets


def build_qa_checks(brief: dict[str, Any], compiled: dict[str, Any], contract: dict[str, Any]) -> list[dict[str, Any]]:
    base_checks = [
        {"check_id": "final_video_evidence", "category": "file_evidence", "description": "最终粗剪视频文件存在且非空", "status": "pending", "severity": "blocker"},
        {"check_id": "duration_consistency", "category": "timeline", "description": "粗剪时长与分镜/片段时长基本一致", "status": "pending", "severity": "major"},
        {"check_id": "storyboard_coverage", "category": "story", "description": "所有关键分镜均在粗剪时间线中出现", "status": "pending", "severity": "major"},
        {"check_id": "audio_presence", "category": "audio", "description": "需要配音/音乐时音频轨已纳入交付说明", "status": "pending", "severity": "major"},
        {"check_id": "subtitle_package", "category": "subtitle", "description": "字幕文件或字幕说明已归档", "status": "pending", "severity": "minor"},
        {"check_id": "delivery_package", "category": "delivery", "description": "最终交付包文件齐全", "status": "pending", "severity": "blocker"},
    ]
    dynamic_checks = [
        {"check_id": "intent_alignment", "category": "strategy", "description": "Stage 路由、最终交付形式与锁定需求一致", "status": "pending", "severity": "blocker"},
        {"check_id": "content_text_alignment", "category": "human_review", "description": "人工确认图像/视频内容与脚本、分镜和文字描述一致", "status": "pending", "severity": "blocker", "review_mode": "human_review"},
        {"check_id": "visual_continuity_contract", "category": "visual", "description": "视觉连续性约束已贯穿关键帧与视频片段", "status": "pending", "severity": "major"},
        {"check_id": "performance_direction_contract", "category": "performance", "description": "动作/情绪/对白方向在提示词、片段和音频阶段保持一致", "status": "pending", "severity": "major"},
        {"check_id": "audio_direction_contract", "category": "audio", "description": "配音与音乐模式匹配 brief 的声音策略", "status": "pending", "severity": "major"},
        {"check_id": "format_fit_contract", "category": "delivery", "description": "输出比例/风格路线/创作目标匹配需求编译策略", "status": "pending", "severity": "major"},
    ]
    for flag in contract.get("human_review_flags") or []:
        dynamic_checks.append({
            "check_id": f"human_review_{flag}",
            "category": "human_review",
            "description": f"人工复核：{flag}",
            "status": "pending",
            "severity": "major",
            "review_mode": "human_review",
        })
    return base_checks + dynamic_checks
