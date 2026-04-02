
from abc import ABC, abstractmethod

from annotate.domain.annotation import Annotation


class DocumentRenderer(ABC):
    """Describe a service that renders an annotation into a final document.

    A concrete renderer is responsible for turning validated annotation
    data, rendered diagrams, and layout settings into a user-facing
    output such as a PDF. The port keeps document-generation concerns
    outside the domain layer while still giving use cases a stable
    interface to invoke.
    """

    @abstractmethod
    def render(
        self,
        annotation: Annotation,
        output_path,
        diagram_size: int,
        page_size: str,
        store_dir,
    ) -> None:
        """Render ``annotation`` to the requested output destination."""
        ...
