#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Any


THIS_DIR = Path(__file__).resolve().parent
ROOT = THIS_DIR.parents[1]
TEMPLATES = ROOT / "templates"
IMAGES = ROOT / "skills" / "video-keyframe-images" / "scripts"
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


new_keyframe_image_jobs = load_module("new_keyframe_image_jobs_stage05_scene_matrix", IMAGES / "new_keyframe_image_jobs.py")
run_comfyui_txt2img = load_module("run_comfyui_txt2img_stage05_scene_matrix", THIS_DIR / "run_comfyui_txt2img.py")
run_openai_gpt_image2 = load_module("run_openai_gpt_image2_stage05_scene_matrix", THIS_DIR / "run_openai_gpt_image2.py")


@dataclass(frozen=True)
class SceneShot:
    shot_id: str
    start_keyframe_prompt: str
    end_keyframe_prompt: str
    style_prompt: str
    consistency_prompt: str
    camera_prompt: str
    negative_prompt: str
    expected_risk_tags: tuple[str, ...]


@dataclass(frozen=True)
class ScenePack:
    pack_key: str
    display_name: str
    normalized_style: str
    shots: tuple[SceneShot, ...]


COMMON_NEGATIVE = "low resolution, watermark, logo, duplicate person, extra limbs, deformed hands, distorted face"


SCENE_PACKS: dict[str, ScenePack] = {
    "realistic_review_pack": ScenePack(
        pack_key="realistic_review_pack",
        display_name="Realistic Review Pack",
        normalized_style="温暖治愈",
        shots=(
            SceneShot(
                shot_id="S001",
                start_keyframe_prompt="cinematic beach walk at sunset, single woman walking along the shoreline",
                end_keyframe_prompt="the same woman glances back toward the sea while continuing the beach walk",
                style_prompt="realistic cinematic still",
                consistency_prompt="same young woman, same beach, same outfit",
                camera_prompt="wide shot",
                negative_prompt=COMMON_NEGATIVE,
                expected_risk_tags=(),
            ),
            SceneShot(
                shot_id="S002",
                start_keyframe_prompt="realistic close-up of a hand offering a teacup across a wooden table",
                end_keyframe_prompt="the same hand steadies the teacup on a tray",
                style_prompt="refined realistic still",
                consistency_prompt="same hand, same teacup, same table",
                camera_prompt="insert close-up",
                negative_prompt=COMMON_NEGATIVE,
                expected_risk_tags=("cup_hand_contact",),
            ),
            SceneShot(
                shot_id="S003",
                start_keyframe_prompt="romance poster, a couple holding hands while walking under evening light",
                end_keyframe_prompt="the same couple keeps holding hands and turns slightly toward camera",
                style_prompt="romantic cinematic poster art",
                consistency_prompt="same couple, same costumes, same lighting",
                camera_prompt="medium wide shot",
                negative_prompt=COMMON_NEGATIVE,
                expected_risk_tags=("two_subject_contact",),
            ),
        ),
    ),
    "realistic_establishing_expanded_pack": ScenePack(
        pack_key="realistic_establishing_expanded_pack",
        display_name="Realistic Establishing Expanded Pack",
        normalized_style="写实电影感",
        shots=(
            SceneShot(
                shot_id="S001",
                start_keyframe_prompt="young woman in a long dress walking alone along the shoreline at dusk, wide coastal establishing shot",
                end_keyframe_prompt="the same woman keeps walking alone by the sea while the sunset sky opens wider behind her",
                style_prompt="realistic cinematic still",
                consistency_prompt="same woman, same long dress, same quiet beach, same sunset atmosphere",
                camera_prompt="wide establishing shot",
                negative_prompt=COMMON_NEGATIVE,
                expected_risk_tags=("single_subject_wide_establishing",),
            ),
            SceneShot(
                shot_id="S002",
                start_keyframe_prompt="middle-aged fisherman standing alone on a foggy harbor pier before sunrise, realistic wide environmental shot",
                end_keyframe_prompt="the same fisherman remains alone on the pier while the harbor lights fade into dawn mist",
                style_prompt="grounded realistic still",
                consistency_prompt="same fisherman, same pier, same foggy harbor, same work clothes",
                camera_prompt="wide establishing shot",
                negative_prompt=COMMON_NEGATIVE,
                expected_risk_tags=("single_subject_wide_establishing",),
            ),
            SceneShot(
                shot_id="S003",
                start_keyframe_prompt="young man in a dark coat crossing a rainy neon street alone at night, realistic city establishing shot",
                end_keyframe_prompt="the same man continues alone through the wet street as traffic reflections spread across the road",
                style_prompt="realistic cinematic still",
                consistency_prompt="same man, same dark coat, same rainy night street, same neon reflections",
                camera_prompt="wide establishing shot",
                negative_prompt=COMMON_NEGATIVE,
                expected_risk_tags=("single_subject_wide_establishing",),
            ),
        ),
    ),
    "realistic_healing_expanded_pack": ScenePack(
        pack_key="realistic_healing_expanded_pack",
        display_name="Realistic Healing Expanded Pack",
        normalized_style="温暖治愈",
        shots=(
            SceneShot(
                shot_id="S001",
                start_keyframe_prompt="young mother with short hair sitting alone beside a large cafe window in morning light, realistic wide interior shot",
                end_keyframe_prompt="the same woman lifts her eyes toward the sunlit street outside while remaining alone at the same cafe table",
                style_prompt="warm healing realistic still",
                consistency_prompt="same woman, same cafe, same soft morning light, same knit cardigan",
                camera_prompt="wide interior establishing shot",
                negative_prompt=COMMON_NEGATIVE,
                expected_risk_tags=("single_subject_wide_establishing",),
            ),
            SceneShot(
                shot_id="S002",
                start_keyframe_prompt="solo female hiker pausing on a mountain road during blue hour, realistic scenic wide shot",
                end_keyframe_prompt="the same hiker stays alone on the road while distant mountain lights appear in the evening haze",
                style_prompt="healing cinematic realism",
                consistency_prompt="same hiker, same backpack, same mountain road, same blue-hour atmosphere",
                camera_prompt="wide scenic shot",
                negative_prompt=COMMON_NEGATIVE,
                expected_risk_tags=("single_subject_wide_establishing",),
            ),
            SceneShot(
                shot_id="S003",
                start_keyframe_prompt="elderly woman watering plants alone in a small rooftop garden at sunset, realistic wide lifestyle shot",
                end_keyframe_prompt="the same elderly woman keeps tending the rooftop plants while warm sunset light fills the city skyline behind her",
                style_prompt="warm realistic still",
                consistency_prompt="same elderly woman, same rooftop garden, same watering can, same sunset skyline",
                camera_prompt="wide lifestyle establishing shot",
                negative_prompt=COMMON_NEGATIVE,
                expected_risk_tags=("single_subject_wide_establishing",),
            ),
        ),
    ),
    "realistic_editorial_expanded_pack": ScenePack(
        pack_key="realistic_editorial_expanded_pack",
        display_name="Realistic Editorial Expanded Pack",
        normalized_style="广告高级感",
        shots=(
            SceneShot(
                shot_id="S001",
                start_keyframe_prompt="young Black woman standing alone in a minimalist hotel lobby with tall stone walls, realistic premium editorial wide shot",
                end_keyframe_prompt="the same woman turns slightly in the same lobby while the polished floor and architectural depth remain prominent",
                style_prompt="premium realistic editorial still",
                consistency_prompt="same woman, same hotel lobby, same tailored outfit, same luxury interior atmosphere",
                camera_prompt="wide editorial establishing shot",
                negative_prompt=COMMON_NEGATIVE,
                expected_risk_tags=("single_subject_wide_establishing",),
            ),
            SceneShot(
                shot_id="S002",
                start_keyframe_prompt="stylish young man standing alone beside a silver sedan on a desert highway at golden hour, realistic luxury ad wide shot",
                end_keyframe_prompt="the same man remains alone near the car while the desert horizon opens behind him in warm light",
                style_prompt="high-end realistic advertising still",
                consistency_prompt="same man, same silver sedan, same desert highway, same golden-hour atmosphere",
                camera_prompt="wide advertising establishing shot",
                negative_prompt=COMMON_NEGATIVE,
                expected_risk_tags=("single_subject_wide_establishing",),
            ),
            SceneShot(
                shot_id="S003",
                start_keyframe_prompt="young East Asian woman standing alone on a modern office rooftop at dusk, realistic premium city wide shot",
                end_keyframe_prompt="the same woman stays alone on the rooftop while the skyline lights become clearer behind her",
                style_prompt="luxury cinematic realism",
                consistency_prompt="same woman, same rooftop, same suit silhouette, same dusk skyline",
                camera_prompt="wide editorial establishing shot",
                negative_prompt=COMMON_NEGATIVE,
                expected_risk_tags=("single_subject_wide_establishing",),
            ),
        ),
    ),
    "guofeng_review_pack": ScenePack(
        pack_key="guofeng_review_pack",
        display_name="Guofeng Review Pack",
        normalized_style="国风水墨/古风",
        shots=(
            SceneShot(
                shot_id="S001",
                start_keyframe_prompt="ancient Chinese woman holding one oil-paper umbrella in misty rain",
                end_keyframe_prompt="the same woman turns with the same oil-paper umbrella under mist",
                style_prompt="guofeng ink wash illustration",
                consistency_prompt="same woman, same umbrella, same hanfu",
                camera_prompt="medium scenic shot",
                negative_prompt=COMMON_NEGATIVE,
                expected_risk_tags=("umbrella_prop_contact",),
            ),
            SceneShot(
                shot_id="S002",
                start_keyframe_prompt="guofeng scholar opening a folding fan near the window",
                end_keyframe_prompt="the same scholar half-closes the folding fan",
                style_prompt="poetic guofeng illustration",
                consistency_prompt="same scholar, same folding fan, same robe",
                camera_prompt="mid shot",
                negative_prompt=COMMON_NEGATIVE,
                expected_risk_tags=("fan_hand_contact",),
            ),
            SceneShot(
                shot_id="S003",
                start_keyframe_prompt="young musician playing a bamboo flute under moonlight",
                end_keyframe_prompt="the same musician lowers the bamboo flute slightly after playing",
                style_prompt="moonlit guofeng illustration",
                consistency_prompt="same musician, same bamboo flute, same robe",
                camera_prompt="medium close-up",
                negative_prompt=COMMON_NEGATIVE,
                expected_risk_tags=("instrument_hand_contact",),
            ),
        ),
    ),
    "anime_review_pack": ScenePack(
        pack_key="anime_review_pack",
        display_name="Anime Review Pack",
        normalized_style="日系动画风（日本动漫感）",
        shots=(
            SceneShot(
                shot_id="S001",
                start_keyframe_prompt="anime heroine gripping a katana in a duel stance",
                end_keyframe_prompt="the same heroine lowers the katana slightly while staying ready",
                style_prompt="anime action key visual",
                consistency_prompt="same heroine, same katana, same costume",
                camera_prompt="dynamic medium shot",
                negative_prompt=COMMON_NEGATIVE,
                expected_risk_tags=("weapon_hand_contact",),
            ),
        ),
    ),
    "stylized_review_pack": ScenePack(
        pack_key="stylized_review_pack",
        display_name="Stylized Review Pack",
        normalized_style="游戏CG感",
        shots=(
            SceneShot(
                shot_id="S001",
                start_keyframe_prompt="heroic armored rider on horseback crossing a windy plateau, premium fantasy game illustration, clean artwork only, no text",
                end_keyframe_prompt="the same rider keeps riding the horse while pulling it to a gentle stop",
                style_prompt="premium fantasy action illustration, clean game cg artwork",
                consistency_prompt="same rider, same horse, same armor",
                camera_prompt="wide action shot",
                negative_prompt=COMMON_NEGATIVE,
                expected_risk_tags=("riding_pose_contact",),
            ),
        ),
    ),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def summarize_manifest(pack: ScenePack, project_dir: Path, manifest_path: Path) -> dict[str, Any]:
    manifest = load_json(manifest_path)
    return {
        "pack_key": pack.pack_key,
        "display_name": pack.display_name,
        "normalized_style": pack.normalized_style,
        "project_dir": str(project_dir).replace("\\", "/"),
        "manifest_path": str(manifest_path).replace("\\", "/"),
        "stage05_route_key": manifest.get("stage05_route_key"),
        "style_family": manifest.get("style_family"),
        "quality_review": manifest.get("quality_review"),
        "self_check": manifest.get("self_check"),
        "allowed_next_stage": manifest.get("allowed_next_stage"),
        "semantic_review_template": semantic_review_template(pack),
        "jobs": manifest.get("jobs") or [],
    }


def semantic_review_template(pack: ScenePack) -> list[dict[str, Any]]:
    template: list[dict[str, Any]] = []
    for shot in pack.shots:
        template.append({
            "shot_id": shot.shot_id,
            "start_image_id": f"IMG_{shot.shot_id}_START",
            "end_image_id": f"IMG_{shot.shot_id}_END",
            "expected_subject_count": 1 if "same couple" not in shot.consistency_prompt.lower() and "same couple" not in shot.start_keyframe_prompt.lower() else 2,
            "must_match": [
                f"主体与提示词一致: {shot.start_keyframe_prompt}",
                f"镜头与构图大方向一致: {shot.camera_prompt}",
                f"风格方向一致: {shot.style_prompt}",
                f"连续性一致: {shot.consistency_prompt}",
                "不能多人/少人，不能多手多脚，不能出现与描述冲突的主体或道具。",
            ],
        })
    return template


def locked_brief_for_pack(project_dir: Path, pack: ScenePack) -> dict[str, Any]:
    brief = load_json(TEMPLATES / "project_brief.draft.example.json")
    brief.update({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": utc_now(),
    })
    normalized = brief.setdefault("normalized", {})
    normalized["style"] = pack.normalized_style
    normalized["final_output"] = "生成关键帧图片素材包"
    return brief


def keyframe_prompts_for_pack(project_dir: Path, locked_brief_path: Path, pack: ScenePack) -> dict[str, Any]:
    template = load_json(TEMPLATES / "keyframe_prompts.example.json")
    prompts = {
        "schema_version": template.get("schema_version", "0.5.0"),
        "stage": "STAGE_04_KEYFRAME_PROMPTS",
        "status": "confirmed",
        "project_id": project_dir.name,
        "source_brief": str(locked_brief_path).replace("\\", "/"),
        "source_script": template.get("source_script"),
        "source_storyboard": template.get("source_storyboard"),
        "source_character_bible": template.get("source_character_bible"),
        "prompt_language": template.get("prompt_language"),
        "visual_strategy": template.get("visual_strategy"),
        "shot_prompts": [],
        "transition_prompts": [],
        "global_negative_prompt": COMMON_NEGATIVE,
        "self_check": {
            "matches_locked_brief": True,
            "matches_script": True,
            "matches_storyboard": True,
            "uses_character_consistency": True,
            "covers_all_storyboard_shots": True,
            "ready_for_image_generation": True,
            "notes": [],
        },
        "allowed_next_stage": None,
    }
    for shot in pack.shots:
        prompts["shot_prompts"].append({
            "shot_id": shot.shot_id,
            "source_shot_ref": f"{project_dir.name}/storyboard#{shot.shot_id}",
            "duration_sec": 5,
            "characters": ["CHAR_001"],
            "scene_summary": shot.start_keyframe_prompt,
            "start_keyframe_prompt": shot.start_keyframe_prompt,
            "end_keyframe_prompt": shot.end_keyframe_prompt,
            "motion_prompt": shot.end_keyframe_prompt,
            "camera_prompt": shot.camera_prompt,
            "lighting_prompt": "",
            "style_prompt": shot.style_prompt,
            "consistency_prompt": shot.consistency_prompt,
            "negative_prompt": shot.negative_prompt,
            "image_generation_notes": "Stage 05 scene matrix smoke validation shot.",
            "video_generation_notes": "Not used for this Stage 05 smoke pack.",
            "dependencies": {
                "reference_images": [],
                "previous_shot_id": None,
                "next_shot_id": None,
            },
        })
    return prompts


def project_name(prefix: str, pack_key: str) -> str:
    return f"{prefix}_{pack_key}"


def prepare_scene_pack_project(base_dir: Path, prefix: str, pack: ScenePack, optimization_profile: str) -> dict[str, Any]:
    project_dir = base_dir / project_name(prefix, pack.pack_key)
    intake_dir = project_dir / "00_intake"
    keyframe_dir = project_dir / "04_keyframes"
    images_dir = project_dir / "05_images"
    intake_dir.mkdir(parents=True, exist_ok=True)
    keyframe_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    locked_brief_path = intake_dir / "project_brief.locked.json"
    keyframe_path = keyframe_dir / "keyframe_prompts.json"
    manifest_path = images_dir / "keyframe_image_manifest.json"

    save_json(locked_brief_path, locked_brief_for_pack(project_dir, pack))
    save_json(keyframe_path, keyframe_prompts_for_pack(project_dir, locked_brief_path, pack))
    rc = new_keyframe_image_jobs.main([
        "new_keyframe_image_jobs.py",
        str(locked_brief_path),
        str(keyframe_path),
        str(manifest_path),
        "--optimization-profile",
        optimization_profile,
    ])
    if rc != 0:
        raise SystemExit(f"ERROR: failed to create Stage 05 jobs for {pack.pack_key}")
    return summarize_manifest(pack, project_dir, manifest_path)


def provider_runner(provider: str):
    if provider == "comfyui_txt2img":
        return run_comfyui_txt2img.main
    if provider == "openai_gpt_image2":
        return run_openai_gpt_image2.main
    raise SystemExit(f"ERROR: unsupported provider for scene matrix smoke: {provider}")


def selected_image_ids_for_pack(pack: ScenePack, image_role: str) -> list[str]:
    suffix = image_role.upper()
    return [f"IMG_{shot.shot_id}_{suffix}" for shot in pack.shots]


def request_item_for_image(request_manifest_path: Path, image_id: str) -> dict[str, Any] | None:
    if not request_manifest_path.exists():
        return None
    data = load_json(request_manifest_path)
    for item in data.get("requests") or []:
        if isinstance(item, dict) and item.get("image_id") == image_id:
            return item
    return None


def run_scene_pack_images(
    *,
    pack: ScenePack,
    manifest_path: Path,
    provider: str,
    optimization_profile: str,
    image_role: str,
    poll_interval: float,
    max_wait_seconds: float | None,
) -> dict[str, Any]:
    runner = provider_runner(provider)
    per_image: list[dict[str, Any]] = []
    request_manifest_name = "comfyui_image_requests.json" if provider == "comfyui_txt2img" else "openai_image_requests.json"
    request_manifest_path = manifest_path.parent / request_manifest_name
    for image_id in selected_image_ids_for_pack(pack, image_role):
        argv = [
            str(manifest_path),
            "--image-id",
            image_id,
            "--allow-beyond-requested-scope",
        ]
        if provider == "comfyui_txt2img":
            argv.extend([
                "--optimization-profile",
                optimization_profile,
                "--poll-interval",
                str(poll_interval),
            ])
            if max_wait_seconds is not None:
                argv.extend(["--max-wait-seconds", str(max_wait_seconds)])
        exit_code = runner(argv)
        manifest = load_json(manifest_path)
        jobs = {job["image_id"]: job for job in manifest.get("jobs") or [] if isinstance(job, dict) and job.get("image_id")}
        job = jobs.get(image_id, {})
        request_item = request_item_for_image(request_manifest_path, image_id)
        per_image.append({
            "image_id": image_id,
            "exit_code": exit_code,
            "job_status": job.get("status"),
            "provider": job.get("provider"),
            "quality_gate": job.get("quality_gate"),
            "output_path": job.get("output_path"),
            "request": request_item,
        })
    updated_manifest = load_json(manifest_path)
    return {
        "pack_key": pack.pack_key,
        "manifest_path": str(manifest_path).replace("\\", "/"),
        "provider": provider,
        "selected_role": image_role,
        "results": per_image,
        "quality_review": updated_manifest.get("quality_review"),
        "self_check": updated_manifest.get("self_check"),
        "allowed_next_stage": updated_manifest.get("allowed_next_stage"),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene-pack", action="append", choices=sorted(SCENE_PACKS.keys()), help="Pack(s) to prepare or run. Defaults to all packs.")
    parser.add_argument("--project-prefix", default=f"real_smoke_{datetime.now().strftime('%Y%m%d')}_stage05_scene_matrix")
    parser.add_argument("--provider", default="comfyui_txt2img", choices=["comfyui_txt2img", "openai_gpt_image2"])
    parser.add_argument("--optimization-profile", default="preview")
    parser.add_argument("--image-role", default="start", choices=["start", "end"])
    parser.add_argument("--run", action="store_true", help="After preparing packs, run the selected provider for the chosen image role.")
    parser.add_argument("--poll-interval", type=float, default=1.0)
    parser.add_argument("--max-wait-seconds", type=float, default=240.0)
    parser.add_argument("--summary-out", default=None, help="Optional combined summary JSON output path.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    selected_pack_keys = args.scene_pack or list(SCENE_PACKS.keys())
    selected_packs = [SCENE_PACKS[key] for key in selected_pack_keys]
    base_dir = ROOT / "video_projects"

    prepared: list[dict[str, Any]] = []
    executed: list[dict[str, Any]] = []
    for pack in selected_packs:
        prepared_pack = prepare_scene_pack_project(base_dir, args.project_prefix, pack, args.optimization_profile)
        prepared.append(prepared_pack)
        if args.run:
            executed.append(
                run_scene_pack_images(
                    pack=pack,
                    manifest_path=Path(prepared_pack["manifest_path"]),
                    provider=args.provider,
                    optimization_profile=args.optimization_profile,
                    image_role=args.image_role,
                    poll_interval=args.poll_interval,
                    max_wait_seconds=args.max_wait_seconds,
                )
            )
            prepared[-1] = summarize_manifest(
                pack,
                Path(prepared_pack["project_dir"]),
                Path(prepared_pack["manifest_path"]),
            )

    summary = {
        "created_at": utc_now(),
        "project_prefix": args.project_prefix,
        "provider": args.provider,
        "optimization_profile": args.optimization_profile,
        "image_role": args.image_role,
        "prepared_packs": prepared,
        "executed_packs": executed,
    }
    summary_path = Path(args.summary_out) if args.summary_out else (base_dir / f"{args.project_prefix}_summary.json")
    save_json(summary_path, summary)
    summary_path_text = str(summary_path).replace("\\", "/")
    print(f"SCENE_MATRIX_SUMMARY: {summary_path_text}")
    print(f"PACKS_PREPARED: {len(prepared)}")
    print(f"PACKS_EXECUTED: {len(executed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
