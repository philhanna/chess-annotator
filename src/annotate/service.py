"""Application service state for the annotate web app."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class SessionState:
    """Serializable high-level session state for the SPA."""

    app_name: str
    frontend_root: str
    source_name: str | None
    selected_game_index: int | None
    selected_ply: int | None
    unsaved_changes: bool
    status: str


class AnnotateSession:
    """Minimal session state for the initial annotate implementation slice."""

    def __init__(self, frontend_root: Path) -> None:
        self._frontend_root = frontend_root
        self._source_name: str | None = None
        self._selected_game_index: int | None = None
        self._selected_ply: int | None = None
        self._unsaved_changes = False

    @property
    def frontend_root(self) -> Path:
        """Return the configured frontend asset directory."""

        return self._frontend_root

    def snapshot(self) -> SessionState:
        """Return the current session state for JSON responses."""

        if self._source_name is None:
            status = "idle"
        else:
            status = "document-loaded"

        return SessionState(
            app_name="chess-annotate",
            frontend_root=str(self._frontend_root),
            source_name=self._source_name,
            selected_game_index=self._selected_game_index,
            selected_ply=self._selected_ply,
            unsaved_changes=self._unsaved_changes,
            status=status,
        )

