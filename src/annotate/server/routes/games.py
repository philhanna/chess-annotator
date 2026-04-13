# annotate.server.routes.games
from dataclasses import dataclass

from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated

from annotate.server.deps import get_service
from annotate.use_cases import (
    AnnotationService,
    GameNotFoundError,
    GameState,
    GameSummary,
    MissingDependencyError,
    OverwriteRequiredError,
    UseCaseError,
)

router = APIRouter()

ServiceDep = Annotated[AnnotationService, Depends(get_service)]


@dataclass
class ImportGameRequest:
    game_id: str
    pgn_text: str
    player_side: str
    author: str = ""
    date: str | None = None
    game_index: int = 0
    overwrite: bool = False


@dataclass
class CopyGameRequest:
    new_game_id: str
    overwrite: bool = False


@router.get("/games", response_model=None)
def list_games(service: ServiceDep) -> list[GameSummary]:
    return service.list_games()


@router.post("/games", status_code=201, response_model=None)
def import_game(body: ImportGameRequest, service: ServiceDep) -> GameState:
    try:
        return service.import_game(
            game_id=body.game_id,
            pgn_text=body.pgn_text,
            player_side=body.player_side,
            author=body.author,
            date=body.date,
            overwrite=body.overwrite,
            game_index=body.game_index,
        )
    except OverwriteRequiredError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except UseCaseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete("/games/{game_id}", status_code=204)
def delete_game(game_id: str, service: ServiceDep) -> None:
    try:
        service.delete_game(game_id)
    except GameNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except UseCaseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/games/{game_id}/copy", status_code=204)
def copy_game(game_id: str, body: CopyGameRequest, service: ServiceDep) -> None:
    try:
        service.save_game_as(
            source_game_id=game_id,
            new_game_id=body.new_game_id,
            overwrite=body.overwrite,
        )
    except GameNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except OverwriteRequiredError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except UseCaseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
