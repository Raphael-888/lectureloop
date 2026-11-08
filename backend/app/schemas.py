"""Shared Pydantic models for the backend (API contract + internal pipeline)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

PageType = Literal[
    "blank",
    "title",
    "outcomes",
    "content",
    "quiz",
    "outlook",
    "references",
]


class Concept(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9_]+$")  # e.g. "gradient_descent"
    name: str  # display name
    summary: str = Field(min_length=1)  # one sentence, used for retrieval and notes
    pages: list[int] = Field(min_length=1)  # PDF page numbers, 1-based
    prerequisites: list[str] = Field(default_factory=list)  # DIRECT prerequisites inside this lecture


class ConceptGraph(BaseModel):
    concepts: list[Concept] = Field(default_factory=list)


class PageRecord(BaseModel):
    """One merged record per PDF page: text layer + vision-model reading."""

    page: int
    slide_no: int | None = None
    title: str | None = None
    page_type: PageType
    text: str
    rich_text: str
    formulas: list[str] = Field(default_factory=list)
    figures: list[str] = Field(default_factory=list)
    uncertain: list[str] = Field(default_factory=list)
    has_vision: bool = False
