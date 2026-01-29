"""File-based configuration demonstrating filesystem dependency patterns.

This module shows configuration loading from files. Tests for file-based
config often become flaky because they:
- Depend on files existing at specific paths
- Can have conflicts between test environments
- May read stale or modified files
- Have different paths on different systems

Solutions:
1. pyfakefs - Complete filesystem virtualization
2. io.StringIO - In-memory file-like objects
3. mocker.patch("builtins.open") - Mock file operations
4. Embed test data as Python constants
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import (
    Any,
    TextIO,
)


@dataclass
class AppConfig:
    """Application configuration."""

    debug: bool = False
    log_level: str = "INFO"
    database_url: str = ""
    api_key: str = ""
    max_retries: int = 3
    timeout: float = 30.0


def load_config(path: str | Path) -> AppConfig:
    """Load configuration from a JSON file.

    This is the simple approach that causes filesystem dependency issues.

    Args:
        path: Path to the configuration file.

    Returns:
        AppConfig object with loaded values.

    Raises:
        FileNotFoundError: If the config file doesn't exist.
        json.JSONDecodeError: If the file isn't valid JSON.

    """
    path = Path(path)
    with path.open() as f:
        data = json.load(f)
    return _parse_config(data)


def load_config_from_stream(stream: TextIO) -> AppConfig:
    """Load configuration from a file-like object.

    This is the testable approach - accepts any file-like object.

    Args:
        stream: File-like object containing JSON config.

    Returns:
        AppConfig object with loaded values.

    """
    data = json.load(stream)
    return _parse_config(data)


def _parse_config(data: dict[str, Any]) -> AppConfig:
    """Parse configuration dictionary into AppConfig.

    Args:
        data: Configuration dictionary.

    Returns:
        AppConfig object.

    """
    return AppConfig(
        debug=data.get("debug", False),
        log_level=data.get("log_level", "INFO"),
        database_url=data.get("database_url", ""),
        api_key=data.get("api_key", ""),
        max_retries=data.get("max_retries", 3),
        timeout=data.get("timeout", 30.0),
    )


def save_config(config: AppConfig, path: str | Path) -> None:
    """Save configuration to a JSON file.

    Args:
        config: AppConfig object to save.
        path: Path to write the configuration file.

    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "debug": config.debug,
        "log_level": config.log_level,
        "database_url": config.database_url,
        "api_key": config.api_key,
        "max_retries": config.max_retries,
        "timeout": config.timeout,
    }

    with path.open("w") as f:
        json.dump(data, f, indent=2)


def get_config_path() -> Path:
    """Get the default configuration path.

    Returns:
        Path to the configuration file.

    """
    return Path("/etc/demo_app/config.json")
