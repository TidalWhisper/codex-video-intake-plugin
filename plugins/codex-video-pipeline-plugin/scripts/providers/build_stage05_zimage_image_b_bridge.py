#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_NEGATIVE_PROMPT = "low quality, blurry, deformed, duplicate subject, extra limbs, bad anatomy, text, watermark, logo"
DEFAULT_NEGATIVE_ANCHOR = (
    "flat documentary realism, washed-out colors, muddy shadows, weak silhouette, low design contrast, "
    "plastic cgi skin, over-detailed photographic texture, broken anatomy, duplicated people, text banner, logo, watermark"
)


def load_ui_graph(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    nodes = data.get("nodes")
    if not isinstance(nodes, list):
        raise SystemExit(f"ERROR: expected ComfyUI UI graph with top-level nodes array: {path}")
    return [node for node in nodes if isinstance(node, dict)]


def widgets(node: dict[str, Any]) -> list[Any]:
    values = node.get("widgets_values")
    return values if isinstance(values, list) else []


def normalize_model_name(raw_name: Any, *, folder: str) -> str:
    name = str(raw_name or "").strip()
    if not name:
        return name
    if "\\" in name or "/" in name:
        return name.replace("/", "\\")
    return f"{folder}\\{name}"


def find_loader_node(
    nodes: list[dict[str, Any]],
    node_type: str,
    *,
    name_contains: str,
) -> dict[str, Any]:
    lowered = name_contains.lower()
    for node in reversed(nodes):
        if str(node.get("type") or "").strip() != node_type:
            continue
        values = widgets(node)
        first_value = str(values[0] if values else "").strip().lower()
        if lowered in first_value:
            return node
    raise SystemExit(f"ERROR: could not find {node_type} with value containing '{name_contains}'")


def find_latent_node(nodes: list[dict[str, Any]]) -> dict[str, Any]:
    for node in nodes:
        if str(node.get("type") or "").strip() == "EmptyLatentImage":
            return node
    raise SystemExit("ERROR: could not find EmptyLatentImage node in source UI graph")


def find_sampler_hint(nodes: list[dict[str, Any]]) -> dict[str, Any]:
    for node in nodes:
        if str(node.get("type") or "").strip() == "KSamplerAdvanced":
            return node
    raise SystemExit("ERROR: could not find KSamplerAdvanced hint node in source UI graph")


def clean_anchor_text(raw: str) -> str:
    text = raw.replace("{$spicy-content-with}", "").replace("{$@}", "").strip()
    while "  " in text:
        text = text.replace("  ", " ")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return ""
    kept: list[str] = []
    stop_prefixes = (
        "YOUR PHOTO:",
        "YOUR PHOTOGRAPH:",
        "YOUR IMAGE:",
        "YOUR DRAWING:",
        "YOUR ILLUSTRATION:",
        "YOUR MULTI SUBJECT PRINT:",
    )
    for line in lines:
        if line.startswith(stop_prefixes):
            break
        if line.startswith("YOUR CONTEXT:"):
            continue
        kept.append(line)
    return " ".join(kept).strip()


def choose_image_b_anchor(nodes: list[dict[str, Any]]) -> str:
    candidates: list[str] = []
    for node in nodes:
        if str(node.get("type") or "").strip() != "PrimitiveStringMultiline":
            continue
        values = widgets(node)
        cleaned = clean_anchor_text(str(values[0] if values else "").strip())
        if cleaned:
            candidates.append(cleaned)
    preferred_keywords = (
        "heavy chromatic aberration",
        "ultra-modern and fragmented",
        "high-contrast palette of neon purples and cyans",
        "dark fantasy film reminiscent of the 1980s",
        "conceptual artist creating a tactile, handcrafted world",
    )
    for keyword in preferred_keywords:
        for candidate in candidates:
            if keyword.lower() in candidate.lower():
                return candidate
    if candidates:
        return candidates[0]
    return (
        "You are a digital concept artist building a premium key visual. Your image emphasizes bold silhouette hierarchy, "
        "dramatic color scripting, graphic texture separation, and a strong non-photographic concept-art finish."
    )


def build_bridge_workflow(
    *,
    unet_name: str,
    clip_name: str,
    clip_type: str,
    vae_name: str,
    width: int,
    height: int,
    steps: int,
    cfg: float,
    sampler_name: str,
    scheduler: str,
    style_anchor: str,
) -> dict[str, Any]:
    return {
        "1": {
            "inputs": {
                "unet_name": unet_name,
                "weight_dtype": "default",
            },
            "class_type": "UNETLoader",
            "_meta": {"title": "Load Z-Image Image-B UNet"},
        },
        "2": {
            "inputs": {
                "clip_name": clip_name,
                "type": clip_type,
                "device": "default",
            },
            "class_type": "CLIPLoader",
            "_meta": {"title": "Load Z-Image Image-B CLIP"},
        },
        "3": {
            "inputs": {
                "vae_name": vae_name,
            },
            "class_type": "VAELoader",
            "_meta": {"title": "Load Z-Image Image-B VAE"},
        },
        "10": {
            "inputs": {
                "text": "stylized concept keyframe",
                "clip": ["2", 0],
            },
            "class_type": "CLIPTextEncode",
            "_meta": {"title": "User Positive Prompt"},
        },
        "11": {
            "inputs": {
                "text": style_anchor,
                "clip": ["2", 0],
            },
            "class_type": "CLIPTextEncode",
            "_meta": {"title": "Z-Image Image-B Style Anchor"},
        },
        "12": {
            "inputs": {
                "conditioning_1": ["10", 0],
                "conditioning_2": ["11", 0],
            },
            "class_type": "ConditioningCombine",
            "_meta": {"title": "Combine Positive Conditioning"},
        },
        "13": {
            "inputs": {
                "text": DEFAULT_NEGATIVE_PROMPT,
                "clip": ["2", 0],
            },
            "class_type": "CLIPTextEncode",
            "_meta": {"title": "User Negative Prompt"},
        },
        "14": {
            "inputs": {
                "text": DEFAULT_NEGATIVE_ANCHOR,
                "clip": ["2", 0],
            },
            "class_type": "CLIPTextEncode",
            "_meta": {"title": "Z-Image Image-B Negative Anchor"},
        },
        "15": {
            "inputs": {
                "conditioning_1": ["13", 0],
                "conditioning_2": ["14", 0],
            },
            "class_type": "ConditioningCombine",
            "_meta": {"title": "Combine Negative Conditioning"},
        },
        "20": {
            "inputs": {
                "width": width,
                "height": height,
                "batch_size": 1,
            },
            "class_type": "EmptyLatentImage",
            "_meta": {"title": "Empty Latent Image"},
        },
        "30": {
            "inputs": {
                "model": ["1", 0],
                "seed": 741852963,
                "steps": steps,
                "cfg": cfg,
                "sampler_name": sampler_name,
                "scheduler": scheduler,
                "positive": ["12", 0],
                "negative": ["15", 0],
                "latent_image": ["20", 0],
                "denoise": 1.0,
            },
            "class_type": "KSampler",
            "_meta": {"title": "Z-Image Image-B Bridge Sampler"},
        },
        "40": {
            "inputs": {
                "samples": ["30", 0],
                "vae": ["3", 0],
            },
            "class_type": "VAEDecode",
            "_meta": {"title": "Decode Image"},
        },
        "60": {
            "inputs": {
                "images": ["40", 0],
                "filename_prefix": "video/keyframes/zimage_image_b_bridge",
            },
            "class_type": "SaveImage",
            "_meta": {"title": "Save Image"},
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a Stage 05 API bridge workflow from Amazing Z-Image image-b UI graph."
    )
    parser.add_argument("source_ui_graph", help="Path to amazing-z-image-b_SAFETENSORS.json UI graph")
    parser.add_argument("output_api_workflow", help="Path to output workflow_api.json")
    args = parser.parse_args(argv)

    source_path = Path(args.source_ui_graph)
    output_path = Path(args.output_api_workflow)
    nodes = load_ui_graph(source_path)

    unet_node = find_loader_node(nodes, "UNETLoader", name_contains="z_image_turbo")
    clip_node = find_loader_node(nodes, "CLIPLoader", name_contains="qwen_3_4b")
    vae_node = find_loader_node(nodes, "VAELoader", name_contains="ae.safetensors")
    latent_node = find_latent_node(nodes)
    sampler_hint = find_sampler_hint(nodes)

    unet_values = widgets(unet_node)
    clip_values = widgets(clip_node)
    vae_values = widgets(vae_node)
    latent_values = widgets(latent_node)
    sampler_values = widgets(sampler_hint)

    workflow = build_bridge_workflow(
        unet_name=normalize_model_name(unet_values[0], folder="Zimage"),
        clip_name=normalize_model_name(clip_values[0], folder="Zimage"),
        clip_type=str(clip_values[1] if len(clip_values) > 1 else "lumina2"),
        vae_name=normalize_model_name(vae_values[0], folder="Zimage"),
        width=int(latent_values[0] if latent_values else 944),
        height=int(latent_values[1] if len(latent_values) > 1 else 1408),
        steps=int(sampler_values[3] if len(sampler_values) > 3 else 8),
        cfg=float(sampler_values[4] if len(sampler_values) > 4 else 1.0),
        sampler_name=str(sampler_values[5] if len(sampler_values) > 5 else "euler"),
        scheduler=str(sampler_values[6] if len(sampler_values) > 6 else "simple"),
        style_anchor=choose_image_b_anchor(nodes),
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(workflow, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"STAGE05 ZIMAGE IMAGE-B BRIDGE WRITTEN: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
