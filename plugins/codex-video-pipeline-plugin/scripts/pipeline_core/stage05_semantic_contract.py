from __future__ import annotations

from typing import Any


def _non_empty_str(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [cleaned for item in value if (cleaned := _non_empty_str(item))]


def _shallow_object(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def load_stage05_semantic_contract(prompts: dict[str, Any]) -> dict[str, Any]:
    raw = prompts.get("stage05_semantic_contract")
    if not isinstance(raw, dict):
        return {}
    contract = {
        "mode": _non_empty_str(raw.get("mode")) or "codex_contract",
        "source": _non_empty_str(raw.get("source")),
        "defaults": _shallow_object(raw.get("defaults")),
        "provider_strategy": _shallow_object(raw.get("provider_strategy")),
        "bootstrap": _shallow_object(raw.get("bootstrap")),
        "jobs": {},
        "job_items": [],
    }
    for item in raw.get("jobs") or []:
        if not isinstance(item, dict):
            continue
        shot_id = _non_empty_str(item.get("shot_id"))
        frame_role = _non_empty_str(item.get("frame_role"))
        if not shot_id or not frame_role:
            continue
        normalized_item = dict(item)
        contract["jobs"][f"{shot_id}:{frame_role.lower()}"] = normalized_item
        contract["job_items"].append(normalized_item)
    return contract


def semantic_contract_summary(contract: dict[str, Any]) -> dict[str, Any]:
    jobs = contract.get("jobs") if isinstance(contract.get("jobs"), dict) else {}
    bootstrap = contract.get("bootstrap") if isinstance(contract.get("bootstrap"), dict) else {}
    defaults = contract.get("defaults") if isinstance(contract.get("defaults"), dict) else {}
    return {
        "mode": _non_empty_str(contract.get("mode")) or "legacy_python_fallback",
        "source": _non_empty_str(contract.get("source")) or "legacy_python_fallback",
        "defaults_defined": bool(defaults),
        "bootstrap_defined": bool(bootstrap),
        "job_contract_count": len(jobs),
    }


def defaults_contract(contract: dict[str, Any]) -> dict[str, Any]:
    return _shallow_object(contract.get("defaults"))


def provider_strategy_contract(contract: dict[str, Any]) -> dict[str, Any]:
    return _shallow_object(contract.get("provider_strategy"))


def bootstrap_contract(contract: dict[str, Any]) -> dict[str, Any]:
    return _shallow_object(contract.get("bootstrap"))


def job_contract(contract: dict[str, Any], shot_id: str, frame_role: str) -> dict[str, Any]:
    jobs = contract.get("jobs") if isinstance(contract.get("jobs"), dict) else {}
    return _shallow_object(jobs.get(f"{shot_id}:{frame_role.lower()}"))


def contract_job_items(contract: dict[str, Any]) -> list[dict[str, Any]]:
    raw_items = contract.get("job_items") if isinstance(contract.get("job_items"), list) else []
    return [dict(item) for item in raw_items if isinstance(item, dict)]


def apply_contract_overrides(base: dict[str, Any], overrides: dict[str, Any], *, allowed_keys: list[str]) -> dict[str, Any]:
    result = dict(base)
    for key in allowed_keys:
        if key not in overrides:
            continue
        value = overrides.get(key)
        if isinstance(value, str):
            cleaned = value.strip()
            if cleaned:
                result[key] = cleaned
        elif isinstance(value, (bool, int, float, list, dict)):
            result[key] = value
    return result


def contract_review_spec(job_contract_data: dict[str, Any]) -> dict[str, Any]:
    return _shallow_object(job_contract_data.get("review"))


def contract_repair_spec(job_contract_data: dict[str, Any]) -> dict[str, Any]:
    return _shallow_object(job_contract_data.get("repair"))


def contract_card_spec(job_contract_data: dict[str, Any]) -> dict[str, Any]:
    return _shallow_object(job_contract_data.get("review_card"))


def contract_provider_prompt(job_contract_data: dict[str, Any]) -> str | None:
    return _non_empty_str(job_contract_data.get("provider_prompt")) or _non_empty_str(job_contract_data.get("prompt"))


def contract_negative_prompt(job_contract_data: dict[str, Any]) -> str | None:
    return _non_empty_str(job_contract_data.get("negative_prompt"))


def contract_reference_images(job_contract_data: dict[str, Any]) -> list[str]:
    return _string_list(job_contract_data.get("reference_images"))
