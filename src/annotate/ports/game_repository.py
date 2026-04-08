from abc import ABC, abstractmethod

from annotate.domain.annotation import Annotation


GameKey = str | int


class GameRepository(ABC):
    """Define persistence operations for annotated games.

    The design stores each game as a directory containing:

    - ``annotated.pgn`` for turning-point markers
    - ``annotation.json`` for segment content and metadata
    - optional ``.work`` copies while a session is open
    """

    @abstractmethod
    def save(self, annotation: Annotation) -> None:
        """Persist ``annotation`` to the canonical store."""
        ...

    @abstractmethod
    def exists(self, game_id: GameKey) -> bool:
        """Return whether ``game_id`` exists in the canonical store."""
        ...

    @abstractmethod
    def load(self, game_id: GameKey) -> Annotation:
        """Load and return one saved game from the canonical store."""
        ...

    @abstractmethod
    def list_all(self) -> list[tuple[str, str]]:
        """Return ``(game_id, title)`` pairs for all saved games, sorted by game id."""
        ...

    @abstractmethod
    def exists_working_copy(self, game_id: GameKey) -> bool:
        """Return whether ``game_id`` currently has working files."""
        ...

    @abstractmethod
    def save_working_copy(self, annotation: Annotation) -> None:
        """Write ``annotation`` to the working-copy files."""
        ...

    @abstractmethod
    def load_working_copy(self, game_id: GameKey) -> Annotation:
        """Load and return the working copy for ``game_id``."""
        ...

    @abstractmethod
    def discard_working_copy(self, game_id: GameKey) -> None:
        """Delete the working files for ``game_id`` if present."""
        ...

    @abstractmethod
    def commit_working_copy(self, game_id: GameKey) -> None:
        """Overwrite the canonical files from the working files; leave the working files in place."""
        ...

    @abstractmethod
    def has_unsaved_working_copy(self, game_id: GameKey) -> bool:
        """Return whether the working files differ from the main files."""
        ...

    @abstractmethod
    def stale_working_copies(self) -> list[str]:
        """Return the game ids of all games that currently have working files.

        Used at startup to detect sessions that were interrupted before the
        user had a chance to close them.
        """
        ...

    @abstractmethod
    def delete(self, game_id: GameKey) -> None:
        """Delete a game directory and all files within it."""
        ...
