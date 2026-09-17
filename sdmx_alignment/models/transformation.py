from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class TransformationActionResult(BaseModel):
    finding_id: str
    action: str
    status: Literal["applied", "no_change", "failed"]
    local_element_id: str | None = None
    reference_element_id: str | None = None
    message: str


class TransformationResult(BaseModel):
    original_sha256: str
    revised_sha256: str
    revised_xml: bytes
    actions: list[TransformationActionResult] = Field(default_factory=list)

