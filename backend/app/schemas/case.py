from __future__ import annotations

import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CaseCreate(BaseModel):
    case_number: str = Field(..., min_length=3, max_length=50)
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    analyst_id: Optional[str] = None
    notes: Optional[str] = None


class CaseUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    analyst_id: Optional[str] = None


class CaseOut(BaseModel):
    id: str
    case_number: str
    title: str
    description: Optional[str]
    status: str
    notes: Optional[str]
    analyst_id: Optional[str]
    analyst_name: Optional[str]
    video_count: int
    created_at: str
    updated_at: str
