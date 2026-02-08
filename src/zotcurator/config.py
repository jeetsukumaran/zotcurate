"""Configuration resolution: CLI args > env vars > config files > defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

CONFIG_DIR_NAME = ".zotc"
ENV_LIBRARY_ID = "ZOTERO_LIBRARY_ID"
ENV_API_KEY = "ZOTERO_API_KEY"
ENV_LIBRARY_TYPE = "ZOTERO_LIBRARY_TYPE"


@dataclass(frozen=True, slots=True)
class Config:
    """Resolved application configuration."""

    library_id: Optional[str]
    api_key: Optional[str]
    library_type: str
    betterbibtex_db: Optional[Path]

    def require_library_id(self) -> str:
        if self.library_id is None:
            raise ConfigError(
                "Library ID required. Provide via -i/--library-id, "
                f"${ENV_LIBRARY_ID}, or {CONFIG_DIR_NAME}/library file."
            )
        return self.library_id

    def require_api_key(self) -> str:
        if self.api_key is None:
            raise ConfigError(
                "API key required. Provide via -k/--api-key, "
                f"${ENV_API_KEY}, or {CONFIG_DIR_NAME}/api-key file."
            )
        return self.api_key

    def require_betterbibtex_db(self) -> Path:
        if self.betterbibtex_db is None:
            raise ConfigError(
                "BetterBibTeX database path required. "
                "Provide via -b/--better-bibtex."
            )
        db = self.betterbibtex_db
        if not db.exists():
            raise ConfigError(f"BetterBibTeX database not found: {db}")
        return db


class ConfigError(Exception):
    """Raised when required configuration is missing or invalid."""


def _read_config_file(name: str) -> Optional[str]:
    """Read a single-line value from config files, checking ./.zotc/ then ~/.zotc/."""
    candidates = [
        Path.cwd() / CONFIG_DIR_NAME / name,
        Path.home() / CONFIG_DIR_NAME / name,
    ]
    for path in candidates:
        if path.is_file():
            content = path.read_text().strip()
            if content:
                return content
    return None


def resolve_config(
    *,
    cli_library_id: Optional[str] = None,
    cli_api_key: Optional[str] = None,
    cli_library_type: Optional[str] = None,
    cli_betterbibtex: Optional[str] = None,
) -> Config:
    """Resolve configuration from CLI args > env vars > config files > defaults."""
    library_id = (
        cli_library_id
        or os.environ.get(ENV_LIBRARY_ID)
        or _read_config_file("library")
    )
    api_key = (
        cli_api_key
        or os.environ.get(ENV_API_KEY)
        or _read_config_file("api-key")
    )
    library_type = (
        cli_library_type
        or os.environ.get(ENV_LIBRARY_TYPE)
        or _read_config_file("library-type")
        or "user"
    )
    betterbibtex_db: Optional[Path] = None
    if cli_betterbibtex:
        betterbibtex_db = Path(cli_betterbibtex).expanduser().resolve()

    return Config(
        library_id=library_id,
        api_key=api_key,
        library_type=library_type,
        betterbibtex_db=betterbibtex_db,
    )
