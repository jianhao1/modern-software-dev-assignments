from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, field_validator


class ExtractActionItemsRequest(BaseModel):
    text: str = ""
    save_note: bool = False

    @field_validator("text", mode="before")
    @classmethod
    def coerce_text(cls, value: Any) -> str:
        return "" if value is None else str(value)


class ExtractedActionItem(BaseModel):
    id: int
    text: str


class ExtractActionItemsResponse(BaseModel):
    note_id: Optional[int]
    items: list[ExtractedActionItem]


class ActionItemResponse(BaseModel):
    id: int
    note_id: Optional[int]
    text: str
    done: bool
    created_at: str


class MarkActionItemDoneRequest(BaseModel):
    done: bool = True


class MarkActionItemDoneResponse(BaseModel):
    id: int
    done: bool


class CreateNoteRequest(BaseModel):
    content: str = ""

    @field_validator("content", mode="before")
    @classmethod
    def coerce_content(cls, value: Any) -> str:
        return "" if value is None else str(value)


class NoteResponse(BaseModel):
    id: int
    content: str
    created_at: str
