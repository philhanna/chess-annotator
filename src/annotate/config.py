import os
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml


def config_dir() -> Path:
    """Return the platform-appropriate config directory for chess-annotator.

    Follows the XDG Base Directory Specification on Linux and macOS:
    ``$XDG_CONFIG_HOME/chess-annotator`` when the variable is set, otherwise
    ``~/.config/chess-annotator``. On Windows the standard location is
    ``%APPDATA%\\chess-annotator``.
    """
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "chess-annotator"
        # Fallback when APPDATA is not set (unusual but possible).
        return Path.home() / "AppData" / "Roaming" / "chess-annotator"
    # XDG-compliant path; fall back to the default ~/.config location.
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg) / "chess-annotator"
    return Path.home() / ".config" / "chess-annotator"


def default_store_dir() -> Path:
    """Return the platform-appropriate default store directory for chess-annotator.

    Follows the XDG Base Directory Specification on Linux and macOS:
    ``$XDG_DATA_HOME/chess-annotator/store`` when the variable is set, otherwise
    ``~/.local/share/chess-annotator/store``. On Windows the default is
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

    All fields reflect the final value after merging the config file with
    built-in defaults. ``store_dir`` additionally honours the
    ``CHESS_ANNOTATE_STORE`` environment variable, which takes precedence
    over everything else.
    """

    store_dir: Path
    author: str | None = None
    diagram_size: int = 360
    page_size: str = "a4"
    server_url: str = "http://127.0.0.1:8765"


def get_config() -> Config:
    """Load and return the fully-resolved application configuration.

    Resolution order for ``store_dir``:

    1. ``CHESS_ANNOTATE_STORE`` environment variable.
    2. ``store_dir`` key in the platform config file.
    3. Built-in platform default (see ``default_store_dir``).

    ``author``, ``diagram_size``, and ``page_size`` are taken from the config file
    when present; built-in defaults apply otherwise (``None``, ``360``, ``"a4"``).
    An unreadable or malformed config file is silently ignored so the application
    can always start with sensible defaults.
    """
    file_data: dict = {}
    config_file = config_dir() / "config.yaml"
    if config_file.exists():
        try:
            file_data = yaml.safe_load(config_file.read_text()) or {}
        except (yaml.YAMLError, OSError):
            # Silently ignore a broken config file; defaults will be used.
            pass

    # Determine store_dir using the three-level resolution order.
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
        server_url=str(file_data.get("server_url", "http://127.0.0.1:8765")),
    )


def get_store_dir() -> Path:
    """Convenience wrapper that returns only the resolved store directory path."""
    return get_config().store_dir
