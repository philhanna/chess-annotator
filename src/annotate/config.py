import json
import os
from pathlib import Path

_CONFIG_FILE = Path.home() / ".chess-annotate" / "config.json"
_DEFAULT_STORE = Path.home() / ".chess-annotate" / "store"


def get_store_dir() -> Path:
    """Resolve the annotation store directory.

    The lookup order is:
    1. ``CHESS_ANNOTATE_STORE`` environment variable
    2. ``~/.chess-annotate/config.json`` key ``"store_dir"``
    3. the built-in default ``~/.chess-annotate/store``

    Invalid or unreadable JSON configuration files are ignored so the
    application can continue using the fallback location.
    """
    env = os.environ.get("CHESS_ANNOTATE_STORE")
    if env:
        return Path(env)

    if _CONFIG_FILE.exists():
        try:
            data = json.loads(_CONFIG_FILE.read_text())
            if "store_dir" in data:
                return Path(data["store_dir"])
        except (json.JSONDecodeError, OSError):
            pass

    return _DEFAULT_STORE
