import os
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml


def config_dir() -> Path:
    """Return the platform config directory for chess-annotator.

    On Linux and macOS the XDG Base Directory Specification is followed:
    ``$XDG_CONFIG_HOME/chess-annotator`` when the variable is set, otherwise
    ``~/.config/chess-annotator``.  On Windows the standard location is
    ``%APPDATA%\\chess-annotator``.
    """
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "chess-annotator"
        return Path.home() / "AppData" / "Roaming" / "chess-annotator"
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg) / "chess-annotator"
    return Path.home() / ".config" / "chess-annotator"


def default_store_dir() -> Path:
    """Return the built-in default store directory for the current platform.

    On Linux and macOS this follows the XDG Base Directory Specification:
    ``$XDG_DATA_HOME/chess-annotator/store`` when the variable is set, otherwise
    ``~/.local/share/chess-annotator/store``.  On Windows the default is
    ``%LOCALAPPDATA%\\chess-annotator\\store``.
    """
    if sys.platform == "win32":
        localappdata = os.environ.get("LOCALAPPDATA")
        if localappdata:
            return Path(localappdata) / "chess-annotator" / "store"
        return Path.home() / "AppData" / "Local" / "chess-annotator" / "store"
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg) / "chess-annotator" / "store"
    return Path.home() / ".local" / "share" / "chess-annotator" / "store"


@dataclass
class Config:
    """Resolved application configuration.

    All fields reflect the final resolved value after applying the
    config file and built-in defaults.  ``store_dir`` additionally
    honours the ``CHESS_ANNOTATE_STORE`` environment variable, which
    takes precedence over everything else.
    """

    store_dir: Path
    author: str | None = None
    diagram_size: int = 360
    page_size: str = "a4"


def get_config() -> Config:
    """Load and return the full application configuration.

    Resolution order for ``store_dir``:

    1. ``CHESS_ANNOTATE_STORE`` environment variable
    2. ``store_dir`` key in the platform config file
    3. Built-in platform default

    ``author``, ``diagram_size``, and ``page_size`` are taken from the
    config file when present, otherwise the built-in defaults apply
    (``None``, ``360``, and ``"a4"`` respectively).

    Invalid or unreadable config files are silently ignored so the
    application continues using built-in defaults.
    """
    file_data: dict = {}
    config_file = config_dir() / "config.yaml"
    if config_file.exists():
        try:
            file_data = yaml.safe_load(config_file.read_text()) or {}
        except (yaml.YAMLError, OSError):
            pass

    env_store = os.environ.get("CHESS_ANNOTATE_STORE")
    if env_store:
        store_dir = Path(env_store).expanduser()
    elif "store_dir" in file_data:
        store_dir = Path(file_data["store_dir"]).expanduser()
    else:
        store_dir = default_store_dir()

    return Config(
        store_dir=store_dir,
        author=file_data.get("author") or None,
        diagram_size=int(file_data.get("diagram_size", 360)),
        page_size=str(file_data.get("page_size", "a4")).lower(),
    )


def get_store_dir() -> Path:
    """Convenience wrapper returning only the resolved store directory."""
    return get_config().store_dir
