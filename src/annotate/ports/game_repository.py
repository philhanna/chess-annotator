from abc import ABC, abstractmethod

from annotate.domain.annotation import Annotation


GameKey = str | int


class GameRepository(ABC):
    @abstractmethod
    def save(self, annotation: Annotation) -> None:
        ...

    @abstractmethod
    def exists(self, game_id: GameKey) -> bool:
        ...

    @abstractmethod
    def load(self, game_id: GameKey) -> Annotation:
        ...

    @abstractmethod
    def list_all(self) -> list[tuple[str, str]]:
        ...

    @abstractmethod
    def exists_working_copy(self, game_id: GameKey) -> bool:
        ...

    @abstractmethod
    def save_working_copy(self, annotation: Annotation) -> None:
        ...

    @abstractmethod
    def load_working_copy(self, game_id: GameKey) -> Annotation:
        ...

    @abstractmethod
    def discard_working_copy(self, game_id: GameKey) -> None:
        ...

    @abstractmethod
    def commit_working_copy(self, game_id: GameKey) -> None:
        ...

    @abstractmethod
    def has_unsaved_working_copy(self, game_id: GameKey) -> bool:
        ...

    @abstractmethod
    def stale_working_copies(self) -> list[str]:
        ...

    @abstractmethod
    def delete(self, game_id: GameKey) -> None:
        ...
