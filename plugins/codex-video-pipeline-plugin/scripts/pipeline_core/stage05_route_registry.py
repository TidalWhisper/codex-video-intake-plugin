from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


EXPECTED_PROVIDER_ORDER = ["comfyui_txt2img", "manual"]
ROUTE_STATUSES = {"candidate", "approved", "provisional", "blocked", "deprecated", "backlog"}
SUITABILITY_CLASSES = {"native-fit", "adapted-fit", "prompt-only", "unsupported", "under_review"}
SPECIAL_DASIWA_OUTCOMES = {"approved_for_stage05", "provisional_for_stage05", "better_fit_for_stage06"}
STYLE_FAMILIES = {"realistic", "anime", "guofeng", "stylized"}
ADOPTION_STATES = {"current_repo", "ready_to_import", "needs_api_conversion", "stage06_only", "research_gap"}
ROUTE_MIGRATION_STATES = {"stage05a_reference_bootstrap_locked", "ready_to_import", "needs_api_conversion", "stage06_only", "research_gap"}
COMMUNITY_PREFERENCE_POLICIES = {"prefer_community_optimized_when_available"}


class RouteRegistryError(RuntimeError):
    pass


def root_dir() -> Path:
    return Path(__file__).resolve().parents[2]


def _is_non_empty_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _require_object(parent: dict[str, Any], key: str, errors: list[str]) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        errors.append(f"{key} must be an object")
        return {}
    return value


def _require_non_empty_str(parent: dict[str, Any], key: str, errors: list[str]) -> str:
    value = parent.get(key)
    if not _is_non_empty_str(value):
        errors.append(f"{key} must be a non-empty string")
        return ""
    return str(value).strip()


def _require_string_list(parent: dict[str, Any], key: str, errors: list[str], *, allow_empty: bool = False) -> list[str]:
    value = parent.get(key)
    if not isinstance(value, list) or not all(_is_non_empty_str(item) for item in value):
        errors.append(f"{key} must be a list of strings")
        return []
    if not allow_empty and not value:
        errors.append(f"{key} must be a non-empty list of strings")
        return []
    return [str(item).strip() for item in value]


def resolve_stage05_route_registry_path(
    registry_path: str | Path | None = None,
    root: str | Path | None = None,
    *,
    allow_example_fallback: bool = False,
) -> Path:
    base = Path(root) if root else root_dir()
    if registry_path is not None:
        path = Path(registry_path)
        if path.is_absolute():
            return path.resolve()
        if path.exists():
            return path.resolve()
        cwd_candidate = (Path.cwd() / path).resolve()
        if cwd_candidate.exists():
            return cwd_candidate
        return base.joinpath(path).resolve()

    primary = (base / "config" / "stage05_route_registry.yaml").resolve()
    if primary.exists():
        return primary
    example = (base / "config" / "stage05_route_registry.example.yaml").resolve()
    if allow_example_fallback and example.exists():
        return example
    return primary


def load_stage05_route_registry(
    registry_path: str | Path | None = None,
    root: str | Path | None = None,
    *,
    allow_example_fallback: bool = False,
    validate: bool = True,
) -> tuple[dict[str, Any], Path]:
    path = resolve_stage05_route_registry_path(
        registry_path=registry_path,
        root=root,
        allow_example_fallback=allow_example_fallback,
    )
    if not path.exists():
        raise RouteRegistryError(
            f"stage05 route registry not found: {path}. "
            "config/stage05_route_registry.yaml is required for Stage 05 routing."
        )
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise RouteRegistryError(f"stage05 route registry is not valid YAML: {path}") from exc
    if not isinstance(data, dict):
        raise RouteRegistryError(f"stage05 route registry root must be an object: {path}")
    if validate:
        errors = validate_stage05_route_registry(data)
        if errors:
            joined = "\n".join(f"- {item}" for item in errors)
            raise RouteRegistryError(f"stage05 route registry is invalid: {path}\n{joined}")
    return data, path


def get_stage05_route_entry(data: dict[str, Any], route_key: str) -> dict[str, Any]:
    routes = data.get("routes")
    if not isinstance(routes, dict):
        raise RouteRegistryError("stage05 route registry must contain a top-level 'routes' object")
    entry = routes.get(route_key)
    if not isinstance(entry, dict):
        raise RouteRegistryError(f"stage05 route registry missing route entry: {route_key}")
    return entry


def get_stage05_route_for_style(data: dict[str, Any], normalized_style: str) -> tuple[str, dict[str, Any], dict[str, Any]]:
    mapping = data.get("stage00_style_to_route")
    if not isinstance(mapping, dict):
        raise RouteRegistryError("stage05 route registry must contain a top-level 'stage00_style_to_route' object")
    style_entry = mapping.get(normalized_style)
    if not isinstance(style_entry, dict):
        raise RouteRegistryError(f"stage05 route registry missing Stage 00 style mapping: {normalized_style}")
    route_key = str(style_entry.get("primary_route") or "").strip()
    if not route_key:
        raise RouteRegistryError(f"stage05 route registry has blank primary_route for style: {normalized_style}")
    return route_key, style_entry, get_stage05_route_entry(data, route_key)


def infer_legacy_style_family_from_workflow_name(workflow_name: str) -> str:
    name = str(workflow_name or "").strip().lower()
    if name.endswith("_anime"):
        return "anime"
    if name.endswith("_guofeng"):
        return "guofeng"
    if name.endswith("_stylized"):
        return "stylized"
    return "realistic"


def resolve_current_comfyui_target(route_key: str, route_entry: dict[str, Any]) -> dict[str, Any]:
    workflow_name = str(route_entry.get("current_workflow_target") or "").strip()
    workflow_mapping_key = str(route_entry.get("current_workflow_mapping_key") or "").strip() or workflow_name
    style_family = str(route_entry.get("style_family") or "").strip().lower()
    if style_family not in STYLE_FAMILIES:
        style_family = infer_legacy_style_family_from_workflow_name(workflow_name or workflow_mapping_key)
    model_id = str(route_entry.get("current_model_candidate") or "").strip() or None
    adoption_strategy = route_entry.get("adoption_strategy")
    preferred_workflow_candidate = None
    preferred_model_candidate = None
    migration_state = None
    preferred_workflow_source_ref = None
    preferred_workflow_format = None
    preferred_workflow_custom_node_dependencies: list[str] | None = None
    preferred_workflow_import_blockers: list[str] | None = None
    if isinstance(adoption_strategy, dict):
        preferred_workflow_candidate = str(adoption_strategy.get("preferred_workflow_candidate") or "").strip() or None
        preferred_model_candidate = str(adoption_strategy.get("preferred_model_candidate") or "").strip() or None
        migration_state = str(adoption_strategy.get("migration_state") or "").strip() or None
    workflow_candidates = route_entry.get("workflow_candidates")
    if preferred_workflow_candidate and isinstance(workflow_candidates, list):
        for item in workflow_candidates:
            if not isinstance(item, dict):
                continue
            candidate_workflow_name = str(item.get("workflow_name") or "").strip()
            if candidate_workflow_name != preferred_workflow_candidate:
                continue
            preferred_workflow_source_ref = str(item.get("source_ref") or "").strip() or None
            preferred_workflow_format = str(item.get("workflow_format") or "").strip() or None
            custom_node_dependencies = item.get("custom_node_dependencies")
            if isinstance(custom_node_dependencies, list):
                preferred_workflow_custom_node_dependencies = [
                    str(dep).strip()
                    for dep in custom_node_dependencies
                    if _is_non_empty_str(dep)
                ]
            import_blockers = item.get("import_blockers")
            if isinstance(import_blockers, list):
                preferred_workflow_import_blockers = [
                    str(blocker).strip()
                    for blocker in import_blockers
                    if _is_non_empty_str(blocker)
                ]
            break
    return {
        "route_key": route_key,
        "workflow_name": workflow_name or workflow_mapping_key,
        "workflow_mapping_key": workflow_mapping_key or workflow_name,
        "style_family": style_family,
        "model_id": model_id,
        "preferred_workflow_candidate": preferred_workflow_candidate,
        "preferred_model_candidate": preferred_model_candidate,
        "migration_state": migration_state,
        "preferred_workflow_source_ref": preferred_workflow_source_ref,
        "preferred_workflow_format": preferred_workflow_format,
        "preferred_workflow_custom_node_dependencies": preferred_workflow_custom_node_dependencies,
        "preferred_workflow_import_blockers": preferred_workflow_import_blockers,
    }


def resolve_route_style_preset(style_entry: dict[str, Any], route_entry: dict[str, Any]) -> dict[str, Any]:
    preset_key = str(style_entry.get("route_preset") or "").strip() or None
    return resolve_named_style_preset(route_entry, preset_key)


def resolve_named_style_preset(route_entry: dict[str, Any], preset_key: str | None) -> dict[str, Any]:
    style_presets = route_entry.get("style_presets")
    if not preset_key or not isinstance(style_presets, dict):
        return {
            "preset_key": preset_key,
            "preset_label": None,
            "positive_anchor": None,
            "negative_anchor": None,
            "style_selector": None,
        }
    preset = style_presets.get(preset_key)
    if not isinstance(preset, dict):
        return {
            "preset_key": preset_key,
            "preset_label": None,
            "positive_anchor": None,
            "negative_anchor": None,
            "style_selector": None,
        }
    return {
        "preset_key": preset_key,
        "preset_label": str(preset.get("display_name") or "").strip() or None,
        "positive_anchor": str(preset.get("positive_anchor") or "").strip() or None,
        "negative_anchor": str(preset.get("negative_anchor") or "").strip() or None,
        "style_selector": str(preset.get("style_selector") or "").strip() or None,
    }


def _validate_route_candidate_list(
    route_key: str,
    label: str,
    items: Any,
    errors: list[str],
    *,
    status: str,
) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        errors.append(f"routes.{route_key}.{label} must be a list")
        return []
    if status != "backlog" and not items:
        errors.append(f"routes.{route_key}.{label} must be non-empty unless status=backlog")
        return []

    valid_items: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"routes.{route_key}.{label}[{index}] must be an object")
            continue
        if label == "workflow_candidates":
            _require_non_empty_str(item, "workflow_name", errors)
            _require_non_empty_str(item, "source_type", errors)
            _require_non_empty_str(item, "source_ref", errors)
            workflow_format = item.get("workflow_format")
            if workflow_format is not None and not _is_non_empty_str(workflow_format):
                errors.append(f"routes.{route_key}.{label}[{index}].workflow_format must be a non-empty string when provided")
            custom_node_dependencies = item.get("custom_node_dependencies")
            if custom_node_dependencies is not None:
                if not isinstance(custom_node_dependencies, list) or not all(_is_non_empty_str(dep) for dep in custom_node_dependencies):
                    errors.append(
                        f"routes.{route_key}.{label}[{index}].custom_node_dependencies must be a list of strings when provided"
                    )
            import_blockers = item.get("import_blockers")
            if import_blockers is not None:
                if not isinstance(import_blockers, list) or not all(_is_non_empty_str(dep) for dep in import_blockers):
                    errors.append(
                        f"routes.{route_key}.{label}[{index}].import_blockers must be a list of strings when provided"
                    )
        else:
            _require_non_empty_str(item, "model_id", errors)
            _require_non_empty_str(item, "source", errors)
            suitability = _require_non_empty_str(item, "suitability", errors)
            if suitability and suitability not in SUITABILITY_CLASSES:
                errors.append(
                    f"routes.{route_key}.{label}[{index}].suitability must be one of: {', '.join(sorted(SUITABILITY_CLASSES))}"
                )
        origin = item.get("origin")
        if origin is not None and not _is_non_empty_str(origin):
            errors.append(f"routes.{route_key}.{label}[{index}].origin must be a non-empty string when provided")
        stack_profile = item.get("stack_profile")
        if stack_profile is not None and not _is_non_empty_str(stack_profile):
            errors.append(f"routes.{route_key}.{label}[{index}].stack_profile must be a non-empty string when provided")
        adoption_state = item.get("adoption_state")
        if adoption_state is not None:
            if not _is_non_empty_str(adoption_state):
                errors.append(f"routes.{route_key}.{label}[{index}].adoption_state must be a non-empty string when provided")
            elif str(adoption_state).strip() not in ADOPTION_STATES:
                errors.append(
                    f"routes.{route_key}.{label}[{index}].adoption_state must be one of: {', '.join(sorted(ADOPTION_STATES))}"
                )
        evidence_refs = item.get("evidence_refs")
        if evidence_refs is not None:
            if not isinstance(evidence_refs, list) or not all(_is_non_empty_str(ref) for ref in evidence_refs):
                errors.append(f"routes.{route_key}.{label}[{index}].evidence_refs must be a list of strings when provided")
        priority = item.get("priority")
        if not isinstance(priority, int) or priority < 1:
            errors.append(f"routes.{route_key}.{label}[{index}].priority must be an integer >= 1")
        valid_items.append(item)
    return valid_items


def validate_stage05_route_registry(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    schema_version = data.get("schema_version")
    if not _is_non_empty_str(schema_version):
        errors.append("schema_version must be a non-empty string")

    stage05_policy = _require_object(data, "stage05_policy", errors)
    if stage05_policy:
        provider_order = _require_string_list(stage05_policy, "provider_order", errors)
        if provider_order and provider_order != EXPECTED_PROVIDER_ORDER:
            errors.append(
                "stage05_policy.provider_order must equal: "
                + " -> ".join(EXPECTED_PROVIDER_ORDER)
            )
        provider_routing_mode = _require_non_empty_str(stage05_policy, "provider_routing_mode", errors)
        if provider_routing_mode and provider_routing_mode != "availability_first":
            errors.append("stage05_policy.provider_routing_mode must be availability_first")
        comfyui_route_resolution = _require_non_empty_str(stage05_policy, "comfyui_route_resolution", errors)
        if comfyui_route_resolution and comfyui_route_resolution != "route_family_first":
            errors.append("stage05_policy.comfyui_route_resolution must be route_family_first")
        _require_string_list(stage05_policy, "notes", errors)

    stage00_style_to_route = _require_object(data, "stage00_style_to_route", errors)
    routes = _require_object(data, "routes", errors)
    route_keys = set(routes.keys()) if routes else set()

    if routes:
        for route_key, raw_entry in routes.items():
            if not isinstance(raw_entry, dict):
                errors.append(f"routes.{route_key} must be an object")
                continue
            _require_non_empty_str(raw_entry, "display_name", errors)
            status = _require_non_empty_str(raw_entry, "status", errors)
            if status and status not in ROUTE_STATUSES:
                errors.append(f"routes.{route_key}.status must be one of: {', '.join(sorted(ROUTE_STATUSES))}")
            style_family = _require_non_empty_str(raw_entry, "style_family", errors)
            if style_family and style_family not in STYLE_FAMILIES:
                errors.append(f"routes.{route_key}.style_family must be one of: {', '.join(sorted(STYLE_FAMILIES))}")
            _require_non_empty_str(raw_entry, "maturity", errors)
            suitable_styles = _require_string_list(raw_entry, "suitable_stage00_styles", errors)
            current_workflow_mapping_key = str(raw_entry.get("current_workflow_mapping_key") or "").strip()
            if status != "backlog" and not current_workflow_mapping_key:
                errors.append(f"routes.{route_key}.current_workflow_mapping_key must be non-empty unless status=backlog")
            current_workflow_target = str(raw_entry.get("current_workflow_target") or "").strip()
            if status != "backlog" and not current_workflow_target:
                errors.append(f"routes.{route_key}.current_workflow_target must be non-empty unless status=backlog")
            current_model_candidate = str(raw_entry.get("current_model_candidate") or "").strip()
            if status != "backlog" and not current_model_candidate:
                errors.append(f"routes.{route_key}.current_model_candidate must be non-empty unless status=backlog")
            adoption_strategy = raw_entry.get("adoption_strategy")
            preferred_workflow_candidate = ""
            preferred_model_candidate = ""
            if adoption_strategy is not None:
                if not isinstance(adoption_strategy, dict):
                    errors.append(f"routes.{route_key}.adoption_strategy must be an object")
                else:
                    policy = _require_non_empty_str(adoption_strategy, "community_preference_policy", errors)
                    if policy and policy not in COMMUNITY_PREFERENCE_POLICIES:
                        errors.append(
                            "routes."
                            f"{route_key}.adoption_strategy.community_preference_policy must be one of: "
                            + ", ".join(sorted(COMMUNITY_PREFERENCE_POLICIES))
                        )
                    preferred_workflow_candidate = _require_non_empty_str(adoption_strategy, "preferred_workflow_candidate", errors)
                    preferred_model_candidate = _require_non_empty_str(adoption_strategy, "preferred_model_candidate", errors)
                    migration_state = _require_non_empty_str(adoption_strategy, "migration_state", errors)
                    if migration_state and migration_state not in ROUTE_MIGRATION_STATES:
                        errors.append(
                            f"routes.{route_key}.adoption_strategy.migration_state must be one of: "
                            + ", ".join(sorted(ROUTE_MIGRATION_STATES))
                        )
                    _require_string_list(adoption_strategy, "notes", errors, allow_empty=True)
            workflow_candidates = _validate_route_candidate_list(
                route_key,
                "workflow_candidates",
                raw_entry.get("workflow_candidates"),
                errors,
                status=status or "",
            )
            model_candidates = _validate_route_candidate_list(
                route_key,
                "model_candidates",
                raw_entry.get("model_candidates"),
                errors,
                status=status or "",
            )
            style_presets = raw_entry.get("style_presets")
            if style_presets is not None:
                if not isinstance(style_presets, dict) or not style_presets:
                    errors.append(f"routes.{route_key}.style_presets must be a non-empty object when provided")
                else:
                    for preset_key, preset_entry in style_presets.items():
                        if not _is_non_empty_str(preset_key):
                            errors.append(f"routes.{route_key}.style_presets contains a blank preset key")
                            continue
                        if not isinstance(preset_entry, dict):
                            errors.append(f"routes.{route_key}.style_presets.{preset_key} must be an object")
                            continue
                        _require_non_empty_str(preset_entry, "display_name", errors)
                        _require_non_empty_str(preset_entry, "positive_anchor", errors)
                        negative_anchor = preset_entry.get("negative_anchor")
                        if negative_anchor is not None and not _is_non_empty_str(negative_anchor):
                            errors.append(
                                f"routes.{route_key}.style_presets.{preset_key}.negative_anchor must be a non-empty string when provided"
                            )
                        notes = preset_entry.get("notes")
                        if notes is not None and (not isinstance(notes, list) or not all(_is_non_empty_str(item) for item in notes)):
                            errors.append(
                                f"routes.{route_key}.style_presets.{preset_key}.notes must be a list of strings when provided"
                            )
            if current_workflow_target and workflow_candidates:
                names = {str(item.get("workflow_name") or "").strip() for item in workflow_candidates if isinstance(item, dict)}
                if current_workflow_target not in names:
                    errors.append(
                        f"routes.{route_key}.current_workflow_target must match one workflow_candidates.workflow_name"
                    )
            if current_model_candidate and model_candidates:
                model_ids = {str(item.get("model_id") or "").strip() for item in model_candidates if isinstance(item, dict)}
                if current_model_candidate not in model_ids:
                    errors.append(
                        f"routes.{route_key}.current_model_candidate must match one model_candidates.model_id"
                    )
                if preferred_model_candidate and preferred_model_candidate not in model_ids:
                    errors.append(
                        f"routes.{route_key}.adoption_strategy.preferred_model_candidate must match one model_candidates.model_id"
                    )
            if preferred_workflow_candidate and workflow_candidates:
                workflow_names = {str(item.get("workflow_name") or "").strip() for item in workflow_candidates if isinstance(item, dict)}
                if preferred_workflow_candidate not in workflow_names:
                    errors.append(
                        f"routes.{route_key}.adoption_strategy.preferred_workflow_candidate must match one workflow_candidates.workflow_name"
                    )
            _require_string_list(raw_entry, "smoke_focus", errors)
            if suitable_styles and stage00_style_to_route:
                for style_name in suitable_styles:
                    if style_name not in stage00_style_to_route:
                        errors.append(
                            f"routes.{route_key}.suitable_stage00_styles references unknown Stage 00 style: {style_name}"
                        )

    if stage00_style_to_route:
        for style_name, raw_entry in stage00_style_to_route.items():
            if not isinstance(raw_entry, dict):
                errors.append(f"stage00_style_to_route.{style_name} must be an object")
                continue
            primary_route = _require_non_empty_str(raw_entry, "primary_route", errors)
            alternates = _require_string_list(raw_entry, "alternates", errors, allow_empty=True)
            route_preset = raw_entry.get("route_preset")
            if route_preset is not None and not _is_non_empty_str(route_preset):
                errors.append(f"stage00_style_to_route.{style_name}.route_preset must be a non-empty string when provided")
            if primary_route and primary_route not in route_keys:
                errors.append(f"stage00_style_to_route.{style_name}.primary_route references unknown route: {primary_route}")
            for route_key in alternates:
                if route_key not in route_keys:
                    errors.append(f"stage00_style_to_route.{style_name}.alternates references unknown route: {route_key}")
            if primary_route in route_keys:
                suitable_styles = data["routes"][primary_route].get("suitable_stage00_styles")
                if isinstance(suitable_styles, list) and style_name not in suitable_styles:
                    errors.append(
                        f"stage00_style_to_route.{style_name}.primary_route={primary_route} is missing this style in routes.{primary_route}.suitable_stage00_styles"
                    )
                if _is_non_empty_str(route_preset):
                    style_presets = data["routes"][primary_route].get("style_presets")
                    if not isinstance(style_presets, dict) or str(route_preset).strip() not in style_presets:
                        errors.append(
                            f"stage00_style_to_route.{style_name}.route_preset must match one routes.{primary_route}.style_presets key"
                        )

    special_validation = data.get("special_validation")
    if special_validation is not None:
        if not isinstance(special_validation, dict):
            errors.append("special_validation must be an object")
        else:
            dasiwa = special_validation.get("dasiwa")
            if dasiwa is not None:
                if not isinstance(dasiwa, dict):
                    errors.append("special_validation.dasiwa must be an object")
                else:
                    targets = _require_string_list(dasiwa, "target_routes", errors)
                    for route_key in targets:
                        if route_key not in route_keys:
                            errors.append(f"special_validation.dasiwa.target_routes references unknown route: {route_key}")
                    _require_non_empty_str(dasiwa, "status", errors)
                    hypothesis = _require_non_empty_str(dasiwa, "current_best_fit_hypothesis", errors)
                    if hypothesis and hypothesis not in SPECIAL_DASIWA_OUTCOMES:
                        errors.append(
                            "special_validation.dasiwa.current_best_fit_hypothesis must be one of: "
                            + ", ".join(sorted(SPECIAL_DASIWA_OUTCOMES))
                        )
                    _require_string_list(dasiwa, "public_reference", errors)
                    _require_string_list(dasiwa, "required_questions", errors)
                    outcomes = _require_string_list(dasiwa, "allowed_outcomes", errors)
                    if outcomes and set(outcomes) != SPECIAL_DASIWA_OUTCOMES:
                        errors.append(
                            "special_validation.dasiwa.allowed_outcomes must exactly contain: "
                            + ", ".join(sorted(SPECIAL_DASIWA_OUTCOMES))
                        )

    return errors
