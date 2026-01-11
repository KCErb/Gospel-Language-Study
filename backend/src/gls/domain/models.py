"""Domain models - Core business entities.

These are pure Python dataclasses representing the domain concepts.
They have no dependencies on infrastructure (database, API, etc.).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Language(str, Enum):
    """Supported languages with ISO 639-2/3 codes.

    Using 3-letter codes to match church website conventions.
    """

    ENGLISH = "eng"
    MANDARIN_SIMPLIFIED = "zhs"  # Simplified Chinese
    MANDARIN_TRADITIONAL = "zht"  # Traditional Chinese
    CZECH = "ces"
    SPANISH = "spa"
    RUSSIAN = "rus"
    PORTUGUESE = "por"
    FRENCH = "fra"
    GERMAN = "deu"
    KOREAN = "kor"
    JAPANESE = "jpn"

    @classmethod
    def from_code(cls, code: str) -> Language:
        """Get Language from code string, case-insensitive."""
        code_lower = code.lower()
        for lang in cls:
            if lang.value == code_lower:
                return lang
        raise ValueError(f"Unknown language code: {code}")


@dataclass(frozen=True)
class TalkId:
    """Value object for talk identification.

    Examples: "2025-10-58-oaks", "2024-04-holland-tomorrow"
    """

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("TalkId cannot be empty")

    def __str__(self) -> str:
        return self.value


@dataclass
class Talk:
    """A conference talk with metadata.

    Represents a talk independent of any specific language version.
    """

    id: TalkId
    title: str
    speaker: str
    date: datetime
    conference: str
    available_languages: list[Language] = field(default_factory=list)

    def has_language(self, language: Language) -> bool:
        """Check if this talk has a version in the given language."""
        return language in self.available_languages


@dataclass
class TalkVersion:
    """A specific language version of a talk.

    Contains the text content and paths to associated files.
    """

    talk_id: TalkId
    language: Language
    text_content: str
    audio_path: str
    text_path: str
    alignment_path: str | None = None

    @property
    def has_alignment(self) -> bool:
        """Check if alignment data exists for this version."""
        return self.alignment_path is not None


@dataclass
class WordAlignment:
    """Word-level timing information from audio alignment."""

    word: str
    start_time: float  # seconds from start of audio
    end_time: float  # seconds from start of audio
    confidence: float  # 0.0 to 1.0


@dataclass
class SegmentAlignment:
    """Sentence/paragraph level alignment with word details.

    A segment typically corresponds to a sentence or natural phrase.
    """

    segment_id: str
    text: str
    start_time: float
    end_time: float
    words: list[WordAlignment] = field(default_factory=list)


@dataclass
class Alignment:
    """Full alignment data for a talk version.

    Maps text to audio timestamps at both segment and word level.
    """

    talk_id: TalkId
    language: Language
    segments: list[SegmentAlignment] = field(default_factory=list)

    def find_segment_at_time(self, time: float) -> SegmentAlignment | None:
        """Find the segment containing given timestamp.

        Uses linear search - consider binary search if performance matters.
        """
        for segment in self.segments:
            if segment.start_time <= time <= segment.end_time:
                return segment
        return None

    def find_word_at_time(self, time: float) -> WordAlignment | None:
        """Find the word being spoken at given timestamp."""
        segment = self.find_segment_at_time(time)
        if not segment:
            return None
        for word in segment.words:
            if word.start_time <= time <= word.end_time:
                return word
        return None

    def get_segment_index_at_time(self, time: float) -> int | None:
        """Get index of segment at given time (for binary search on frontend)."""
        for i, segment in enumerate(self.segments):
            if segment.start_time <= time <= segment.end_time:
                return i
        return None


@dataclass
class VocabularyItem:
    """User-saved word or phrase for study.

    Links source and target language text with optional context.
    """

    id: str
    user_id: str
    source_language: Language
    target_language: Language
    source_text: str
    target_text: str
    context_sentence: str | None = None
    audio_start_time: float | None = None
    audio_end_time: float | None = None
    talk_id: TalkId | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    @staticmethod
    def generate_id() -> str:
        """Generate a unique ID for a new vocabulary item."""
        return str(uuid.uuid4())


@dataclass
class User:
    """User profile for multi-user support.

    For MVP, we use a single default user.
    """

    id: str
    name: str
    native_languages: list[Language] = field(default_factory=list)
    learning_languages: list[Language] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)

    @staticmethod
    def default() -> User:
        """Create the default single-user for MVP."""
        return User(
            id="default-user",
            name="Default User",
            native_languages=[Language.ENGLISH],
            learning_languages=[Language.MANDARIN_SIMPLIFIED, Language.CZECH],
        )
