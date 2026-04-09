from abc import ABC, abstractmethod

from annotate.domain.annotation import Annotation


class DocumentRenderer(ABC):
    """Port for rendering an annotation into a final output document.

    A concrete renderer is responsible for turning an ``Annotation`` — including
    its segment labels, commentary, and diagram flags — into a user-facing output
    file such as a PDF. Keeping this interface in the ports layer means the domain
    and use-case layers have no dependency on any particular rendering technology.
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
        """Render ``annotation`` to the file at ``output_path``.

        Args:
            annotation:   The fully-populated annotation to render.
            output_path:  Destination file path for the rendered document.
            diagram_size: Width (and height) in pixels for board diagram images.
            page_size:    Paper size string, typically ``"a4"`` or ``"letter"``.
            store_dir:    Root store directory, used to locate diagram caches.
        """
        ...
