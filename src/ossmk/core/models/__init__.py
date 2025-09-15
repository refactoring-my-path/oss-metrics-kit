from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Visibility(str, Enum):
    public = "public"
    private = "private"


class Repo(BaseModel):
    id: str
    host: str = "github.com"
    owner: str
    name: str
    visibility: Visibility = Visibility.public
    topics: list[str] = Field(default_factory=list)


class User(BaseModel):
    id: str
    login: str
    display_name: Optional[str] = None
    orgs: list[str] = Field(default_factory=list)


class EventKind(str, Enum):
    commit = "commit"
    pr = "pr"
    review = "review"
    issue = "issue"


class ContributionEvent(BaseModel):
    id: str
    kind: EventKind
    repo_id: str
    user_id: str
    created_at: datetime
    lines_added: int = 0
    lines_removed: int = 0


class Score(BaseModel):
    subject_id: str
    dimension: str
    value: float
    window: str = "all"
    metadata: dict[str, str] = Field(default_factory=dict)


class ScoreRule(BaseModel):
    id: str
    dimension: str
    selector: str = "*"
    weight: float = 1.0
    decay: float = 1.0
    threshold: float = 0.0

