
from abc import ABC, abstractmethod

from annotate.domain.annotation import Annotation


class AnnotationRepository(ABC):
    """Define persistent storage operations for annotations.

    Implementations hide the underlying storage mechanism from the core
    application. In addition to the canonical save/load operations, this
    port models the working-copy lifecycle used by the interactive CLI
    so authors can edit safely before committing changes back to the
    main store.
    """

    @abstractmethod
    def save(self, annotation: Annotation) -> None: ...

    @abstractmethod
    def load(self, annotation_id: str) -> Annotation: ...

    @abstractmethod
    def list_all(self) -> list[tuple[str, str]]:
        """Return list of (annotation_id, title) for all saved annotations."""
        ...

    @abstractmethod
    def exists_working_copy(self, annotation_id: str) -> bool: ...

    @abstractmethod
    def save_working_copy(self, annotation: Annotation) -> None: ...

    @abstractmethod
    def load_working_copy(self, annotation_id: str) -> Annotation: ...

    @abstractmethod
    def discard_working_copy(self, annotation_id: str) -> None: ...

    @abstractmethod
    def commit_working_copy(self, annotation_id: str) -> None:
        """Overwrite the main store file from the working copy, then remove it."""
        ...

    @abstractmethod
    def stale_working_copies(self) -> list[str]:
        """Return annotation_ids that have a working copy in the work directory."""
        ...
