"""Playback-related API endpoints for audio and alignment."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from gls.api.deps import AlignmentRepoType, TalkRepoType
from gls.domain.models import Language, TalkId

router = APIRouter()


class WordAlignmentResponse(BaseModel):
    """Word-level alignment data."""

    word: str
    start_time: float
    end_time: float
    confidence: float


class SegmentAlignmentResponse(BaseModel):
    """Segment-level alignment with words."""

    segment_id: str
    text: str
    start_time: float
    end_time: float
    words: list[WordAlignmentResponse]


class AlignmentResponse(BaseModel):
    """Full alignment response."""

    talk_id: str
    language: str
    segments: list[SegmentAlignmentResponse]


class TalkVersionResponse(BaseModel):
    """Talk version with text content."""

    talk_id: str
    language: str
    text_content: str
    has_alignment: bool


@router.get("/audio/{talk_id}/{language}")
def get_audio(
    talk_id: str,
    language: str,
    talk_repo: TalkRepoType,
) -> FileResponse:
    """Stream audio file for a talk version.

    Returns 404 if talk or language version not found.
    Returns 500 if audio file exists in DB but not on disk (data corruption).
    """
    try:
        lang = Language.from_code(language)
    except ValueError:
        valid_codes = [lang_enum.value for lang_enum in Language]
        raise HTTPException(
            status_code=400,
            detail=f"Unknown language code: {language}. Valid codes: {valid_codes}",
        ) from None

    version = talk_repo.get_version(TalkId(talk_id), lang)
    if not version:
        raise HTTPException(
            status_code=404,
            detail=f"Talk '{talk_id}' not found in language '{language}'",
        )

    audio_path = Path(version.audio_path)
    if not audio_path.exists():
        raise HTTPException(
            status_code=500,
            detail="Audio file missing from disk. Please re-add the talk data.",
        )

    return FileResponse(
        path=audio_path,
        media_type="audio/mpeg",
        filename=f"{talk_id}_{language}.mp3",
    )


@router.get("/text/{talk_id}/{language}", response_model=TalkVersionResponse)
def get_text(
    talk_id: str,
    language: str,
    talk_repo: TalkRepoType,
    alignment_repo: AlignmentRepoType,
) -> TalkVersionResponse:
    """Get text content for a talk version.

    Returns the full text and whether alignment data is available.
    """
    try:
        lang = Language.from_code(language)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown language code: {language}",
        ) from None

    version = talk_repo.get_version(TalkId(talk_id), lang)
    if not version:
        raise HTTPException(
            status_code=404,
            detail=f"Talk '{talk_id}' not found in language '{language}'",
        )

    has_alignment = alignment_repo.has_alignment(TalkId(talk_id), lang)

    return TalkVersionResponse(
        talk_id=talk_id,
        language=language,
        text_content=version.text_content,
        has_alignment=has_alignment,
    )


@router.get("/alignment/{talk_id}/{language}", response_model=AlignmentResponse)
def get_alignment(
    talk_id: str,
    language: str,
    alignment_repo: AlignmentRepoType,
) -> AlignmentResponse:
    """Get word-level alignment data for a talk version.

    Returns 404 if alignment hasn't been generated yet.
    Alignment is optional - playback works without it, just no word highlighting.
    """
    try:
        lang = Language.from_code(language)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown language code: {language}",
        ) from None

    alignment = alignment_repo.get_alignment(TalkId(talk_id), lang)
    if not alignment:
        raise HTTPException(
            status_code=404,
            detail=f"Alignment not yet generated for '{talk_id}' in '{language}'. "
            "Playback will work but without word-level highlighting.",
        )

    return AlignmentResponse(
        talk_id=talk_id,
        language=language,
        segments=[
            SegmentAlignmentResponse(
                segment_id=seg.segment_id,
                text=seg.text,
                start_time=seg.start_time,
                end_time=seg.end_time,
                words=[
                    WordAlignmentResponse(
                        word=w.word,
                        start_time=w.start_time,
                        end_time=w.end_time,
                        confidence=w.confidence,
                    )
                    for w in seg.words
                ],
            )
            for seg in alignment.segments
        ],
    )
