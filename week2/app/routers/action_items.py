from __future__ import annotations

from collections.abc import Callable
from typing import Optional

from fastapi import APIRouter, HTTPException

from .. import db
from ..schemas import ActionItemResponse
from ..schemas import ExtractActionItemsRequest
from ..schemas import ExtractActionItemsResponse
from ..schemas import MarkActionItemDoneRequest
from ..schemas import MarkActionItemDoneResponse
from ..services.extract import extract_action_items
from ..services.extract import extract_action_items_llm


router = APIRouter(prefix="/action-items", tags=["action-items"])


@router.post("/extract", response_model=ExtractActionItemsResponse)
def extract(payload: ExtractActionItemsRequest) -> ExtractActionItemsResponse:
    return _extract_with(payload, extract_action_items)


@router.post("/extract-llm", response_model=ExtractActionItemsResponse)
def extract_llm(payload: ExtractActionItemsRequest) -> ExtractActionItemsResponse:
    return _extract_with(payload, extract_action_items_llm)


def _extract_with(
    payload: ExtractActionItemsRequest,
    extractor: Callable[[str], list[str]],
) -> ExtractActionItemsResponse:
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")

    note_id: Optional[int] = None
    if payload.save_note:
        note_id = db.insert_note(text)

    items = extractor(text)
    ids = db.insert_action_items(items, note_id=note_id)
    return ExtractActionItemsResponse(
        note_id=note_id,
        items=[{"id": i, "text": t} for i, t in zip(ids, items)],
    )


@router.get("", response_model=list[ActionItemResponse])
def list_all(note_id: Optional[int] = None) -> list[ActionItemResponse]:
    return db.list_action_items(note_id=note_id)


@router.post("/{action_item_id}/done", response_model=MarkActionItemDoneResponse)
def mark_done(
    action_item_id: int,
    payload: MarkActionItemDoneRequest,
) -> MarkActionItemDoneResponse:
    updated = db.mark_action_item_done(action_item_id, payload.done)
    if not updated:
        raise HTTPException(status_code=404, detail="action item not found")
    return MarkActionItemDoneResponse(id=action_item_id, done=payload.done)
