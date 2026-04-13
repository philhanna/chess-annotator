# annotate.server.routes.segments
from dataclasses import dataclass

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Annotated

from annotate.server.deps import get_service
from annotate.use_cases import (
    AnnotationService,
    GameNotFoundError,
    SegmentDetail,
    SegmentNotFoundError,
    SegmentSummary,
    SessionNotOpenError,
    UseCaseError,
)

router = APIRouter()

ServiceDep = Annotated[AnnotationService, Depends(get_service)]


@dataclass
class AddTurningPointRequest:
    ply: int
    label: str = ""


@dataclass
class MergeSegmentsRequest:
    m: int
    n: int


@dataclass
class PatchSegmentRequest:
    label: str | None = None
    annotation: str | None = None


@router.get("/games/{game_id}/session/segments", response_model=None)
def list_segments(game_id: str, service: ServiceDep) -> list[SegmentSummary]:
    try:
        return service.list_segments(game_id=game_id)
    except GameNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SessionNotOpenError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except UseCaseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/games/{game_id}/session/segments", response_model=None)
def add_turning_point(
    game_id: str, body: AddTurningPointRequest, service: ServiceDep
) -> list[SegmentSummary]:
    try:
        return service.add_turning_point(game_id=game_id, ply=body.ply, label=body.label)
    except GameNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SessionNotOpenError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except UseCaseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/games/{game_id}/session/segments/merge", response_model=None)
def merge_segments(
    game_id: str, body: MergeSegmentsRequest, service: ServiceDep
) -> list[SegmentSummary]:
    try:
        return service.merge_segments(game_id=game_id, m=body.m, n=body.n)
    except GameNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SessionNotOpenError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except UseCaseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/games/{game_id}/session/segments/{ply}", response_model=None)
def view_segment(game_id: str, ply: int, service: ServiceDep) -> SegmentDetail:
    try:
        return service.view_segment(game_id=game_id, turning_point_ply=ply)
    except GameNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SessionNotOpenError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except SegmentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except UseCaseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.patch("/games/{game_id}/session/segments/{ply}", response_model=None)
def patch_segment(
    game_id: str, ply: int, body: PatchSegmentRequest, service: ServiceDep
) -> SegmentDetail:
    try:
        detail: SegmentDetail | None = None
        if body.label is not None:
            detail = service.set_segment_label(
                game_id=game_id, turning_point_ply=ply, label=body.label
            )
        if body.annotation is not None:
            detail = service.set_segment_annotation(
                game_id=game_id, turning_point_ply=ply, annotation_text=body.annotation
            )
        if detail is None:
            detail = service.view_segment(game_id=game_id, turning_point_ply=ply)
        return detail
    except GameNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SessionNotOpenError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except SegmentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except UseCaseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete("/games/{game_id}/session/segments/{ply}", response_model=None)
def remove_turning_point(
    game_id: str,
    ply: int,
    service: ServiceDep,
    force: Annotated[bool, Query()] = False,
) -> list[SegmentSummary]:
    try:
        return service.remove_turning_point(game_id=game_id, ply=ply, force=force)
    except GameNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SessionNotOpenError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except UseCaseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
