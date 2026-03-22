"""Configuration management module."""

import json
from pathlib import Path
from typing import Any, Dict


def _normalize_github_entry(entry: Dict[str, Any], *, config_path: Path) -> Dict[str, str]:
    """Normalize one GitHub resource entry."""
    name = str(entry.get("name") or "").strip()
    api_key = str(entry.get("api_key") or "").strip()
    if not name:
        raise ValueError(f"Missing key in {config_path}: github[].name")
    if not api_key:
        raise ValueError(f"Missing key in {config_path}: github[].api_key")
    return {"name": name, "api_key": api_key}


def load_api_config(base_dir: Path) -> Dict[str, Any]:
    """
    Load API configuration from .secret/api.json.

    Args:
            base_dir: Base directory where .secret folder is located

    Returns:
            Configuration dictionary with api_url, model, api_key

    Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If required keys are missing or empty
            json.JSONDecodeError: If config file is not valid JSON
    """
    config_path = base_dir / ".secret" / "api.json"

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as file:
        config = json.load(file)

    normalized = _normalize_api_config(config, config_path=config_path)
    return normalized


def _normalize_api_config(config: Dict[str, Any], *, config_path: Path) -> Dict[str, Any]:
    """Normalize config into runtime keys used by the application."""
    if "openai" in config or "github" in config:
        return _normalize_nested_api_config(config, config_path=config_path)

    return _normalize_legacy_flat_config(config, config_path=config_path)


def _normalize_nested_api_config(
    config: Dict[str, Any], *, config_path: Path
) -> Dict[str, Any]:
    """Normalize nested config format with openai/github objects."""
    openai = config.get("openai")
    if not isinstance(openai, dict):
        raise ValueError(f"Missing or invalid object 'openai' in {config_path}")

    required_openai_keys = ["api_url", "model", "api_key"]
    missing_keys = [
        key for key in required_openai_keys if key not in openai or not openai[key]
    ]
    if missing_keys:
        missing = ", ".join(f"openai.{key}" for key in missing_keys)
        raise ValueError(f"Missing keys in {config_path}: {missing}")

    github = config.get("github", {})
    if github is None:
        github = {}
    github_resources: list[Dict[str, str]] = []
    if isinstance(github, list):
        github_resources = [
            _normalize_github_entry(entry, config_path=config_path)
            for entry in github
            if isinstance(entry, dict)
        ]
        if len(github_resources) != len(github):
            raise ValueError(f"Invalid object in 'github' list in {config_path}")
    elif isinstance(github, dict):
        api_key = str(github.get("api_key") or "").strip()
        if api_key:
            github_resources = [{"name": "*", "api_key": api_key}]
    else:
        raise ValueError(f"Invalid object 'github' in {config_path}")

    return {
        "api_url": str(openai["api_url"]),
        "model": str(openai["model"]),
        "api_key": str(openai["api_key"]),
        "github_resources": github_resources,
    }


def _normalize_legacy_flat_config(
    config: Dict[str, Any], *, config_path: Path
) -> Dict[str, Any]:
    """Normalize legacy flat config format for backward compatibility."""
    required_keys = ["api_url", "model", "api_key"]
    missing_keys = [
        key for key in required_keys if key not in config or not config[key]
    ]

    if missing_keys:
        missing = ", ".join(missing_keys)
        raise ValueError(f"Missing keys in {config_path}: {missing}")

    return {
        "api_url": str(config["api_url"]),
        "model": str(config["model"]),
        "api_key": str(config["api_key"]),
        "github_resources": (
            [{"name": "*", "api_key": str(config.get("github_token") or "").strip()}]
            if str(config.get("github_token") or "").strip()
            else []
        ),
    }
