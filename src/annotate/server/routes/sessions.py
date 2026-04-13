# annotate.server.routes.sessions
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Annotated

from annotate.server.deps import get_service
from annotate.use_cases import (
    AnnotationService,
    CloseGameResult,
    GameNotFoundError,
    GameState,
    SessionNotOpenError,
    UseCaseError,
)

router = APIRouter()

ServiceDep = Annotated[AnnotationService, Depends(get_service)]


@router.post("/games/{game_id}/session", status_code=200, response_model=None)
def open_session(game_id: str, service: ServiceDep) -> GameState:
    try:
        return service.open_game(game_id)
    except GameNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except UseCaseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/games/{game_id}/session", response_model=None)
def get_session(game_id: str, service: ServiceDep) -> GameState:
    try:
        return service.open_game(game_id)
    except GameNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except UseCaseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/games/{game_id}/session/save", response_model=None)
def save_session(game_id: str, service: ServiceDep) -> GameState:
    try:
        return service.save_session(game_id)
    except GameNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SessionNotOpenError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except UseCaseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete("/games/{game_id}/session", response_model=None)
def close_session(
    game_id: str,
    service: ServiceDep,
    save_changes: Annotated[bool | None, Query()] = None,
) -> CloseGameResult:
    try:
        result = service.close_game(game_id, save_changes=save_changes)
    except GameNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SessionNotOpenError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except UseCaseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if result.requires_confirmation:
        raise HTTPException(
            status_code=409,
            detail={"requires_confirmation": True},
        )
    return result
