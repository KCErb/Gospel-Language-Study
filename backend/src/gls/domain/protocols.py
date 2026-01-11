"""Protocol definitions for dependency injection.

These are abstract interfaces that define what the domain layer needs
from infrastructure. Implementations live in the infrastructure layer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .models import Alignment, Language, Talk, TalkId, TalkVersion, VocabularyItem


class TalkRepository(Protocol):
    """Abstract interface for talk data access."""

    def get_by_id(self, talk_id: TalkId) -> Talk | None:
        """Retrieve a talk by its ID."""
        ...

    def get_all(self) -> Sequence[Talk]:
        """Retrieve all available talks."""
        ...

    def get_version(self, talk_id: TalkId, language: Language) -> TalkVersion | None:
        """Get a specific language version of a talk."""
        ...

    def get_available_languages(self, talk_id: TalkId) -> Sequence[Language]:
        """Get list of available languages for a talk."""
        ...


class AlignmentRepository(Protocol):
    """Abstract interface for alignment data access."""

    def get_alignment(self, talk_id: TalkId, language: Language) -> Alignment | None:
        """Retrieve alignment data for a talk version."""
        ...

    def save_alignment(self, alignment: Alignment) -> None:
        """Persist alignment data."""
        ...

    def has_alignment(self, talk_id: TalkId, language: Language) -> bool:
        """Check if alignment exists for a talk version."""
        ...


class VocabularyRepository(Protocol):
    """Abstract interface for vocabulary data access."""

    def get_by_user(self, user_id: str) -> Sequence[VocabularyItem]:
        """Get all vocabulary items for a user."""
        ...

    def get_by_id(self, item_id: str) -> VocabularyItem | None:
        """Get a specific vocabulary item."""
        ...

    def save(self, item: VocabularyItem) -> None:
        """Save a vocabulary item."""
        ...

    def delete(self, item_id: str) -> bool:
        """Delete a vocabulary item. Returns True if deleted."""
        ...

    def search(
        self,
        user_id: str,
        query: str,
        language: Language | None = None,
    ) -> Sequence[VocabularyItem]:
        """Search vocabulary items by text."""
        ...
