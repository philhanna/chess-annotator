from abc import ABC, abstractmethod

from annotate.domain.annotation import Annotation


class DocumentRenderer(ABC):
    @abstractmethod
    def render(
        self,
        annotation: Annotation,
        output_path,
        diagram_size: int,
        page_size: str,
        store_dir,
    ) -> None:
        ...
