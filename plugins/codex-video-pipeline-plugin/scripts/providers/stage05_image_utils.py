#!/usr/bin/env python3
from __future__ import annotations

import json
import html
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from pipeline_blueprints import next_stage_after  # noqa: E402
from pipeline_core.project_state import annotate_evidence_origin  # noqa: E402
from pipeline_core.stage05_quality_gates import build_auto_repair_plan, build_creator_review_card, build_quality_gate, summarize_quality_review, UMBRELLA_HINTS  # noqa: E402

KNOWN_PLUGIN_ROOT_CHILDREN = {
    "video_projects",
    "templates",
    "config",
    "workflows",
    "skills",
    "scripts",
    "tests",
    "docs",
    "prompts",
}

DEFAULT_STAGE05_NEGATIVE_HINTS = (
    "text",
    "typography",
    "letters",
    "caption",
    "subtitle",
    "watermark",
    "logo",
)

GAME_CG_NEGATIVE_HINTS = (
    "wordmark",
    "headline text",
    "top title header",
    "sky title text",
    "pseudo chinese characters",
    "title card",
    "title plaque",
    "cover layout",
    "badge emblem",
    "ui frame",
)


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"ERROR: file not found: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON in {path}: {exc}")


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def plugin_root_for_manifest(manifest_path: Path) -> Path | None:
    return next(
        (anchor.resolve() for anchor in [manifest_path.parent, *manifest_path.parents] if anchor.name == "codex-video-pipeline-plugin"),
        None,
    )


def resolve_path(base_json: Path, raw: Any) -> Path:
    p = Path(str(raw))
    if p.is_absolute():
        return p
    if p.exists():
        return p.resolve()
    base_abs = base_json if base_json.is_absolute() else (Path.cwd() / base_json).resolve()

    def plugin_root_candidates() -> list[Path]:
        candidates: list[Path] = []
        seen: set[str] = set()

        def add(path: Path) -> None:
            resolved = path.resolve()
            if resolved.name != "codex-video-pipeline-plugin":
                return
            key = str(resolved).lower()
            if key not in seen:
                candidates.append(resolved)
                seen.add(key)

        for anchor in [base_abs.parent, *base_abs.parents]:
            add(anchor)
        cwd = Path.cwd().resolve()
        for anchor in [cwd, *cwd.parents]:
            add(anchor)
        add(ROOT)
        return candidates

    plugin_roots = plugin_root_candidates()
    if p.parts:
        first = p.parts[0].lower()
    special_roots: list[Path] = []
    repo_roots: list[Path] = []
    for plugin_root in plugin_roots:
        if plugin_root.parent.name == "plugins":
            repo_root = plugin_root.parent.parent.resolve()
            if repo_root not in repo_roots:
                repo_roots.append(repo_root)
    if p.parts:
        first = p.parts[0].lower()
        if first == "plugins":
            special_roots.extend(repo_roots)
        elif first in KNOWN_PLUGIN_ROOT_CHILDREN:
            special_roots.extend(plugin_roots)
    anchors: list[Path] = []
    seen: set[str] = set()
    for anchor in [*special_roots, *repo_roots, *plugin_roots, Path.cwd().resolve(), base_abs.parent, *base_abs.parents]:
        key = str(anchor.resolve()).lower()
        if key not in seen:
            anchors.append(anchor)
            seen.add(key)
    for anchor in anchors:
        candidate = (anchor / p).resolve()
        if candidate.exists():
            return candidate
    for anchor in anchors:
        candidate = (anchor / p).resolve()
        if candidate.parent.exists():
            return candidate
    return (base_json.parent / p).resolve()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _mentions_any(text: str, hints: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(hint.lower() in lowered for hint in hints)


def _prop_guardrail_sections(job: dict[str, Any]) -> list[str]:
    joined = " ".join(
        str(job.get(key) or "")
        for key in ["prompt", "style_prompt", "consistency_prompt", "camera_prompt", "negative_prompt"]
    )
    if _mentions_any(joined, UMBRELLA_HINTS):
        return [
            "Composition: one person only and one umbrella only in the entire frame, no second umbrella, no duplicate canopy, no extra umbrella in background or foreground, no mirrored accessory duplication",
            "Pose: single subject, exactly two arms and two hands, natural shoulder and elbow anatomy, one umbrella with one handle only, umbrella held by one believable visible hand or by both hands on the same single handle, the other hand must not hold a second prop, no duplicated hand or floating prop interaction",
            "Avoid: extra hands, extra fingers, duplicated arm, broken wrist, umbrella handle detached from hand, floating umbrella, impossible grip, second umbrella, duplicate umbrella canopy, overlapping parasol, mirrored limb anatomy",
        ]
    return []


def _route_guardrail_sections(job: dict[str, Any]) -> list[str]:
    route_key = str(job.get("stage05_route_key") or "").strip()
    camera_text = " ".join(
        str(job.get(key) or "")
        for key in ["camera_prompt", "prompt", "style_prompt", "consistency_prompt"]
    ).lower()
    if route_key == "realistic_cinematic" and (
        "establishing shot" in camera_text
        or ("wide shot" in camera_text and any(hint in camera_text for hint in ("shoreline", "beach", "sea", "street", "skyline")))
    ):
        return [
            "Composition: true environmental establishing shot with coastline, sky, or surrounding location clearly visible; keep the subject smaller in frame instead of turning it into a portrait close-up",
            "Scene intent: this is part of the story world itself, not a behind-the-scenes production still, not a fashion editorial set, and not a staged studio shoot",
            "Avoid: film set, camera rig, monitor, tripod, lighting stand, boom mic, crew equipment, camera operator, indoor soundstage, interview chair setup, glamour beauty pose, face-dominant crop",
        ]
    if route_key == "guofeng_ink" and ("medium scenic shot" in camera_text or "wide scenic shot" in camera_text or "scenic shot" in camera_text):
        return [
            "Composition: keep this as a medium scenic guofeng frame with visible rain atmosphere and readable surrounding environment, not a face-dominant beauty portrait",
            "Framing: show full umbrella canopy and enough robe silhouette or body posture to read the scene, with pavilion, riverbank, trees, mist, or other poetic depth cues visible around the subject",
            "Avoid: centered beauty close-up, glamour poster portrait, oversized face crop, bust-only framing, cropped umbrella canopy",
        ]
    if route_key == "game_cg":
        return [
            "Output: deliver clean full-bleed artwork only for downstream video use, not a finished poster, cover, title card, or marketing layout",
            "Composition: no footer title plaque, no centered wordmark, no logo badge, no caption band, no UI frame, no floating emblem, and no fake engraved scene text",
            "Frame hygiene: keep the upper sky and top border free of any title header, fake runes, pseudo Chinese characters, or decorative lettering of any kind",
            "Instruction: if the request implies splash art or key art, interpret it as artwork-only image content without any rendered lettering or branding elements",
        ]
    return []


def _realistic_establishing_negative_hints(job: dict[str, Any]) -> list[str]:
    route_key = str(job.get("stage05_route_key") or "").strip()
    if route_key != "realistic_cinematic":
        return []
    camera_text = " ".join(
        str(job.get(key) or "")
        for key in ["camera_prompt", "prompt", "style_prompt", "consistency_prompt"]
    ).lower()
    if not (
        "establishing shot" in camera_text
        or ("wide shot" in camera_text and any(hint in camera_text for hint in ("shoreline", "beach", "sea", "street", "skyline")))
    ):
        return []
    return [
        "centered full-body portrait",
        "centered beauty pose",
        "hero poster framing",
        "face-dominant composition",
        "fashion portrait framing",
        "subject filling frame",
    ]


def effective_negative_prompt(job: dict[str, Any]) -> str:
    existing = [item.strip() for item in str(job.get("negative_prompt") or "").split(",") if item.strip()]
    existing.extend(
        item.strip()
        for item in (job.get("repair_negative_prompt_additions") or [])
        if isinstance(item, str) and item.strip()
    )
    existing.extend(
        item.strip()
        for item in str(job.get("comfyui_style_negative_anchor") or "").split(",")
        if item.strip()
    )
    existing.extend(_realistic_establishing_negative_hints(job))
    seen = {item.lower() for item in existing}
    merged = list(existing)
    for hint in DEFAULT_STAGE05_NEGATIVE_HINTS:
        if hint.lower() not in seen:
            merged.append(hint)
            seen.add(hint.lower())
    if str(job.get("stage05_route_key") or "").strip() == "game_cg":
        for hint in GAME_CG_NEGATIVE_HINTS:
            if hint.lower() not in seen:
                merged.append(hint)
                seen.add(hint.lower())
    return ", ".join(merged)


def _is_original_zimage_ui_workflow(job: dict[str, Any]) -> bool:
    source_ref = str(job.get("preferred_comfyui_workflow_source_ref") or "").replace("\\", "/").lower()
    return "/workflows/zimage/amazing-z-" in source_ref


def _is_reference_guided_qwen_edit_workflow(job: dict[str, Any]) -> bool:
    source_ref = str(job.get("preferred_comfyui_workflow_source_ref") or "").replace("\\", "/").lower()
    return (
        "qwen-edit-2511-shortdrama-character-anchor-base.json" in source_ref
        or "qwenedit+nextscene" in source_ref
    )


def _contains_cjk(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text))


def _clean_prompt_fragment(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text.replace("\r", " ").replace("\n", " "))
    text = re.sub(r"(?i)^character identity anchor\s*:\s*", "", text)
    text = re.sub(r"(?i)^identity anchor\s*:\s*", "", text)
    text = re.sub(r"^同一人物设定[:：]\s*", "", text)
    text = re.sub(r"(?i)\bemotion remains\b", "emotion stays", text)
    text = re.sub(r"(?i)^emotion[:：]\s*", "", text)
    return text.strip(" ,，。;；")


def _clean_prompt_sentence(value: Any) -> str:
    text = _clean_prompt_fragment(value)
    if not text:
        return ""
    if _contains_cjk(text):
        pieces = [item.strip(" ，。;；") for item in re.split(r"\s*,\s*", text) if item.strip(" ，。;；")]
        if len(pieces) >= 2 and pieces[1].startswith(pieces[0]):
            pieces = pieces[1:]
        text = "，".join(pieces)
        text = re.sub(r"[。！？][，,]", "，", text)
        text = re.sub(r"([，。！？])\1+", r"\1", text)
    else:
        text = re.sub(r"\s*,\s*", ", ", text)
    return text


def _split_identity_anchor(value: Any) -> tuple[str, str]:
    identity = _clean_prompt_fragment(value)
    if not identity:
        return "", ""
    for sep in ("；", ";"):
        if sep in identity:
            description, continuity = identity.split(sep, 1)
            return description.strip(" ,，。;；"), continuity.strip(" ,，。;；")
    return identity, ""


def _append_unique_sentence(sentences: list[str], candidate: str) -> None:
    text = candidate.strip()
    if not text:
        return
    lowered = text.lower()
    if any(existing.lower() == lowered for existing in sentences):
        return
    sentences.append(text)


def _finish_sentence(text: str, *, cjk: bool) -> str:
    stripped = text.strip()
    if not stripped:
        return ""
    if stripped[-1] in ".!?。！？":
        return stripped
    return stripped + ("。" if cjk else ".")


def _is_qwen_nextscene_workflow(job: dict[str, Any]) -> bool:
    source_ref = str(job.get("preferred_comfyui_workflow_source_ref") or "").replace("\\", "/").lower()
    return "qwenedit+nextscene" in source_ref


def _qwen_prompt_is_already_composed(job: dict[str, Any], base_prompt: str) -> bool:
    if not _is_qwen_nextscene_workflow(job):
        return False
    if str(job.get("prompt_composition_mode") or "").strip().lower() != "zimage_skill_aligned":
        return False
    lowered = base_prompt.lower()
    return (
        "next scene" in lowered
        and ("镜头采用" in base_prompt or "full-frame" in lowered or "no black bars" in lowered)
    )


def _sanitize_qwen_nextscene_base_prompt(base_prompt: str) -> str:
    text = base_prompt.strip()
    if not text:
        return ""
    text = re.sub(
        r"(?i)([，, ]*)realistic cinematic short film([。.]*)",
        "",
        text,
    )
    text = re.sub(r"[，,]\s*[，,]", "，", text)
    text = re.sub(r"\s{2,}", " ", text)
    text = re.sub(r"[。！？]\s*[。！？]+", "。", text)
    return text.strip(" ,，。;；")


def _rewrite_qwen_continuity_fragment(text: str, *, cjk: bool) -> str:
    if not text:
        return text
    if cjk:
        text = text.replace("同一情绪气场", "基础表情、视线方向和动作节奏")
        text = text.replace("整体气质", "基础表情、视线方向和动作节奏")
    return text


def _rewrite_qwen_abstract_cjk_text(text: str) -> str:
    rewritten = text
    replacements = [
        ("像是在等海风把心事吹散", "海风吹动头发和裙摆，她继续慢慢往前走，不要夸张表情"),
        ("把心事留在身后", "不再回头，肩膀自然下沉，背部不再紧绷"),
        ("整个人终于轻下来", "肩膀比前一镜头更放松，步伐更稳定，呼吸更均匀"),
        ("海风把情绪一点点吹开", "海风吹动头发和裙摆，眉头慢慢放松，肩膀比前一镜头更放松"),
        ("呼吸和情绪都一点点慢下来", "呼吸节奏放慢，表情更安静，视线停在海平线"),
        ("呼吸和情绪一点点慢下来", "呼吸节奏放慢，表情更安静，视线停在海平线"),
        ("情绪慢慢沉下来", "表情更安静，嘴唇自然闭合，视线停在远处海平线"),
        ("情绪推进到安静停顿", "人物停下来不说话，视线停在海平线，表情安静"),
        ("情绪推进到安静观察", "人物继续看向前方海面，不说话，表情平静"),
        ("情绪推进到安静克制", "表情收住，嘴唇自然闭合，眉头不要夸张上扬"),
        ("情绪从克制转向松开", "眉头从轻微收住变为放松，嘴角不再绷紧，肩膀比前一镜头更放松"),
        ("情绪收束而释然", "表情平静，眉头舒展，肩膀放松，不再回头"),
        ("那点没说出口的情绪终于开始松开", "眉头慢慢放松，嘴角不再绷紧，肩膀和手臂比前一镜头更放松"),
        ("海面与晚霞继续呼吸", "海面反光、晚霞层次和海平线继续清楚可见"),
        ("表情安静克制、略带心事", "表情平静，嘴唇自然闭合，眉头轻微收住，视线稳定，不夸张微笑"),
        ("表情安静克制，略带心事", "表情平静，嘴唇自然闭合，眉头轻微收住，视线稳定，不夸张微笑"),
        ("安静克制、略带心事", "表情平静，嘴唇自然闭合，眉头轻微收住，视线稳定，不夸张微笑"),
        ("安静克制，略带心事", "表情平静，嘴唇自然闭合，眉头轻微收住，视线稳定，不夸张微笑"),
        ("表情安静克制", "表情平静，嘴唇自然闭合，眉头轻微收住"),
        ("安静克制", "表情平静，嘴唇自然闭合，眉头轻微收住"),
        ("略带心事", "眉头轻微收住，嘴角不要上扬，视线稳定"),
    ]
    for source, target in replacements:
        rewritten = rewritten.replace(source, target)
    rewritten = re.sub(r"情绪推进到([^\n，。]+)", r"表情和动作变化要直接表现为\1", rewritten)
    rewritten = re.sub(r"情绪落在([^\n，。]+)", r"表情和动作最后停在\1", rewritten)
    rewritten = re.sub(r"气场", "表情和动作状态", rewritten)
    return rewritten


def _rewrite_qwen_prompt_for_model_clarity(text: str, *, cjk: bool) -> str:
    if not text:
        return text
    if not cjk:
        return text
    rewritten = _rewrite_qwen_abstract_cjk_text(text)
    rewritten = re.sub(r"\s{2,}", " ", rewritten)
    rewritten = re.sub(r"([，。！？])\1+", r"\1", rewritten)
    return rewritten.strip(" ,，。;；")


def _qwen_concrete_performance_sentences(performance: str, emotion: str, *, cjk: bool) -> list[str]:
    if not cjk:
        return []
    lowered_performance = performance.lower()
    lowered_emotion = emotion.lower()
    sentences: list[str] = []
    if performance:
        if "慢" in performance or "轻" in performance or "克制" in performance:
            sentences.append("动作幅度要小，抬手、转身、迈步都放慢，停顿要清楚，不要大幅摆臂或夸张表情")
        if "呼吸" in performance:
            sentences.append("胸口起伏、肩膀放松和步伐节奏要能看出真实呼吸带来的轻微变化")
    if emotion:
        if "克制" in emotion or "restrained" in lowered_emotion:
            sentences.append("表情收住，嘴唇自然闭合，眉头不要夸张上扬")
        if "松开" in emotion or "释然" in emotion or "轻下来" in emotion:
            sentences.append("表情比前一镜头更放松，眉头舒展，肩膀自然下沉")
        if "安静" in emotion or "平静" in emotion:
            sentences.append("人物停顿或慢速动作时保持安静表情，视线稳定，不要夸张张嘴或大笑")
    return sentences


def _qwen_camera_reinforcement_sentences(camera: str, *, cjk: bool) -> list[str]:
    lowered = camera.lower()
    sentences: list[str] = []
    if "back view" in lowered:
        if cjk:
            sentences.append("人物不要正面看向镜头，镜头以后背或侧后方轮廓为主")
            sentences.append("必须是完整满幅画面，full-frame image, no black bars, no embedded border, no picture-in-picture frame")
            sentences.append("发型长度、裙摆轮廓和行走姿态都要清楚可读，不能只剩模糊背影")
        else:
            sentences.append("Do not show the subject facing the camera; keep the view on the back or rear three-quarter silhouette")
            sentences.append("Keep it as a full-frame image with no black bars, no embedded border, and no picture-in-picture frame")
            sentences.append("Keep the hair length, dress silhouette, and walking posture clearly readable instead of reducing the subject to an indistinct back silhouette")
    if "wide" in lowered or "establishing" in lowered:
        if cjk:
            sentences.append("人物在画面中保持较小比例，环境空间要比人物更突出")
            sentences.append("不要把画面拍成人像照或大半身构图，人物高度不要超过画面高度的三分之一，海岸线、天空和海面应占据主要画面")
        else:
            sentences.append("Keep the subject relatively small in frame so the environment reads more strongly than the portrait")
            sentences.append("Do not turn the frame into a portrait or medium-close composition; keep the subject under one third of the frame height and let the coastline, sky, and sea dominate the image")
    if "establishing" in lowered:
        if cjk:
            sentences.append("人物不要站在画面正中央成为主视觉，面部不能比环境更抢眼，应先读到海岸线、海面和天光，再读到人物")
        else:
            sentences.append("Do not place the subject as the central visual focus; the coastline, sea, and sky should read before the face or body")
    return sentences


def _qwen_output_guardrail_sentences(*, cjk: bool) -> list[str]:
    if cjk:
        return [
            "只输出单张完整画面，不要宫格、拼贴、多分镜格或 contact sheet",
            "不要出现黑边、假电影边框、内嵌相框或任何画中画布局",
        ]
    return [
        "Output one single full-frame cinematic frame only, not a collage, contact sheet, storyboard grid, or split-panel layout",
        "Do not introduce black bars, fake letterboxing, embedded frames, or any picture-in-picture layout",
    ]


def _original_zimage_scene_guardrails(job: dict[str, Any], *, cjk: bool) -> list[str]:
    route_key = str(job.get("stage05_route_key") or "").strip()
    camera_text = " ".join(
        str(job.get(key) or "")
        for key in ["camera_prompt", "prompt", "style_prompt", "consistency_prompt"]
    ).lower()
    sentences: list[str] = []
    if route_key == "realistic_cinematic" and (
        "establishing shot" in camera_text
        or ("wide shot" in camera_text and any(hint in camera_text for hint in ("shoreline", "beach", "sea", "street", "skyline")))
    ):
        if cjk:
            sentences.append("把它当成故事世界里的真实场景，不要拍成幕后花絮、摄影棚测试照或时尚棚拍，海岸线、天空和周围环境要清晰可见，人物在画面中不要过大")
        else:
            sentences.append("Treat this as an in-world story scene, not a behind-the-scenes still, studio setup, or fashion set; keep the coastline, sky, and surrounding environment clearly visible with the subject not oversized in frame")
    if cjk:
        sentences.append("不要出现摄影机、镜头、三脚架、监视器、灯架、boom 麦、剧组人员或任何片场设备，也不要有幕后拍摄感")
    else:
        sentences.append("Do not show cameras, lenses, tripods, monitors, lighting stands, boom mics, crew members, or any on-set equipment, and avoid any behind-the-scenes feeling")
    return sentences


def _build_original_zimage_prompt(job: dict[str, Any]) -> str:
    base_prompt = _clean_prompt_sentence(job.get("prompt"))
    identity_description, continuity = _split_identity_anchor(job.get("identity_anchor_prompt") or job.get("consistency_prompt"))
    camera = _clean_prompt_fragment(job.get("camera_prompt"))
    lighting = _clean_prompt_fragment(job.get("lighting_prompt"))
    style = _clean_prompt_fragment(job.get("style_prompt"))
    performance = _clean_prompt_fragment(job.get("performance_prompt"))
    story_anchor_bundle = job.get("story_anchor_bundle") if isinstance(job.get("story_anchor_bundle"), dict) else {}
    composition_focus = _clean_prompt_sentence(story_anchor_bundle.get("composition_focus"))
    emotion = _clean_prompt_fragment(story_anchor_bundle.get("emotion"))
    cjk = _contains_cjk(" ".join([
        base_prompt,
        identity_description,
        continuity,
        composition_focus,
        performance,
        emotion,
    ]))

    sentences: list[str] = []
    _append_unique_sentence(sentences, base_prompt)

    if identity_description:
        if cjk:
            _append_unique_sentence(sentences, f"画面主角始终是{identity_description}")
        else:
            _append_unique_sentence(sentences, f"The protagonist is always {identity_description}")

    if camera and composition_focus and composition_focus not in base_prompt:
        if cjk:
            _append_unique_sentence(sentences, f"镜头采用{camera}，{composition_focus}")
        else:
            _append_unique_sentence(sentences, f"Use a {camera} with framing that keeps {composition_focus}")
    elif camera:
        if cjk:
            _append_unique_sentence(sentences, f"镜头采用{camera}")
        else:
            _append_unique_sentence(sentences, f"Use a {camera}")
    elif composition_focus and composition_focus not in base_prompt:
        _append_unique_sentence(sentences, composition_focus)

    if performance:
        normalized_performance = performance.replace(" / ", "，" if cjk else ", ")
        if cjk:
            _append_unique_sentence(sentences, f"人物状态与动作保持{normalized_performance}")
        else:
            _append_unique_sentence(sentences, f"Keep the body language and performance {normalized_performance}")
    elif emotion:
        if cjk:
            _append_unique_sentence(sentences, f"人物情绪保持{emotion}")
        else:
            _append_unique_sentence(sentences, f"Keep the emotional tone {emotion}")

    if continuity:
        _append_unique_sentence(sentences, continuity)
    if lighting:
        if cjk:
            _append_unique_sentence(sentences, f"光线与环境氛围为{lighting}")
        else:
            _append_unique_sentence(sentences, f"Lighting and atmosphere: {lighting}")
    if style:
        if cjk:
            _append_unique_sentence(sentences, f"整体画面质感保持{style}")
        else:
            _append_unique_sentence(sentences, f"Keep the overall visual treatment {style}")

    for sentence in _original_zimage_scene_guardrails(job, cjk=cjk):
        _append_unique_sentence(sentences, sentence)

    return " ".join(_finish_sentence(sentence, cjk=cjk) for sentence in sentences if sentence).strip()


def _build_reference_guided_qwen_edit_prompt(job: dict[str, Any]) -> str:
    base_prompt = _clean_prompt_sentence(job.get("prompt"))
    identity_description, continuity = _split_identity_anchor(job.get("identity_anchor_prompt") or job.get("consistency_prompt"))
    camera = _clean_prompt_fragment(job.get("camera_prompt"))
    lighting = _clean_prompt_fragment(job.get("lighting_prompt"))
    style = _clean_prompt_fragment(job.get("style_prompt"))
    performance = _clean_prompt_fragment(job.get("performance_prompt"))
    story_anchor_bundle = job.get("story_anchor_bundle") if isinstance(job.get("story_anchor_bundle"), dict) else {}
    composition_focus = _clean_prompt_sentence(story_anchor_bundle.get("composition_focus"))
    emotion = _clean_prompt_fragment(story_anchor_bundle.get("emotion"))
    cjk = _contains_cjk(" ".join([
        base_prompt,
        identity_description,
        continuity,
        composition_focus,
        performance,
        emotion,
    ]))
    trust_base_prompt = _qwen_prompt_is_already_composed(job, base_prompt)
    if trust_base_prompt:
        base_prompt = _sanitize_qwen_nextscene_base_prompt(base_prompt)
    base_prompt = _rewrite_qwen_prompt_for_model_clarity(base_prompt, cjk=cjk)
    continuity = _rewrite_qwen_continuity_fragment(continuity, cjk=cjk)
    identity_description = _rewrite_qwen_prompt_for_model_clarity(identity_description, cjk=cjk)

    sentences: list[str] = []
    if cjk:
        _append_unique_sentence(sentences, "严格沿用参考图中的同一位主角，保持同一张脸、同一发型、同一条裙子的版型、领口、腰线和整体轮廓，不要换人，不要换衣服")
    else:
        _append_unique_sentence(sentences, "Use the exact same protagonist from the reference image, keeping the same face, hairstyle, and the same dress design, neckline, waistline, and silhouette; do not change the person or outfit")

    _append_unique_sentence(sentences, base_prompt)

    if identity_description:
        if cjk:
            _append_unique_sentence(sentences, f"主角始终是{identity_description}")
        else:
            _append_unique_sentence(sentences, f"The protagonist remains {identity_description}")

    for reinforcement in _qwen_camera_reinforcement_sentences(camera, cjk=cjk):
        _append_unique_sentence(sentences, reinforcement)

    if trust_base_prompt:
        pass
    elif camera and composition_focus and composition_focus not in base_prompt:
        if cjk:
            _append_unique_sentence(sentences, f"镜头采用{camera}，{composition_focus}")
        else:
            _append_unique_sentence(sentences, f"Use a {camera} with framing that keeps {composition_focus}")
    elif camera:
        if cjk:
            _append_unique_sentence(sentences, f"镜头采用{camera}")
        else:
            _append_unique_sentence(sentences, f"Use a {camera}")
    elif composition_focus and composition_focus not in base_prompt:
        _append_unique_sentence(sentences, composition_focus)

    if trust_base_prompt:
        pass
    elif performance:
        normalized_performance = performance.replace(" / ", "，" if cjk else ", ")
        if cjk:
            for sentence in _qwen_concrete_performance_sentences(normalized_performance, emotion, cjk=cjk):
                _append_unique_sentence(sentences, sentence)
        else:
            _append_unique_sentence(sentences, f"Keep the body language and performance {normalized_performance}")
    elif emotion:
        if cjk:
            for sentence in _qwen_concrete_performance_sentences("", emotion, cjk=cjk):
                _append_unique_sentence(sentences, sentence)
        else:
            _append_unique_sentence(sentences, f"Keep the emotional tone {emotion}")

    if continuity:
        _append_unique_sentence(sentences, continuity)
    if lighting and not trust_base_prompt:
        if cjk:
            _append_unique_sentence(sentences, f"光线与环境氛围为{lighting}")
        else:
            _append_unique_sentence(sentences, f"Lighting and atmosphere: {lighting}")
    if style and not trust_base_prompt:
        if cjk:
            _append_unique_sentence(sentences, f"整体画面质感保持{style}")
        else:
            _append_unique_sentence(sentences, f"Keep the overall visual treatment {style}")

    for sentence in _qwen_output_guardrail_sentences(cjk=cjk):
        _append_unique_sentence(sentences, sentence)

    if cjk:
        _append_unique_sentence(sentences, "只改变场景、机位、动作和表情变化，人物身份、服装主结构、基础表情、视线方向和动作节奏必须前后一致")
        _append_unique_sentence(sentences, "画面里不要出现多人，不要出现文字、水印、片场设备或任何破坏叙事连续性的元素")
    else:
        _append_unique_sentence(sentences, "Only change the scene, camera angle, action, and emotional progression while keeping the character identity, outfit structure, and overall presence stable")
        _append_unique_sentence(sentences, "Do not introduce extra people, text, watermarks, on-set equipment, or anything that breaks scene continuity")

    return " ".join(_finish_sentence(sentence, cjk=cjk) for sentence in sentences if sentence).strip()


def build_provider_prompt(job: dict[str, Any]) -> str:
    if _is_original_zimage_ui_workflow(job):
        # The original Amazing Zimage UI workflows expect #57 to contain only
        # the prompt text. Style switching must happen through #88.
        return _build_original_zimage_prompt(job)
    if _is_reference_guided_qwen_edit_workflow(job):
        return _build_reference_guided_qwen_edit_prompt(job)

    sections: list[str] = []
    base_prompt = str(job.get("prompt") or "").strip()
    if base_prompt:
        sections.append(base_prompt)
    route_intent = str(job.get("comfyui_style_positive_anchor") or "").strip()
    if route_intent:
        sections.append(f"Route intent: {route_intent}")
    include_style_section = True
    for label, key in [
        ("Style", "style_prompt"),
        ("Lighting", "lighting_prompt"),
        ("Consistency", "consistency_prompt"),
        ("Identity", "identity_anchor_prompt"),
        ("Camera", "camera_prompt"),
    ]:
        if key == "style_prompt" and not include_style_section:
            continue
        value = str(job.get(key) or "").strip()
        if value:
            sections.append(f"{label}: {value}")
    sections.extend(_prop_guardrail_sections(job))
    sections.extend(_route_guardrail_sections(job))
    for item in job.get("repair_prompt_sections") or []:
        if isinstance(item, str) and item.strip():
            sections.append(item.strip())
    negative = effective_negative_prompt(job)
    if negative:
        sections.append(f"Avoid: {negative}")
    return "\n".join(sections).strip()


def append_error(job: dict[str, Any], provider_name: str, message: str) -> None:
    job["status"] = "failed"
    job["provider"] = provider_name
    job.setdefault("errors", [])
    job["errors"].append({
        "type": "provider_error",
        "provider": provider_name,
        "message": message,
        "created_at": utc_now(),
    })
    job.setdefault("evidence", {})
    job["evidence"]["created_at"] = None


def missing_character_reference_block(job: dict[str, Any]) -> dict[str, Any] | None:
    gate = build_quality_gate(job)
    risk_tags = [str(tag).strip() for tag in (gate.get("risk_tags") or []) if str(tag).strip()]
    missing_reference_images = [
        str(item).replace("\\", "/")
        for item in (job.get("missing_reference_images") or [])
        if isinstance(item, str) and str(item).strip()
    ]
    if "missing_character_reference" not in risk_tags or not missing_reference_images:
        return None
    return {
        "image_id": str(job.get("image_id") or "").strip() or None,
        "shot_id": str(job.get("shot_id") or "").strip() or None,
        "frame_role": str(job.get("frame_role") or "").strip() or None,
        "risk_tags": risk_tags,
        "reason": (
            "Blocked before generation: this character-locked high-risk shot is missing a Stage 03 reference image, "
            "so prompt-only Stage 05 generation would likely drift into a different person."
        ),
        "creator_summary": "当前镜头缺少角色参考图，继续生图最容易出现 start / mid / end 不是同一个人。",
        "missing_reference_images": missing_reference_images,
        "reference_images": [
            str(item).replace("\\", "/")
            for item in (job.get("reference_images") or [])
            if isinstance(item, str) and str(item).strip()
        ],
        "recovery_steps": [
            "先补齐 Stage 03 角色参考图，再重跑当前关键帧。",
            "至少提供主角正向清晰参考图，保证脸型、发型、服装轮廓和主要随身物跨帧固定。",
            "补图后优先重跑 start / mid / end 全套关键帧，再人工横向核对是不是同一个人。",
        ],
    }


def append_blocked(
    job: dict[str, Any],
    provider_name: str,
    message: str,
    *,
    error_type: str = "preflight_blocked",
    details: dict[str, Any] | None = None,
) -> None:
    job["status"] = "blocked"
    job["provider"] = provider_name
    job.setdefault("errors", [])
    job["errors"].append({
        "type": error_type,
        "provider": provider_name,
        "message": message,
        "details": details or {},
        "created_at": utc_now(),
    })
    job.setdefault("evidence", {})
    job["evidence"].update({
        "file_exists": False,
        "file_size_bytes": 0,
        "created_at": None,
    })
    job["notes"] = message


def _sync_stage05_manifest_command(manifest_path: Path) -> str:
    plugin_root = plugin_root_for_manifest(manifest_path)
    runner = (
        plugin_root / "skills" / "video-keyframe-images" / "scripts" / "sync_keyframe_image_manifest.py"
        if plugin_root
        else Path("plugins/codex-video-pipeline-plugin/skills/video-keyframe-images/scripts/sync_keyframe_image_manifest.py")
    )
    runner_text = str(runner.resolve() if isinstance(runner, Path) and runner.is_absolute() else runner).replace("\\", "/")
    manifest_text = str(manifest_path.resolve()).replace("\\", "/")
    return f"python {runner_text} {manifest_text}"


def _reference_bootstrap_command(manifest_path: Path) -> str:
    plugin_root = plugin_root_for_manifest(manifest_path)
    runner = (
        plugin_root / "skills" / "video-keyframe-images" / "scripts" / "run_stage05_reference_bootstrap.py"
        if plugin_root
        else Path("plugins/codex-video-pipeline-plugin/skills/video-keyframe-images/scripts/run_stage05_reference_bootstrap.py")
    )
    runner_text = str(runner.resolve() if isinstance(runner, Path) and runner.is_absolute() else runner).replace("\\", "/")
    manifest_text = str(manifest_path.resolve()).replace("\\", "/")
    return f"python {runner_text} {manifest_text}"


def reference_bootstrap_candidates(
    manifest_path: Path,
    *,
    missing_reference_images: list[str],
) -> list[dict[str, Any]]:
    data = load_json(manifest_path)
    jobs = data.get("jobs") if isinstance(data.get("jobs"), list) else []
    missing_set = {
        str(item).replace("\\", "/")
        for item in missing_reference_images
        if isinstance(item, str) and str(item).strip()
    }
    candidates: list[dict[str, Any]] = []
    review_rank = {
        "approved": 220,
        "not_required": 180,
        "pending": 80,
    }
    frame_rank = {
        "start": 30,
        "end": 20,
        "mid": 10,
    }
    for job in jobs:
        if not isinstance(job, dict):
            continue
        reference_images = {
            str(item).replace("\\", "/")
            for item in (job.get("reference_images") or [])
            if isinstance(item, str) and str(item).strip()
        }
        matched_targets = sorted(reference_images & missing_set)
        if not matched_targets:
            continue
        output_raw = job.get("evidence", {}).get("file_path") or job.get("output_path")
        if not output_raw:
            continue
        output_path = resolve_path(manifest_path, output_raw)
        if not output_path.exists() or not output_path.is_file() or output_path.stat().st_size <= 0:
            continue
        gate = job.get("quality_gate") if isinstance(job.get("quality_gate"), dict) else {}
        risk_tags = {
            str(tag).strip()
            for tag in (gate.get("risk_tags") or [])
            if str(tag).strip()
        }
        score = 1000
        score += review_rank.get(str(gate.get("manual_review_status") or "").strip(), 0)
        score += frame_rank.get(str(job.get("frame_role") or "").strip(), 0)
        if "umbrella_prop_contact" not in risk_tags:
            score += 40
        if "missing_character_reference" not in risk_tags:
            score += 20
        candidates.append({
            "image_id": str(job.get("image_id") or "").strip() or None,
            "shot_id": str(job.get("shot_id") or "").strip() or None,
            "frame_role": str(job.get("frame_role") or "").strip() or None,
            "source_path": str(output_path).replace("\\", "/"),
            "target_reference_paths": matched_targets,
            "score": score,
        })
    candidates.sort(
        key=lambda item: (
            -int(item.get("score") or 0),
            str(item.get("shot_id") or ""),
            str(item.get("frame_role") or ""),
            str(item.get("image_id") or ""),
        )
    )
    return candidates


def build_missing_reference_manual_recovery(manifest_path: Path, blocked_jobs: list[dict[str, Any]]) -> dict[str, Any]:
    keyframes_dir = manifest_path.parent / "keyframes"
    keyframes_dir_text = str(keyframes_dir).replace("\\", "/")
    missing_paths: list[str] = []
    blocked_image_ids: list[str] = []
    for item in blocked_jobs:
        blocked_image_ids.append(str(item.get("image_id") or ""))
        for path_text in item.get("missing_reference_images") or []:
            normalized = str(path_text).replace("\\", "/")
            if normalized not in missing_paths:
                missing_paths.append(normalized)
    suggested_command = None
    if missing_paths:
        suggested_command = _reference_bootstrap_command(manifest_path)
    steps = [
        "1. 先执行 Stage05-A，按 Stage03 人物设定生成主角参考图。",
        f"2. 缺失参考图最终需要回填到这些路径：{', '.join(missing_paths) if missing_paths else '03_characters/reference_images/...'}。",
    ]
    if suggested_command:
        steps.append(f"3. 推荐直接执行：`{suggested_command}`。")
        steps.append("4. 这会按当前项目的风格路由选择合适的 Zimage 工作流，生成主参考图并回填 Stage03。")
        steps.append("5. 回填成功后重新生成 Stage05-B manifest，再执行 Qwen NextScene 一致性分镜图生成。")
    else:
        steps.append("3. 补图后重新运行当前 Stage05-B 执行器，并横向核对 start / mid / end 是否为同一人物。")
    steps.append(f"6. 如需人工兜底，也请把修正后的关键帧放到 {keyframes_dir_text} 后再执行 `{_sync_stage05_manifest_command(manifest_path)}`。")
    return {
        "status": "required",
        "reason": "Stage05-B 缺少 Stage03 主角色参考图，已阻断 reference-guided 一致性分镜生成。",
        "blocked_image_ids": blocked_image_ids,
        "missing_reference_images": missing_paths,
        "suggested_bootstrap_command": suggested_command,
        "steps": steps,
        "created_at": utc_now(),
    }


def _review_queue_markdown_lines(data: dict[str, Any], manifest_path: Path | None = None) -> list[str]:
    quality_review = data.get("quality_review") if isinstance(data.get("quality_review"), dict) else {}
    queue = quality_review.get("review_queue") if isinstance(quality_review.get("review_queue"), list) else []
    runtime = data.get("creator_runtime_status") if isinstance(data.get("creator_runtime_status"), dict) else {}
    manual_recovery = data.get("manual_recovery") if isinstance(data.get("manual_recovery"), dict) else {}
    lines = [
        "# Stage 05 Manual Review",
        "",
        f"- 项目：`{data.get('project_id')}`",
        f"- 当前状态：`{data.get('status')}`",
        f"- 高风险图片数：{quality_review.get('risky_image_count', 0)}",
        f"- 待人工复核数：{quality_review.get('pending_count', 0)}",
        f"- 可直接进入 Stage 06：`{'yes' if data.get('self_check', {}).get('ready_for_video_clip_generation') else 'no'}`",
        "",
    ]
    if runtime.get("headline"):
        lines.extend([
            "## 运行提示",
            "",
            f"- {runtime.get('headline')}",
        ])
        if runtime.get("detail"):
            lines.append(f"- {runtime.get('detail')}")
        if runtime.get("review_headline"):
            lines.append(f"- {runtime.get('review_headline')}")
        lines.append("")
    bootstrap_command = str(manual_recovery.get("suggested_bootstrap_command") or "").strip()
    if bootstrap_command:
        lines.extend([
            "## 先跑 Stage05-A",
            "",
            f"- 推荐先执行：`{bootstrap_command}`",
            "- 这会根据 Stage03 人物设定和当前风格路由生成主角色参考图，并自动回填 Stage03。",
            "",
        ])
    if not queue:
        lines.extend([
            "## 复核结论",
            "",
            "当前没有高风险镜头，按常规抽查关键帧即可。",
            "",
        ])
        return lines
    next_ids = quality_review.get("next_review_image_ids") if isinstance(quality_review.get("next_review_image_ids"), list) else []
    if next_ids:
        lines.extend([
            "## 建议先看",
            "",
            "- " + " -> ".join(f"`{item}`" for item in next_ids if str(item).strip()),
            "",
        ])
    if manifest_path is not None:
        lines.extend([
            "## 看完后的推进",
            "",
            f"- 如果想用本地可点击工作台，先启动：`{_workbench_payload(data, manifest_path).get('quick_actions', {}).get('serve_workbench_command')}`",
            f"- 这批图确认可用后，可先执行：`{_approve_command_for_manifest(manifest_path, top=min(3, max(1, len(next_ids) or 1)))}`",
            "- 批准时必须补上 `--content-aligned --content-alignment-note \"...\"`，明确确认图片内容与镜头文字描述一致。",
            "- 如果只想放行单张，也可以改成 `--image-id IMG_...`。",
            "",
        ])
    top_cards = quality_review.get("top_review_cards") if isinstance(quality_review.get("top_review_cards"), list) else []
    if top_cards:
        lines.extend([
            "## Top 3 快速问题卡",
            "",
        ])
        for card in top_cards:
            if not isinstance(card, dict):
                continue
            image_id = str(card.get("image_id") or "").strip() or "unknown"
            shot_id = str(card.get("shot_id") or "").strip() or "-"
            frame_role = str(card.get("frame_role") or "").strip() or "-"
            lines.append(f"### #{card.get('rank') or '-'} {image_id}")
            lines.append("")
            lines.append(f"- 镜头：`{shot_id}` / `{frame_role}`")
            lines.append(f"- 为什么先看：{card.get('headline') or '高风险镜头'}")
            if card.get("first_check"):
                lines.append(f"- 第一检查点：{card.get('first_check')}")
            if card.get("quick_fix"):
                lines.append(f"- 第一改法：{card.get('quick_fix')}")
            lines.append("")
    lines.extend([
        "## 复核队列",
        "",
    ])
    for item in queue:
        if not isinstance(item, dict):
            continue
        image_id = str(item.get("image_id") or "").strip() or "unknown"
        shot_id = str(item.get("shot_id") or "").strip() or "-"
        frame_role = str(item.get("frame_role") or "").strip() or "-"
        lines.append(f"### {image_id}")
        lines.append("")
        lines.append(f"- 镜头：`{shot_id}` / `{frame_role}`")
        lines.append(f"- 优先级：{item.get('priority_label') or '待定'} ({item.get('priority_score') or 0})")
        if item.get("risk_summary"):
            lines.append(f"- 风险摘要：{item.get('risk_summary')}")
        if item.get("review_focus"):
            lines.append(f"- 先看什么：{item.get('review_focus')}")
        card = None
        jobs = data.get("jobs") if isinstance(data.get("jobs"), list) else []
        for job in jobs:
            if isinstance(job, dict) and str(job.get("image_id") or "").strip() == image_id:
                card = job.get("creator_review_card") if isinstance(job.get("creator_review_card"), dict) else None
                preview = str(job.get("repair_preview_path") or "").strip()
                output = str(job.get("evidence", {}).get("file_path") or job.get("output_path") or "").strip()
                blocked_note = str(job.get("notes") or "").strip() if str(job.get("status") or "").strip() == "blocked" else ""
                if output:
                    lines.append(f"- 当前结果：`{output}`")
                if preview:
                    lines.append(f"- 一修前预检：`{preview}`")
                if blocked_note:
                    lines.append(f"- 当前阻断：{blocked_note}")
                break
        checklist = item.get("checklist") if isinstance(item.get("checklist"), list) else []
        if checklist:
            lines.append("- 复核清单：")
            for check in checklist[:3]:
                lines.append(f"  - {check}")
        suggestions = []
        if isinstance(card, dict) and isinstance(card.get("suggestions"), list):
            suggestions = [str(s).strip() for s in card["suggestions"] if str(s).strip()]
        if suggestions:
            lines.append("- 改法建议：")
            for suggestion in suggestions[:3]:
                lines.append(f"  - {suggestion}")
        if isinstance(card, dict) and card.get("next_step"):
            lines.append(f"- 下一步：{card.get('next_step')}")
        lines.append("")
    return lines


def _job_by_image_id(data: dict[str, Any], image_id: str) -> dict[str, Any] | None:
    jobs = data.get("jobs") if isinstance(data.get("jobs"), list) else []
    for job in jobs:
        if isinstance(job, dict) and str(job.get("image_id") or "").strip() == image_id:
            return job
    return None


def _rerun_command_for_image(manifest_path: Path, image_id: str) -> str:
    plugin_root = plugin_root_for_manifest(manifest_path)
    runner = (
        plugin_root / "skills" / "video-keyframe-images" / "scripts" / "auto_repair_stage05_review_queue.py"
        if plugin_root
        else Path("plugins/codex-video-pipeline-plugin/skills/video-keyframe-images/scripts/auto_repair_stage05_review_queue.py")
    )
    runner_text = str(runner.resolve() if isinstance(runner, Path) and runner.is_absolute() else runner).replace("\\", "/")
    manifest_text = str(manifest_path.resolve()).replace("\\", "/")
    return f"python {runner_text} {manifest_text} --image-id {image_id}"


def _approve_command_for_manifest(manifest_path: Path, *, top: int = 1) -> str:
    plugin_root = plugin_root_for_manifest(manifest_path)
    runner = plugin_root / "skills" / "video-keyframe-images" / "scripts" / "approve_stage05_review_queue.py" if plugin_root else Path("plugins/codex-video-pipeline-plugin/skills/video-keyframe-images/scripts/approve_stage05_review_queue.py")
    runner_text = str(runner.resolve() if isinstance(runner, Path) and runner.is_absolute() else runner).replace("\\", "/")
    manifest_text = str(manifest_path.resolve()).replace("\\", "/")
    return (
        f'python {runner_text} {manifest_text} --top {max(1, top)} '
        '--content-aligned --content-alignment-note "confirmed content matches shot description"'
    )


def _auto_repair_command_for_manifest(manifest_path: Path, *, image_id: str | None = None, top: int | None = None) -> str:
    plugin_root = plugin_root_for_manifest(manifest_path)
    runner = (
        plugin_root / "skills" / "video-keyframe-images" / "scripts" / "auto_repair_stage05_review_queue.py"
        if plugin_root
        else Path("plugins/codex-video-pipeline-plugin/skills/video-keyframe-images/scripts/auto_repair_stage05_review_queue.py")
    )
    runner_text = str(runner.resolve() if isinstance(runner, Path) and runner.is_absolute() else runner).replace("\\", "/")
    manifest_text = str(manifest_path.resolve()).replace("\\", "/")
    command = f"python {runner_text} {manifest_text}"
    if image_id:
        command += f" --image-id {image_id}"
    elif top is not None:
        command += f" --limit {max(1, top)}"
    return command


def _path_to_uri(raw_path: str | None) -> str | None:
    if not raw_path:
        return None
    try:
        return Path(raw_path).resolve().as_uri()
    except ValueError:
        return None


def _workbench_payload(data: dict[str, Any], manifest_path: Path) -> dict[str, Any]:
    quality_review = data.get("quality_review") if isinstance(data.get("quality_review"), dict) else {}
    review_queue = quality_review.get("review_queue") if isinstance(quality_review.get("review_queue"), list) else []
    runtime = data.get("creator_runtime_status") if isinstance(data.get("creator_runtime_status"), dict) else {}
    provider_decisions = data.get("provider_decisions") if isinstance(data.get("provider_decisions"), list) else []
    top_cards = quality_review.get("top_review_cards") if isinstance(quality_review.get("top_review_cards"), list) else []
    top_limit = min(3, max(1, len(top_cards) or len(review_queue) or 1))
    plugin_root = plugin_root_for_manifest(manifest_path)
    manifest_path_text = str(manifest_path.resolve()).replace("\\", "/")
    if plugin_root:
        serve_script = (plugin_root / "skills" / "video-keyframe-images" / "scripts" / "serve_stage05_review_workbench.py").resolve()
        serve_script_text = str(serve_script).replace("\\", "/")
        serve_workbench_command = f"python {serve_script_text} {manifest_path_text}"
    else:
        serve_workbench_command = (
            "python plugins/codex-video-pipeline-plugin/skills/video-keyframe-images/scripts/serve_stage05_review_workbench.py "
            + manifest_path_text
        )

    cards: list[dict[str, Any]] = []
    for item in review_queue:
        if not isinstance(item, dict):
            continue
        image_id = str(item.get("image_id") or "").strip()
        if not image_id:
            continue
        job = _job_by_image_id(data, image_id)
        if not isinstance(job, dict):
            continue
        evidence_path = str(job.get("evidence", {}).get("file_path") or job.get("output_path") or "").strip()
        preview_path = str(job.get("repair_preview_path") or "").strip() or None
        creator_review_card = job.get("creator_review_card") if isinstance(job.get("creator_review_card"), dict) else {}
        cards.append({
            "image_id": image_id,
            "shot_id": str(job.get("shot_id") or "").strip() or None,
            "frame_role": str(job.get("frame_role") or "").strip() or None,
            "priority_label": item.get("priority_label"),
            "priority_score": item.get("priority_score"),
            "risk_summary": item.get("risk_summary"),
            "review_focus": item.get("review_focus"),
            "checklist": list(item.get("checklist") or []),
            "suggestions": list(creator_review_card.get("suggestions") or item.get("suggestions") or []),
            "manual_review_status": item.get("manual_review_status"),
            "auto_repair_status": job.get("auto_repair_status"),
            "result_image_path": evidence_path or None,
            "result_image_uri": _path_to_uri(evidence_path),
            "repair_preview_path": preview_path,
            "repair_preview_uri": _path_to_uri(preview_path),
            "approve_command": _approve_command_for_manifest(manifest_path, top=1).replace("--top 1", f"--image-id {image_id}"),
            "auto_repair_command": _auto_repair_command_for_manifest(manifest_path, image_id=image_id),
            "sync_command": _sync_stage05_manifest_command(manifest_path),
        })

    return {
        "project_id": data.get("project_id"),
        "manifest_path": str(manifest_path.resolve()).replace("\\", "/"),
        "generated_at": utc_now(),
        "status": data.get("status"),
        "summary": data.get("summary") if isinstance(data.get("summary"), dict) else {},
        "self_check": data.get("self_check") if isinstance(data.get("self_check"), dict) else {},
        "quality_review": quality_review,
        "creator_runtime_status": runtime,
        "provider_decisions": provider_decisions[-5:],
        "quick_actions": {
            "approve_top_command": _approve_command_for_manifest(manifest_path, top=top_limit),
            "auto_repair_top_command": _auto_repair_command_for_manifest(manifest_path, top=top_limit),
            "sync_manifest_command": _sync_stage05_manifest_command(manifest_path),
            "serve_workbench_command": serve_workbench_command,
            "manual_review_markdown_path": str((manifest_path.parent / "manual_review.md").resolve()).replace("\\", "/"),
            "prompt_patch_plan_path": str((manifest_path.parent / "prompt_patch_plan.json").resolve()).replace("\\", "/"),
        },
        "top_review_cards": top_cards,
        "cards": cards,
    }


def _workbench_html(payload: dict[str, Any]) -> str:
    runtime = payload.get("creator_runtime_status") if isinstance(payload.get("creator_runtime_status"), dict) else {}
    quality_review = payload.get("quality_review") if isinstance(payload.get("quality_review"), dict) else {}
    quick_actions = payload.get("quick_actions") if isinstance(payload.get("quick_actions"), dict) else {}
    cards = payload.get("cards") if isinstance(payload.get("cards"), list) else []

    def _copy_button(command: str, label: str) -> str:
        encoded = json.dumps(command, ensure_ascii=False)
        return f"<button class=\"btn secondary\" type=\"button\" onclick='copyCommand({encoded})'>{html.escape(label)}</button>"

    def _action_button(action: str, image_id: str | None, command: str, label: str, *, secondary: bool = False) -> str:
        action_text = json.dumps(action, ensure_ascii=False)
        image_text = json.dumps(image_id, ensure_ascii=False)
        command_text = json.dumps(command, ensure_ascii=False)
        css_class = "btn secondary" if secondary else "btn"
        return (
            f"<button class=\"{css_class}\" type=\"button\" "
            f"onclick='runWorkbenchAction({action_text}, {image_text}, {command_text})'>{html.escape(label)}</button>"
        )

    card_html: list[str] = []
    for card in cards:
        if not isinstance(card, dict):
            continue
        image_uri = str(card.get("result_image_uri") or "").strip()
        image_path = str(card.get("result_image_path") or "").strip()
        preview_uri = str(card.get("repair_preview_uri") or "").strip()
        preview_block = ""
        if preview_uri:
            preview_block = f"""
            <div class="preview-stack">
              <div class="preview-label">一修前预检</div>
              <a href="{html.escape(preview_uri)}" data-local-path="{html.escape(str(card.get('repair_preview_path') or ''))}" target="_blank" rel="noreferrer">
                <img src="{html.escape(preview_uri)}" data-local-path="{html.escape(str(card.get('repair_preview_path') or ''))}" alt="{html.escape(str(card.get('image_id') or 'preview'))}" />
              </a>
            </div>
            """
        checklist = "".join(f"<li>{html.escape(str(item))}</li>" for item in (card.get("checklist") or []))
        suggestions = "".join(f"<li>{html.escape(str(item))}</li>" for item in (card.get("suggestions") or []))
        approve_command = str(card.get("approve_command") or "").strip()
        auto_repair_command = str(card.get("auto_repair_command") or "").strip()
        sync_command = str(card.get("sync_command") or "").strip()
        card_html.append(
            f"""
            <section class="card">
              <div class="visual">
                <div class="preview-stack">
                  <div class="preview-label">当前关键帧</div>
                  <a href="{html.escape(image_uri or '#')}" data-local-path="{html.escape(image_path)}" target="_blank" rel="noreferrer">
                    <img src="{html.escape(image_uri or '')}" data-local-path="{html.escape(image_path)}" alt="{html.escape(str(card.get('image_id') or 'image'))}" />
                  </a>
                </div>
                {preview_block}
              </div>
              <div class="meta">
                <div class="meta-top">
                  <h2>{html.escape(str(card.get("image_id") or ""))}</h2>
                  <span class="badge">{html.escape(str(card.get("priority_label") or "待复核"))}</span>
                </div>
                <p class="muted">镜头：{html.escape(str(card.get("shot_id") or "-"))} / {html.escape(str(card.get("frame_role") or "-"))}</p>
                <p class="summary">{html.escape(str(card.get("risk_summary") or ""))}</p>
                <p><strong>先看什么：</strong>{html.escape(str(card.get("review_focus") or ""))}</p>
                <p><strong>当前状态：</strong>manual={html.escape(str(card.get("manual_review_status") or "-"))}，repair={html.escape(str(card.get("auto_repair_status") or "not_started"))}</p>
                <p><strong>图片路径：</strong><code>{html.escape(image_path)}</code></p>
                <div class="grid">
                  <div>
                    <h3>复核清单</h3>
                    <ul>{checklist or '<li>暂无</li>'}</ul>
                  </div>
                  <div>
                    <h3>修正建议</h3>
                    <ul>{suggestions or '<li>暂无</li>'}</ul>
                  </div>
                </div>
                <div class="actions">
                  <a class="btn" href="{html.escape(image_uri or '#')}" target="_blank" rel="noreferrer">查看原图</a>
                  {_action_button("auto_repair_image", str(card.get("image_id") or "").strip() or None, auto_repair_command, "执行自动二修")}
                  {_action_button("approve_image", str(card.get("image_id") or "").strip() or None, approve_command, "通过当前镜头", secondary=True)}
                  {_copy_button(auto_repair_command, "复制命令")}
                </div>
                <div class="cmd-block">
                  <div class="cmd-label">自动二修</div>
                  <pre>{html.escape(auto_repair_command)}</pre>
                </div>
                <div class="cmd-block">
                  <div class="cmd-label">通过当前镜头</div>
                  <pre>{html.escape(approve_command)}</pre>
                </div>
                <div class="cmd-block">
                  <div class="cmd-label">刷新 manifest</div>
                  <pre>{html.escape(sync_command)}</pre>
                </div>
              </div>
            </section>
            """
        )

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Stage 05 审图工作台 - {html.escape(str(payload.get("project_id") or ""))}</title>
  <style>
    :root {{
      --bg: #f4efe7;
      --panel: #fffaf4;
      --panel-2: #ffffff;
      --ink: #2d241f;
      --muted: #6e6057;
      --accent: #b74f2f;
      --accent-soft: #f3d8cd;
      --line: #e7d8cb;
      --shadow: 0 16px 40px rgba(77, 53, 38, 0.10);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", "Microsoft YaHei UI", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, #f8e9d7 0, transparent 26%),
        radial-gradient(circle at top right, #e7f0f8 0, transparent 24%),
        linear-gradient(180deg, #f7f1ea 0%, #efe6db 100%);
    }}
    .shell {{
      max-width: 1280px;
      margin: 0 auto;
      padding: 32px 20px 56px;
    }}
    .hero, .toolbar, .card {{
      background: rgba(255, 250, 244, 0.92);
      border: 1px solid var(--line);
      border-radius: 24px;
      box-shadow: var(--shadow);
    }}
    .hero {{
      padding: 28px;
      margin-bottom: 20px;
    }}
    .hero h1 {{
      margin: 0 0 10px;
      font-size: 32px;
      line-height: 1.1;
    }}
    .hero p {{
      margin: 0 0 12px;
      color: var(--muted);
      font-size: 16px;
    }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
      margin-top: 18px;
    }}
    .stat {{
      padding: 16px;
      border-radius: 18px;
      background: var(--panel-2);
      border: 1px solid var(--line);
    }}
    .stat strong {{
      display: block;
      font-size: 26px;
      margin-bottom: 6px;
    }}
    .toolbar {{
      padding: 20px;
      margin-bottom: 20px;
    }}
    .toolbar-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 16px;
      align-items: start;
    }}
    .toolbar pre, .cmd-block pre {{
      margin: 10px 0 0;
      padding: 12px 14px;
      border-radius: 16px;
      background: #241d18;
      color: #fff6ef;
      overflow-x: auto;
      white-space: pre-wrap;
      word-break: break-word;
    }}
    .card {{
      display: grid;
      grid-template-columns: minmax(280px, 420px) minmax(0, 1fr);
      gap: 20px;
      padding: 20px;
      margin-bottom: 18px;
    }}
    .visual {{
      display: grid;
      gap: 12px;
      align-content: start;
    }}
    .preview-stack {{
      border: 1px solid var(--line);
      border-radius: 18px;
      overflow: hidden;
      background: #f7eee4;
    }}
    .preview-label {{
      padding: 10px 14px;
      font-size: 13px;
      color: var(--muted);
      border-bottom: 1px solid var(--line);
      background: rgba(255,255,255,0.8);
    }}
    img {{
      display: block;
      width: 100%;
      height: auto;
      background: #eadfd3;
    }}
    .meta-top {{
      display: flex;
      gap: 10px;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
    }}
    .meta h2 {{
      margin: 0;
      font-size: 24px;
    }}
    .badge {{
      display: inline-flex;
      align-items: center;
      padding: 8px 12px;
      border-radius: 999px;
      background: var(--accent-soft);
      color: var(--accent);
      font-size: 13px;
      font-weight: 600;
    }}
    .muted, .summary {{
      color: var(--muted);
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 16px;
      margin: 16px 0;
    }}
    .grid h3, .cmd-label {{
      margin: 0 0 8px;
      font-size: 15px;
    }}
    ul {{
      margin: 0;
      padding-left: 18px;
      color: var(--ink);
    }}
    li {{
      margin-bottom: 8px;
    }}
    .actions {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin: 18px 0 10px;
    }}
    .btn {{
      appearance: none;
      border: 0;
      cursor: pointer;
      text-decoration: none;
      padding: 12px 16px;
      border-radius: 999px;
      font-weight: 600;
      background: var(--accent);
      color: white;
    }}
    .btn.secondary {{
      background: #fff0e7;
      color: var(--accent);
      border: 1px solid #edc4b2;
    }}
    .empty {{
      padding: 30px;
      border-radius: 24px;
      background: rgba(255,255,255,0.82);
      border: 1px dashed var(--line);
      color: var(--muted);
      text-align: center;
    }}
    .toast {{
      position: fixed;
      right: 16px;
      bottom: 16px;
      background: #241d18;
      color: white;
      padding: 12px 14px;
      border-radius: 14px;
      opacity: 0;
      transform: translateY(10px);
      transition: opacity .2s ease, transform .2s ease;
      pointer-events: none;
    }}
    .toast.show {{
      opacity: 1;
      transform: translateY(0);
    }}
    @media (max-width: 920px) {{
      .card {{ grid-template-columns: 1fr; }}
      .hero h1 {{ font-size: 28px; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <h1>Stage 05 审图工作台</h1>
      <p>只保留创作者最关心的信息：先看哪张、哪里最危险、如果不对该怎么重修。</p>
      <p>{html.escape(str(runtime.get("headline") or "当前关键帧已生成，等待人工复核。"))}</p>
      <p>{html.escape(str(runtime.get("detail") or ""))}</p>
      <div class="stats">
        <div class="stat"><strong>{html.escape(str(quality_review.get("pending_count", 0)))}</strong><span>待人工复核</span></div>
        <div class="stat"><strong>{html.escape(str(quality_review.get("risky_image_count", 0)))}</strong><span>高风险镜头</span></div>
        <div class="stat"><strong>{html.escape(str((payload.get("summary") or {{}}).get("generated_image_count", 0)))}</strong><span>已生成关键帧</span></div>
        <div class="stat"><strong>{html.escape('yes' if (payload.get('self_check') or {{}}).get('ready_for_video_clip_generation') else 'no')}</strong><span>可进入 Stage 06</span></div>
      </div>
    </section>

    <section class="toolbar">
      <div class="toolbar-grid">
        <div>
          <h2>一键推进</h2>
          <p class="muted">看完没问题时，直接放行当前 top 队列。</p>
          <div class="actions">
            {_action_button("approve_top", None, str(quick_actions.get("approve_top_command") or ""), "直接通过 Top 队列", secondary=True)}
          </div>
          <pre>{html.escape(str(quick_actions.get("approve_top_command") or ""))}</pre>
        </div>
        <div>
          <h2>自动二修入口</h2>
          <p class="muted">看出明显问题时，优先走 provider-aware 自动二修，而不是手动翻 runner。</p>
          <div class="actions">
            {_action_button("auto_repair_top", None, str(quick_actions.get("auto_repair_top_command") or ""), "执行 Top 队列自动二修")}
          </div>
          <pre>{html.escape(str(quick_actions.get("auto_repair_top_command") or ""))}</pre>
        </div>
        <div>
          <h2>刷新状态</h2>
          <p class="muted">人工替换图片后，用它回写 evidence 和复核状态。</p>
          <div class="actions">
            {_action_button("sync_manifest", None, str(quick_actions.get("sync_manifest_command") or ""), "刷新当前工作台", secondary=True)}
          </div>
          <pre>{html.escape(str(quick_actions.get("sync_manifest_command") or ""))}</pre>
        </div>
      </div>
      <div class="toolbar-grid" style="margin-top:16px;">
        <div>
          <h2>本地工作台服务</h2>
          <p class="muted">如果你希望按钮直接可点生效，而不是只复制命令，先启动这个本地服务入口。</p>
          <pre>{html.escape(str(quick_actions.get("serve_workbench_command") or ""))}</pre>
        </div>
      </div>
    </section>

    {"".join(card_html) if card_html else '<section class="empty">当前没有待复核高风险镜头，可以按常规抽查后继续推进。</section>'}
  </div>
  <div class="toast" id="toast">命令已复制</div>
  <script>
    function localApiUrl(path, localPath) {{
      const encoded = encodeURIComponent(localPath || "");
      return `${{path}}?path=${{encoded}}`;
    }}

    function rewriteLocalFileLinks() {{
      if (!window.location.protocol.startsWith("http")) {{
        return;
      }}
      document.querySelectorAll("[data-local-path]").forEach((node) => {{
        const localPath = node.getAttribute("data-local-path");
        if (!localPath) {{
          return;
        }}
        const targetUrl = localApiUrl("/api/file", localPath);
        if (node.tagName === "IMG") {{
          node.src = targetUrl;
        }} else if (node.tagName === "A") {{
          node.href = targetUrl;
        }}
      }});
    }}

    function showToast(text) {{
      const toast = document.getElementById("toast");
      toast.textContent = text;
      toast.classList.add("show");
      setTimeout(() => toast.classList.remove("show"), 1600);
    }}

    async function copyCommand(text) {{
      try {{
        await navigator.clipboard.writeText(text);
        showToast("命令已复制");
      }} catch (err) {{
        window.prompt("复制下面这条命令：", text);
      }}
    }}

    async function runWorkbenchAction(action, imageId, fallbackCommand) {{
      if (!window.location.protocol.startsWith("http")) {{
        copyCommand(fallbackCommand);
        return;
      }}
      showToast("正在执行，请稍候");
      try {{
        const response = await fetch("/api/action", {{
          method: "POST",
          headers: {{"Content-Type": "application/json"}},
          body: JSON.stringify({{action, image_id: imageId}})
        }});
        const payload = await response.json();
        if (!response.ok || payload.ok !== true) {{
          const detail = payload.output || payload.error || "动作执行失败";
          window.alert(detail);
          showToast("执行失败");
          return;
        }}
        showToast("执行完成，正在刷新");
        window.location.reload();
      }} catch (err) {{
        window.alert(`执行失败：${{err}}`);
        showToast("执行失败");
      }}
    }}

    rewriteLocalFileLinks();
  </script>
</body>
</html>
"""


def _prompt_patch_plan_payload(data: dict[str, Any], manifest_path: Path) -> dict[str, Any]:
    quality_review = data.get("quality_review") if isinstance(data.get("quality_review"), dict) else {}
    top_cards = quality_review.get("top_review_cards") if isinstance(quality_review.get("top_review_cards"), list) else []
    review_queue = quality_review.get("review_queue") if isinstance(quality_review.get("review_queue"), list) else []

    def build_patch_from_card(card: dict[str, Any]) -> dict[str, Any] | None:
        if not isinstance(card, dict):
            return None
        image_id = str(card.get("image_id") or "").strip()
        if not image_id:
            return None
        job = _job_by_image_id(data, image_id)
        if not isinstance(job, dict):
            return None
        auto_repair_plan = job.get("auto_repair_plan") if isinstance(job.get("auto_repair_plan"), dict) else None
        if not isinstance(auto_repair_plan, dict):
            auto_repair_plan = build_auto_repair_plan(job, job.get("quality_gate") if isinstance(job.get("quality_gate"), dict) else None)
        creator_review_card = job.get("creator_review_card") if isinstance(job.get("creator_review_card"), dict) else {}
        prompt_sections = [str(item).strip() for item in (auto_repair_plan.get("repair_prompt_sections") or []) if str(item).strip()]
        negative_hints = [str(item).strip() for item in (auto_repair_plan.get("repair_negative_hints") or []) if str(item).strip()]
        current_negative = [item.strip() for item in str(job.get("negative_prompt") or "").split(",") if item.strip()]
        merged_negative = current_negative[:]
        for hint in negative_hints:
            if hint.lower() not in {item.lower() for item in merged_negative}:
                merged_negative.append(hint)
        return {
            "rank": card.get("rank"),
            "image_id": image_id,
            "shot_id": job.get("shot_id"),
            "frame_role": job.get("frame_role"),
            "priority_label": card.get("priority_label"),
            "priority_score": card.get("priority_score"),
            "risk_summary": card.get("headline"),
            "current_prompt": job.get("prompt"),
            "prompt_patch_sections": prompt_sections,
            "patched_prompt_preview": "\n".join([str(job.get("prompt") or "").strip(), *prompt_sections]).strip(),
            "current_negative_prompt": str(job.get("negative_prompt") or "").strip(),
            "negative_prompt_additions": negative_hints,
            "patched_negative_prompt_preview": ", ".join(merged_negative),
            "quick_fix": card.get("quick_fix") or ((creator_review_card.get("suggestions") or [None])[0] if isinstance(creator_review_card, dict) else None),
            "review_focus": card.get("review_focus") or card.get("first_check"),
            "repair_preview_path": job.get("repair_preview_path"),
            "result_image_path": (job.get("evidence", {}) or {}).get("file_path") or job.get("output_path"),
            "rerun_command": _rerun_command_for_image(manifest_path, image_id),
            "creator_review_card": creator_review_card,
        }

    all_patches: list[dict[str, Any]] = []
    for index, item in enumerate(review_queue):
        if not isinstance(item, dict):
            continue
        queue_card = dict(item)
        queue_card.setdefault("rank", index + 1)
        patch = build_patch_from_card(queue_card)
        if patch:
            all_patches.append(patch)

    top_patches: list[dict[str, Any]] = []
    for card in top_cards:
        patch = build_patch_from_card(card)
        if patch:
            top_patches.append(patch)
    return {
        "project_id": data.get("project_id"),
        "manifest_path": str(manifest_path.resolve()).replace("\\", "/"),
        "generated_at": utc_now(),
        "patch_count": len(top_patches),
        "queue_patch_count": len(all_patches),
        "top_prompt_patches": top_patches,
        "all_prompt_patches": all_patches,
    }


def _prompt_patch_markdown_lines(plan: dict[str, Any]) -> list[str]:
    patches = plan.get("top_prompt_patches") if isinstance(plan.get("top_prompt_patches"), list) else []
    lines = [
        "# Stage 05 Prompt Patch Cards",
        "",
        f"- 项目：`{plan.get('project_id')}`",
        f"- Patch 数量：{plan.get('patch_count', 0)}",
        "",
    ]
    if not patches:
        lines.extend([
            "当前没有需要生成 prompt patch 的高风险镜头。",
            "",
        ])
        return lines
    for patch in patches:
        if not isinstance(patch, dict):
            continue
        lines.append(f"## #{patch.get('rank') or '-'} {patch.get('image_id') or 'unknown'}")
        lines.append("")
        lines.append(f"- 镜头：`{patch.get('shot_id') or '-'}` / `{patch.get('frame_role') or '-'}`")
        if patch.get("risk_summary"):
            lines.append(f"- 风险：{patch.get('risk_summary')}")
        if patch.get("review_focus"):
            lines.append(f"- 先改什么：{patch.get('review_focus')}")
        if patch.get("quick_fix"):
            lines.append(f"- 最短改法：{patch.get('quick_fix')}")
        lines.append("- Prompt 补丁：")
        for item in patch.get("prompt_patch_sections") or []:
            lines.append(f"  - {item}")
        lines.append("- Negative 补丁：")
        for item in patch.get("negative_prompt_additions") or []:
            lines.append(f"  - {item}")
        if patch.get("rerun_command"):
            lines.append(f"- 单图重跑：`{patch.get('rerun_command')}`")
        lines.append("")
    return lines


def write_stage05_manual_review_files(data: dict[str, Any], manifest_path: Path) -> None:
    lines = _review_queue_markdown_lines(data, manifest_path)
    content = "\n".join(lines)
    write_text(manifest_path.parent / "manual_review.md", content)
    write_text(manifest_path.parent / "image_review.md", content)


def write_stage05_prompt_patch_files(data: dict[str, Any], manifest_path: Path) -> None:
    plan = _prompt_patch_plan_payload(data, manifest_path)
    write_json(manifest_path.parent / "prompt_patch_plan.json", plan)
    write_text(manifest_path.parent / "prompt_patch_cards.md", "\n".join(_prompt_patch_markdown_lines(plan)))


def write_stage05_review_workbench_files(data: dict[str, Any], manifest_path: Path) -> None:
    payload = _workbench_payload(data, manifest_path)
    write_json(manifest_path.parent / "stage05_review_workbench.json", payload)
    write_text(manifest_path.parent / "stage05_review_workbench.html", _workbench_html(payload))


def update_manifest_state(data: dict[str, Any], manifest_path: Path) -> None:
    jobs = data.get("jobs") if isinstance(data.get("jobs"), list) else []
    routing = data.get("routing") if isinstance(data.get("routing"), dict) else {"legacy_mode": True}
    strategy = data.get("image_provider_strategy") if isinstance(data.get("image_provider_strategy"), dict) else {}
    primary_provider = str(strategy.get("primary") or "").strip() or None
    fallback_providers = [str(item).strip() for item in (strategy.get("fallback") or []) if str(item).strip()]
    generated = 0
    failed = 0
    shots: dict[str, set[str]] = {}
    evidence_origin_summary = {
        "provider_output": 0,
        "fallback_output": 0,
        "manual_import": 0,
        "placeholder_or_incomplete": 0,
    }
    for job in jobs:
        if not isinstance(job, dict):
            continue
        shot_id = job.get("shot_id")
        frame_role = job.get("frame_role")
        if isinstance(shot_id, str) and isinstance(frame_role, str):
            shots.setdefault(shot_id, set()).add(frame_role)
        output_path = job.get("output_path") or job.get("evidence", {}).get("file_path")
        resolved = resolve_path(manifest_path, output_path)
        exists = resolved.exists() and resolved.is_file() and resolved.stat().st_size > 0
        job.setdefault("evidence", {})
        job["evidence"]["file_path"] = str(resolved).replace("\\", "/")
        job["evidence"]["file_exists"] = exists
        job["evidence"]["file_size_bytes"] = resolved.stat().st_size if exists else 0
        origin = annotate_evidence_origin(
            job["evidence"],
            provider=job.get("provider"),
            file_exists=exists,
            file_size_bytes=job["evidence"]["file_size_bytes"],
            primary_provider=primary_provider,
            fallback_providers=fallback_providers,
            production_ready=exists and not str(job.get("provider") or "").strip().lower().startswith("placeholder_test_"),
        )
        evidence_origin_summary[origin] += 1
        job["quality_gate"] = build_quality_gate(job)
        creator_review_card = build_creator_review_card(
            job,
            job["quality_gate"],
            auto_repair_status=str(job.get("auto_repair_status") or "").strip() or None,
        )
        if creator_review_card:
            existing_card = job.get("creator_review_card") if isinstance(job.get("creator_review_card"), dict) else {}
            creator_review_card.update(existing_card)
            if "auto_repair_status" not in creator_review_card and job.get("auto_repair_status"):
                creator_review_card["auto_repair_status"] = job.get("auto_repair_status")
            if job.get("repair_preview_path") and "repair_preview_path" not in creator_review_card:
                creator_review_card["repair_preview_path"] = job.get("repair_preview_path")
            job["creator_review_card"] = creator_review_card
        if exists:
            generated += 1
        elif job.get("status") in {"failed", "blocked"}:
            failed += 1
    expected = len(jobs)
    all_exist = expected > 0 and generated == expected
    quality_review = summarize_quality_review(jobs)
    manual_review_cleared = bool(quality_review.get("manual_review_cleared"))
    data.setdefault("summary", {})
    data["summary"].update({
        "shot_count": len(shots),
        "expected_image_count": expected,
        "generated_image_count": generated,
        "failed_image_count": failed if failed else max(0, expected - generated),
        "evidence_origin_summary": evidence_origin_summary,
    })
    data["quality_review"] = quality_review
    provider_status = data.get("creator_runtime_status")
    if not isinstance(provider_status, dict):
        provider_status = {}
    if isinstance(data.get("provider_decisions"), list):
        latest_decision = data["provider_decisions"][-1] if data["provider_decisions"] else None
        if isinstance(latest_decision, dict):
            provider = str(latest_decision.get("provider") or "").strip()
            decision = str(latest_decision.get("decision") or "").strip()
            reason = str(latest_decision.get("reason") or "").strip()
            if provider == "comfyui_txt2img" and decision == "auto_fallback_selected":
                provider_status.update({
                    "headline": "OpenAI 不可用，已自动切到本地 ComfyUI。",
                    "detail": "本地生成通常更慢，但当前任务会继续完成。",
                    "reason": reason,
                })
            elif provider == "manual" and "manual_recovery_required" in decision:
                if reason == "missing_character_reference_before_generation":
                    provider_status.update({
                        "headline": "高风险关键帧已阻断，先补角色参考图。",
                        "detail": "当前镜头缺少 Stage 03 角色参考图，继续自动生图最容易出现 start / mid / end 换人。",
                        "reason": reason,
                    })
                else:
                    provider_status.update({
                        "headline": "自动 provider 无法继续，当前需要人工补位。",
                        "detail": "请按 manifest 中的 manual recovery 指引放置或补修关键帧。",
                        "reason": reason,
                    })
    if quality_review.get("risky_image_count"):
        provider_status["review_headline"] = quality_review.get("creator_feedback_headline")
    if provider_status:
        data["creator_runtime_status"] = provider_status
    data.setdefault("self_check", {})
    notes: list[str] = []
    if not manual_review_cleared and quality_review.get("blocking_image_ids"):
        notes.append(
            "Manual review required before Stage 06 for: "
            + ", ".join(str(item) for item in quality_review["blocking_image_ids"])
        )
    if quality_review.get("next_review_image_ids"):
        notes.append(
            "Review priority queue starts with: "
            + ", ".join(str(item) for item in quality_review["next_review_image_ids"])
        )
    data["self_check"].update({
        "covers_all_keyframe_prompts": expected > 0,
        "has_start_and_end_for_each_shot": all({"start", "end"}.issubset(roles) for roles in shots.values()) if shots else False,
        "all_required_images_exist": all_exist,
        "manual_review_cleared": manual_review_cleared,
        "ready_for_video_clip_generation": all_exist and manual_review_cleared,
        "notes": notes,
    })
    if all_exist:
        data["status"] = "generated"
    elif generated > 0 or failed > 0:
        data["status"] = "in_progress"
    data["allowed_next_stage"] = (
        next_stage_after("STAGE_05_KEYFRAME_IMAGES", routing, "STAGE_06_VIDEO_CLIPS")
        if all_exist and manual_review_cleared
        else None
    )
    data["updated_at"] = utc_now()
    write_stage05_manual_review_files(data, manifest_path)
    write_stage05_prompt_patch_files(data, manifest_path)
    write_stage05_review_workbench_files(data, manifest_path)
