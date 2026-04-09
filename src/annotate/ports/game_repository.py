from abc import ABC, abstractmethod

from annotate.domain.annotation import Annotation


# Type alias for values accepted wherever a game identifier is expected.
GameKey = str | int


class GameRepository(ABC):
    """Port defining all persistence operations for annotated games.

    Each game is stored in its own isolated location identified by a ``GameKey``.
    The repository supports two file states per game:

    * **Canonical files** — the authoritative, last-saved version of the game.
    * **Working-copy files** — a parallel set written during an open session,
      accumulating edits that have not yet been committed back to the canonical
      files. The presence of working files signals that a session is in progress.

    Implementations are responsible for serialisation, file layout, and
    validation; the domain and use-case layers interact only with this interface.
    """

    @abstractmethod
    def save(self, annotation: Annotation) -> None:
        """Persist ``annotation`` to the canonical store, overwriting any existing files."""
        ...

    @abstractmethod
    def exists(self, game_id: GameKey) -> bool:
        """Return True when ``game_id`` exists in the canonical store."""
        ...

    @abstractmethod
    def load(self, game_id: GameKey) -> Annotation:
        """Load and return the canonical ``Annotation`` for ``game_id``."""
        ...

    @abstractmethod
    def list_all(self) -> list[tuple[str, str]]:
        """Return ``(game_id, title)`` pairs for every canonical game, sorted by game id."""
        ...

    @abstractmethod
    def exists_working_copy(self, game_id: GameKey) -> bool:
        """Return True when ``game_id`` currently has working-copy files."""
        ...

    @abstractmethod
    def save_working_copy(self, annotation: Annotation) -> None:
        """Write ``annotation`` to the working-copy files, creating them if absent."""
        ...

    @abstractmethod
    def load_working_copy(self, game_id: GameKey) -> Annotation:
        """Load and return the working-copy ``Annotation`` for ``game_id``."""
        ...

    @abstractmethod
    def discard_working_copy(self, game_id: GameKey) -> None:
        """Delete the working-copy files for ``game_id``, if they exist."""
        ...

    @abstractmethod
    def commit_working_copy(self, game_id: GameKey) -> None:
        """Overwrite the canonical files with the working-copy files.

        The working-copy files are left in place after the commit so that the
        session can continue without interruption.
        """
        ...

    @abstractmethod
    def has_unsaved_working_copy(self, game_id: GameKey) -> bool:
        """Return True when the working-copy files differ from the canonical files."""
        ...

    @abstractmethod
    def stale_working_copies(self) -> list[str]:
        """Return the game ids of every game that currently has working-copy files.

        Used at startup to detect sessions that were interrupted before the user
        had a chance to close them cleanly.
        """
        ...

    @abstractmethod
    def delete(self, game_id: GameKey) -> None:
        """Permanently delete a game and all its associated files from the store."""
        ...
