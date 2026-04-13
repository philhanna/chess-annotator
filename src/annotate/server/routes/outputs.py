# annotate.server.routes.outputs
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from typing import Annotated

from annotate.server.deps import get_service
from annotate.use_cases import (
    AnnotationService,
    GameNotFoundError,
    MissingDependencyError,
    UseCaseError,
)

router = APIRouter()

ServiceDep = Annotated[AnnotationService, Depends(get_service)]


@router.post("/games/{game_id}/render")
def render_pdf(game_id: str, service: ServiceDep) -> Response:
    try:
        output_path = service.render_pdf(game_id=game_id)
    except GameNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except MissingDependencyError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    except (UseCaseError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    pdf_bytes = output_path.read_bytes()
    return Response(content=pdf_bytes, media_type="application/pdf")


@router.post("/games/{game_id}/lichess")
def upload_to_lichess(game_id: str, service: ServiceDep) -> dict[str, str]:
    try:
        url = service.upload_to_lichess(game_id=game_id)
    except GameNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except MissingDependencyError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    except UseCaseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"url": url}
