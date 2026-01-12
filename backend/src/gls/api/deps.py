"""FastAPI dependency injection setup.

This module wires together the domain services with infrastructure implementations.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from gls.config import Settings, get_settings
from gls.infrastructure.storage.talk_storage import FileAlignmentRepository, FileTalkRepository


def get_talk_repository(
    settings: Annotated[Settings, Depends(get_settings)],
) -> FileTalkRepository:
    """Get talk repository instance."""
    return FileTalkRepository(settings.talks_dir)


def get_alignment_repository(
    settings: Annotated[Settings, Depends(get_settings)],
) -> FileAlignmentRepository:
    """Get alignment repository instance."""
    return FileAlignmentRepository(settings.talks_dir)


# Type aliases for dependency injection
TalkRepoType = Annotated[FileTalkRepository, Depends(get_talk_repository)]
AlignmentRepoType = Annotated[FileAlignmentRepository, Depends(get_alignment_repository)]


def get_current_user_id() -> str:
    """Return default user ID for MVP. Replace with auth later."""
    return "default-user"


CurrentUserId = Annotated[str, Depends(get_current_user_id)]
