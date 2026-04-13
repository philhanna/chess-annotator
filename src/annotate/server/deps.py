# annotate.server.deps
from annotate.use_cases import AnnotationService

_service: AnnotationService | None = None


def init_service(service: AnnotationService) -> None:
    """Store the application-wide ``AnnotationService`` singleton."""
    global _service
    _service = service


def get_service() -> AnnotationService:
    """Return the ``AnnotationService`` singleton (must be initialised first)."""
    assert _service is not None, "Service has not been initialised"
    return _service
