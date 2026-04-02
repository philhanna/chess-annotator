# chess_annotate.ports.editor_launcher
from __future__ import annotations

from abc import ABC, abstractmethod


class EditorLauncher(ABC):

    @abstractmethod
    def edit(self, initial_text: str) -> str:
        """Open the text in an external editor and return the saved result."""
        ...
