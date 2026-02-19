"""Auto-detection of Zotero configuration from the local system.

Reads the Zotero data directory and SQLite databases to surface
values that would otherwise need to be supplied manually:

  - BetterBibTeX database path  (from OS default / prefs.js)
  - Zotero library ID           (from zotero.sqlite settings table)

The API key cannot be auto-detected and must always be supplied
by the user.

All reads are strictly read-only. No writes are performed.
"""

from __future__ import annotations

import configparser
import re
import sqlite3
import sys
from pathlib import Path
from typing import Optional


# ── Zotero data directory ─────────────────────────────────────────────────────

def find_zotero_data_dir() -> Optional[Path]:
    """Find the Zotero data directory for the current OS.

    Checks OS-default locations and, on Linux, parses profiles.ini to
    find the active profile. Returns None if nothing is found.
    """
    if sys.platform == "darwin":
        return _check(Path.home() / "Library" / "Application Support" / "Zotero")

    if sys.platform == "win32":
        appdata = Path.home() / "AppData" / "Roaming"
        return _check(appdata / "Zotero" / "Zotero")

    # Linux: Zotero uses a Firefox-style profile directory
    # The data dir is usually ~/.zotero/zotero/<profile>/
    # but may be overridden via prefs.js (extensions.zotero.dataDir)
    return _find_linux_data_dir()


def _check(path: Path) -> Optional[Path]:
    return path if path.is_dir() else None


def _find_linux_data_dir() -> Optional[Path]:
    """Locate the Zotero data dir on Linux via profiles.ini."""
    profiles_root = Path.home() / ".zotero" / "zotero"
    profiles_ini = profiles_root / "profiles.ini"

    if not profiles_ini.exists():
        return None

    # Parse the Firefox-style profiles.ini
    config = configparser.ConfigParser()
    config.read(profiles_ini)

    # Prefer the profile marked as Default=1, otherwise take the first
    chosen: Optional[str] = None
    for section in config.sections():
        if section.lower().startswith("profile"):
            if config.getboolean(section, "Default", fallback=False):
                chosen = config.get(section, "Path", fallback=None)
                break
            if chosen is None:
                chosen = config.get(section, "Path", fallback=None)

    if not chosen:
        return None

    profile_path = (
        Path(chosen)
        if Path(chosen).is_absolute()
        else profiles_root / chosen
    )

    # Check for a custom data dir in prefs.js
    prefs_js = profile_path / "prefs.js"
    if prefs_js.exists():
        custom = _read_pref(prefs_js, "extensions.zotero.dataDir")
        if custom:
            p = Path(custom)
            if p.is_dir():
                return p

    # Default: data lives directly in the profile dir
    return profile_path if profile_path.is_dir() else None


def _read_pref(prefs_js: Path, key: str) -> Optional[str]:
    """Extract a single string preference value from a Firefox prefs.js file."""
    pattern = re.compile(
        r'user_pref\("' + re.escape(key) + r'",\s*"([^"]+)"\)',
    )
    text = prefs_js.read_text(encoding="utf-8", errors="replace")
    m = pattern.search(text)
    return m.group(1) if m else None


# ── BetterBibTeX database ─────────────────────────────────────────────────────

def find_betterbibtex_db(data_dir: Optional[Path] = None) -> Optional[Path]:
    """Find the BetterBibTeX SQLite database.

    Looks in the provided data_dir, or falls back to auto-detecting
    the Zotero data directory.
    """
    if data_dir is None:
        data_dir = find_zotero_data_dir()
    if data_dir is None:
        return None
    candidate = data_dir / "better-bibtex.sqlite"
    return candidate if candidate.exists() else None


# ── Zotero library (user) ID ──────────────────────────────────────────────────

def find_library_id(data_dir: Optional[Path] = None) -> Optional[str]:
    """Read the Zotero web user ID from zotero.sqlite.

    The web user ID (used by the Zotero API) is stored in the settings
    table of the local Zotero SQLite database:

        SELECT value FROM settings WHERE setting='account' AND key='userID'

    Returns the ID as a string, or None if not found or not yet synced.
    """
    if data_dir is None:
        data_dir = find_zotero_data_dir()
    if data_dir is None:
        return None

    db_path = data_dir / "zotero.sqlite"
    if not db_path.exists():
        return None

    uri = f"file:{db_path}?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True)
        try:
            row = conn.execute(
                "SELECT value FROM settings WHERE setting='account' AND key='userID'"
            ).fetchone()
            return str(row[0]) if row else None
        finally:
            conn.close()
    except sqlite3.Error:
        return None


# ── Convenience: detect everything at once ────────────────────────────────────

def detect_defaults() -> dict[str, Optional[str]]:
    """Auto-detect all available configuration values.

    Returns a dict with keys:
        data_dir       - Zotero data directory path (str)
        betterbibtex   - BetterBibTeX database path (str)
        library_id     - Zotero web user ID (str)

    All values may be None if detection fails.
    """
    data_dir = find_zotero_data_dir()
    bbt = find_betterbibtex_db(data_dir)
    library_id = find_library_id(data_dir)

    return {
        "data_dir": str(data_dir) if data_dir else None,
        "betterbibtex": str(bbt) if bbt else None,
        "library_id": library_id,
    }
