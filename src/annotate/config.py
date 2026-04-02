# annotate.config
import os
import sys
from pathlib import Path

import yaml


def _config_dir() -> Path:
    """Return the platform config directory for chess-plan.

    On Linux and macOS the XDG Base Directory Specification is followed:
    ``$XDG_CONFIG_HOME/chess-plan`` when the variable is set, otherwise
    ``~/.config/chess-plan``.  On Windows the standard location is
    ``%APPDATA%\\chess-plan``.
    """
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "chess-plan"
        return Path.home() / "AppData" / "Roaming" / "chess-plan"
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg) / "chess-plan"
    return Path.home() / ".config" / "chess-plan"


def _default_store_dir() -> Path:
    """Return the built-in default store directory for the current platform.

    On Linux and macOS this follows the XDG Base Directory Specification:
    ``$XDG_DATA_HOME/chess-plan/store`` when the variable is set, otherwise
    ``~/.local/share/chess-plan/store``.  On Windows the default is
    ``%LOCALAPPDATA%\\chess-plan\\store``.
    """
    if sys.platform == "win32":
        localappdata = os.environ.get("LOCALAPPDATA")
        if localappdata:
            return Path(localappdata) / "chess-plan" / "store"
        return Path.home() / "AppData" / "Local" / "chess-plan" / "store"
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg) / "chess-plan" / "store"
    return Path.home() / ".local" / "share" / "chess-plan" / "store"


def get_store_dir() -> Path:
    """Resolve the annotation store directory.

    The lookup order is:

    1. ``CHESS_ANNOTATE_STORE`` environment variable
    2. ``store_dir`` key in the platform config file
       (``~/.config/chess-plan/config.yaml`` on Linux/macOS,
       ``%APPDATA%\\chess-plan\\config.yaml`` on Windows)
    3. Built-in platform default

    Invalid or unreadable config files are silently ignored so the
    application continues using the default location.
    """
    env = os.environ.get("CHESS_ANNOTATE_STORE")
    if env:
        return Path(env)

    config_file = _config_dir() / "config.yaml"
    if config_file.exists():
        try:
            data = yaml.safe_load(config_file.read_text()) or {}
            if "store_dir" in data:
                return Path(data["store_dir"])
        except (yaml.YAMLError, OSError):
            pass

    return _default_store_dir()
