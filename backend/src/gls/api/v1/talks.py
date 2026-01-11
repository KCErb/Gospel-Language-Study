"""Talk-related API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from gls.api.deps import TalkRepoType
from gls.domain.models import TalkId

router = APIRouter()


class TalkResponse(BaseModel):
    """Response model for a talk."""

    id: str
    title: str
    speaker: str
    date: str
    conference: str
    available_languages: list[str]


class TalkListResponse(BaseModel):
    """Response model for list of talks."""

    talks: list[TalkResponse]


@router.get("", response_model=TalkListResponse)
def list_talks(talk_repo: TalkRepoType) -> TalkListResponse:
    """List all available talks."""
    talks = talk_repo.get_all()
    return TalkListResponse(
        talks=[
            TalkResponse(
                id=str(talk.id),
                title=talk.title,
                speaker=talk.speaker,
                date=talk.date.isoformat(),
                conference=talk.conference,
                available_languages=[lang.value for lang in talk.available_languages],
            )
            for talk in talks
        ]
    )


@router.get("/{talk_id}", response_model=TalkResponse)
def get_talk(talk_id: str, talk_repo: TalkRepoType) -> TalkResponse:
    """Get a specific talk by ID."""
    talk = talk_repo.get_by_id(TalkId(talk_id))
    if not talk:
        raise HTTPException(status_code=404, detail="Talk not found")
    return TalkResponse(
        id=str(talk.id),
        title=talk.title,
        speaker=talk.speaker,
        date=talk.date.isoformat(),
        conference=talk.conference,
        available_languages=[lang.value for lang in talk.available_languages],
    )
