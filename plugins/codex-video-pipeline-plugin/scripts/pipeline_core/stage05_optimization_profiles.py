from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml


class Stage05OptimizationError(RuntimeError):
    pass


def root_dir() -> Path:
    return Path(__file__).resolve().parents[2]


def _is_non_empty_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def resolve_stage05_optimization_profiles_path(
    config_path: str | Path | None = None,
    root: str | Path | None = None,
    *,
    allow_example_fallback: bool = False,
) -> Path:
    base = Path(root) if root else root_dir()
    if config_path is not None:
        path = Path(config_path)
        if path.is_absolute():
            return path.resolve()
        if path.exists():
            return path.resolve()
        cwd_candidate = (Path.cwd() / path).resolve()
        if cwd_candidate.exists():
            return cwd_candidate
        return (base / path).resolve()

    primary = (base / "config" / "stage05_optimization_profiles.yaml").resolve()
    if primary.exists():
        return primary
    example = (base / "config" / "stage05_optimization_profiles.example.yaml").resolve()
    if allow_example_fallback and example.exists():
        return example
    return primary


def validate_stage05_optimization_profiles(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not _is_non_empty_str(data.get("schema_version")):
        errors.append("schema_version must be a non-empty string")

    catalog = data.get("profile_catalog")
    if not isinstance(catalog, dict) or not catalog:
        errors.append("profile_catalog must be a non-empty object")
        catalog = {}
    else:
        for profile_key, profile_entry in catalog.items():
            if not _is_non_empty_str(profile_key):
                errors.append("profile_catalog contains a blank profile key")
                continue
            if not isinstance(profile_entry, dict):
                errors.append(f"profile_catalog.{profile_key} must be an object")
                continue
            if not _is_non_empty_str(profile_entry.get("display_name")):
                errors.append(f"profile_catalog.{profile_key}.display_name must be a non-empty string")
            description = profile_entry.get("description")
            if description is not None and not _is_non_empty_str(description):
                errors.append(f"profile_catalog.{profile_key}.description must be a non-empty string when provided")

    default_profile = data.get("default_profile")
    if not _is_non_empty_str(default_profile):
        errors.append("default_profile must be a non-empty string")
    elif catalog and str(default_profile).strip() not in catalog:
        errors.append("default_profile must exist in profile_catalog")

    workflow_profiles = data.get("workflow_profiles")
    if not isinstance(workflow_profiles, dict) or not workflow_profiles:
        errors.append("workflow_profiles must be a non-empty object")
        return errors

    for workflow_key, workflow_entry in workflow_profiles.items():
        if not _is_non_empty_str(workflow_key):
            errors.append("workflow_profiles contains a blank workflow key")
            continue
        if not isinstance(workflow_entry, dict):
            errors.append(f"workflow_profiles.{workflow_key} must be an object")
            continue
        inherits = workflow_entry.get("inherits")
        if inherits is not None and not _is_non_empty_str(inherits):
            errors.append(f"workflow_profiles.{workflow_key}.inherits must be a non-empty string when provided")
        default = workflow_entry.get("default_profile")
        if default is not None and not _is_non_empty_str(default):
            errors.append(f"workflow_profiles.{workflow_key}.default_profile must be a non-empty string when provided")
        elif _is_non_empty_str(default) and catalog and str(default).strip() not in catalog:
            errors.append(f"workflow_profiles.{workflow_key}.default_profile must exist in profile_catalog")
        profiles = workflow_entry.get("profiles")
        if profiles is not None and not isinstance(profiles, dict):
            errors.append(f"workflow_profiles.{workflow_key}.profiles must be an object when provided")
            continue
        if isinstance(profiles, dict):
            for profile_key, profile_entry in profiles.items():
                if not _is_non_empty_str(profile_key):
                    errors.append(f"workflow_profiles.{workflow_key}.profiles contains a blank profile key")
                    continue
                if catalog and profile_key not in catalog:
                    errors.append(
                        f"workflow_profiles.{workflow_key}.profiles.{profile_key} must exist in profile_catalog"
                    )
                if not isinstance(profile_entry, dict):
                    errors.append(f"workflow_profiles.{workflow_key}.profiles.{profile_key} must be an object")
                    continue
                for numeric_key in ["dimension_scale"]:
                    value = profile_entry.get(numeric_key)
                    if value is not None and not isinstance(value, (int, float)):
                        errors.append(
                            f"workflow_profiles.{workflow_key}.profiles.{profile_key}.{numeric_key} must be numeric when provided"
                        )
                    elif isinstance(value, (int, float)) and value <= 0:
                        errors.append(
                            f"workflow_profiles.{workflow_key}.profiles.{profile_key}.{numeric_key} must be > 0"
                        )
                for int_key in ["round_to_multiple", "max_width", "max_height"]:
                    value = profile_entry.get(int_key)
                    if value is not None and (not isinstance(value, int) or value <= 0):
                        errors.append(
                            f"workflow_profiles.{workflow_key}.profiles.{profile_key}.{int_key} must be an integer > 0 when provided"
                        )
                workflow_replacements = profile_entry.get("workflow_replacements")
                if workflow_replacements is not None:
                    if not isinstance(workflow_replacements, dict):
                        errors.append(
                            f"workflow_profiles.{workflow_key}.profiles.{profile_key}.workflow_replacements must be an object when provided"
                        )
                    else:
                        for replacement_key, replacement_value in workflow_replacements.items():
                            if not _is_non_empty_str(replacement_key):
                                errors.append(
                                    f"workflow_profiles.{workflow_key}.profiles.{profile_key}.workflow_replacements contains a blank key"
                                )
                            elif not isinstance(replacement_value, (str, int, float, bool)):
                                errors.append(
                                    f"workflow_profiles.{workflow_key}.profiles.{profile_key}.workflow_replacements.{replacement_key} must be a scalar"
                                )
                notes = profile_entry.get("notes")
                if notes is not None and (not isinstance(notes, list) or not all(_is_non_empty_str(item) for item in notes)):
                    errors.append(
                        f"workflow_profiles.{workflow_key}.profiles.{profile_key}.notes must be a list of non-empty strings when provided"
                    )
    return errors


def load_stage05_optimization_profiles(
    config_path: str | Path | None = None,
    root: str | Path | None = None,
    *,
    allow_example_fallback: bool = False,
    validate: bool = True,
) -> tuple[dict[str, Any], Path]:
    path = resolve_stage05_optimization_profiles_path(
        config_path=config_path,
        root=root,
        allow_example_fallback=allow_example_fallback,
    )
    if not path.exists():
        raise Stage05OptimizationError(
            f"stage05 optimization profiles not found: {path}. "
            "config/stage05_optimization_profiles.yaml is required for Stage 05 optimization."
        )
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise Stage05OptimizationError(f"stage05 optimization profiles are not valid YAML: {path}") from exc
    if not isinstance(data, dict):
        raise Stage05OptimizationError(f"stage05 optimization profiles root must be an object: {path}")
    if validate:
        errors = validate_stage05_optimization_profiles(data)
        if errors:
            joined = "\n".join(f"- {item}" for item in errors)
            raise Stage05OptimizationError(f"stage05 optimization profiles are invalid: {path}\n{joined}")
    return data, path


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def _resolve_workflow_entry(
    workflow_profiles: dict[str, Any],
    workflow_mapping_key: str,
    *,
    stack: tuple[str, ...] = (),
) -> dict[str, Any]:
    entry = workflow_profiles.get(workflow_mapping_key)
    if not isinstance(entry, dict):
        raise Stage05OptimizationError(f"stage05 optimization profiles missing workflow entry: {workflow_mapping_key}")
    if workflow_mapping_key in stack:
        cycle = " -> ".join([*stack, workflow_mapping_key])
        raise Stage05OptimizationError(f"stage05 optimization profile inheritance cycle detected: {cycle}")
    inherits = str(entry.get("inherits") or "").strip()
    if not inherits:
        return deepcopy(entry)
    parent = _resolve_workflow_entry(workflow_profiles, inherits, stack=(*stack, workflow_mapping_key))
    return _deep_merge(parent, entry)


def resolve_stage05_workflow_optimization(
    data: dict[str, Any],
    workflow_mapping_key: str,
    *,
    requested_profile: str | None = None,
) -> dict[str, Any]:
    workflow_profiles = data.get("workflow_profiles")
    if not isinstance(workflow_profiles, dict):
        raise Stage05OptimizationError("stage05 optimization profiles must contain workflow_profiles")
    catalog = data.get("profile_catalog")
    if not isinstance(catalog, dict):
        raise Stage05OptimizationError("stage05 optimization profiles must contain profile_catalog")

    merged_entry = _resolve_workflow_entry(workflow_profiles, workflow_mapping_key)
    profile_key = str(requested_profile or merged_entry.get("default_profile") or data.get("default_profile") or "").strip()
    if not profile_key:
        raise Stage05OptimizationError(f"stage05 optimization profile is blank for workflow: {workflow_mapping_key}")
    profile_catalog_entry = catalog.get(profile_key)
    if not isinstance(profile_catalog_entry, dict):
        raise Stage05OptimizationError(f"stage05 optimization profile is not declared in profile_catalog: {profile_key}")
    profiles = merged_entry.get("profiles")
    if not isinstance(profiles, dict):
        raise Stage05OptimizationError(f"stage05 optimization workflow entry has no profiles: {workflow_mapping_key}")
    profile_entry = profiles.get(profile_key)
    if not isinstance(profile_entry, dict):
        raise Stage05OptimizationError(
            f"stage05 optimization workflow '{workflow_mapping_key}' does not define profile '{profile_key}'"
        )
    return {
        "workflow_mapping_key": workflow_mapping_key,
        "profile_key": profile_key,
        "profile_label": str(profile_catalog_entry.get("display_name") or "").strip(),
        "profile_description": str(profile_catalog_entry.get("description") or "").strip() or None,
        "dimension_scale": float(profile_entry.get("dimension_scale") or 1.0),
        "round_to_multiple": int(profile_entry.get("round_to_multiple") or 64),
        "max_width": int(profile_entry["max_width"]) if isinstance(profile_entry.get("max_width"), int) else None,
        "max_height": int(profile_entry["max_height"]) if isinstance(profile_entry.get("max_height"), int) else None,
        "workflow_replacements": deepcopy(profile_entry.get("workflow_replacements") or {}),
        "notes": [str(item).strip() for item in profile_entry.get("notes") or [] if _is_non_empty_str(item)],
    }
