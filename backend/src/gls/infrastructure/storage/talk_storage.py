"""File-based talk storage implementation.

Reads talks from the filesystem in the format:
    data/talks/{talk_id}/{lang}/
        - *.mp3 (audio file)
        - *.txt (text file)
        - alignment.json (optional)
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

from gls.domain.models import (
    Alignment,
    Language,
    SegmentAlignment,
    Talk,
    TalkId,
    TalkVersion,
    WordAlignment,
)


class FileTalkRepository:
    """Repository that reads talk data from filesystem.

    Directory structure:
        talks_dir/
            {talk_id}/
                {lang}/
                    *.mp3
                    *.txt
                    alignment.json (optional)
    """

    def __init__(self, talks_dir: Path) -> None:
        self._talks_dir = talks_dir

    def get_all(self) -> Sequence[Talk]:
        """Get all talks from the filesystem."""
        talks: list[Talk] = []

        if not self._talks_dir.exists():
            return talks

        for talk_dir in self._talks_dir.iterdir():
            if talk_dir.is_dir() and not talk_dir.name.startswith("."):
                talk = self._load_talk(talk_dir)
                if talk:
                    talks.append(talk)

        return sorted(talks, key=lambda t: t.date, reverse=True)

    def get_by_id(self, talk_id: TalkId) -> Talk | None:
        """Get a specific talk by ID."""
        talk_dir = self._talks_dir / talk_id.value
        if not talk_dir.exists():
            return None
        return self._load_talk(talk_dir)

    def get_version(self, talk_id: TalkId, language: Language) -> TalkVersion | None:
        """Get a specific language version of a talk."""
        lang_dir = self._talks_dir / talk_id.value / language.value
        if not lang_dir.exists():
            return None

        text_file = self._find_file(lang_dir, ".txt")
        audio_file = self._find_file(lang_dir, ".mp3")

        if not text_file or not audio_file:
            return None

        text_content = text_file.read_text(encoding="utf-8")
        alignment_file = lang_dir / "alignment.json"

        return TalkVersion(
            talk_id=talk_id,
            language=language,
            text_content=text_content,
            audio_path=str(audio_file),
            text_path=str(text_file),
            alignment_path=str(alignment_file) if alignment_file.exists() else None,
        )

    def get_available_languages(self, talk_id: TalkId) -> Sequence[Language]:
        """Get list of available languages for a talk."""
        talk_dir = self._talks_dir / talk_id.value
        if not talk_dir.exists():
            return []

        languages: list[Language] = []
        for lang_dir in talk_dir.iterdir():
            if lang_dir.is_dir() and not lang_dir.name.startswith("."):
                try:
                    lang = Language.from_code(lang_dir.name)
                    # Verify it has both text and audio
                    if self._find_file(lang_dir, ".txt") and self._find_file(lang_dir, ".mp3"):
                        languages.append(lang)
                except ValueError:
                    # Unknown language code, skip
                    pass

        return languages

    def _load_talk(self, talk_dir: Path) -> Talk | None:
        """Load talk metadata from directory."""
        talk_id = TalkId(talk_dir.name)
        available_languages = list(self.get_available_languages(talk_id))

        if not available_languages:
            return None

        # Try to parse metadata from directory name or first available text
        title, speaker, date, conference = self._extract_metadata(talk_dir, available_languages[0])

        return Talk(
            id=talk_id,
            title=title,
            speaker=speaker,
            date=date,
            conference=conference,
            available_languages=available_languages,
        )

    def _extract_metadata(
        self, talk_dir: Path, primary_lang: Language
    ) -> tuple[str, str, datetime, str]:
        """Extract metadata from directory name and text file.

        Directory name format: YYYY-MM-NN-speaker or similar
        Example: 2025-10-58-oaks
        """
        dir_name = talk_dir.name

        # Try to parse date from directory name (YYYY-MM format)
        date_match = re.match(r"(\d{4})-(\d{2})", dir_name)
        if date_match:
            year = int(date_match.group(1))
            month = int(date_match.group(2))
            date = datetime(year, month, 1)
            # Determine conference name from month
            if month == 4:
                conference = f"April {year} General Conference"
            elif month == 10:
                conference = f"October {year} General Conference"
            else:
                conference = f"{year} General Conference"
        else:
            date = datetime.now()
            conference = "General Conference"

        # Try to extract speaker from directory name
        speaker_match = re.search(r"-([a-z]+)$", dir_name)
        speaker = speaker_match.group(1).title() if speaker_match else "Unknown Speaker"

        # Try to get title from text file (usually first non-header line)
        title = self._extract_title_from_text(talk_dir, primary_lang)
        if not title:
            title = dir_name.replace("-", " ").title()

        return title, speaker, date, conference

    def _extract_title_from_text(self, talk_dir: Path, lang: Language) -> str | None:
        """Extract talk title from text file.

        Looks for the title which is typically repeated after the timestamp header.
        """
        lang_dir = talk_dir / lang.value
        text_file = self._find_file(lang_dir, ".txt")
        if not text_file:
            return None

        try:
            lines = text_file.read_text(encoding="utf-8").strip().split("\n")
            # Skip timestamp line, look for first substantial content
            for line in lines[1:10]:  # Check first 10 lines
                line = line.strip()
                # Skip empty lines, timestamps, URLs, page numbers
                if not line:
                    continue
                if re.match(r"\d+/\d+/\d+", line):  # Date format
                    continue
                if line.startswith("http"):
                    continue
                if re.match(r"\d+/\d+$", line):  # Page number
                    continue
                if len(line) > 5:  # Reasonable title length
                    return line
        except Exception:
            pass

        return None

    def _find_file(self, directory: Path, extension: str) -> Path | None:
        """Find the first file with given extension in directory."""
        if not directory.exists():
            return None
        for file in directory.iterdir():
            if file.suffix.lower() == extension.lower() and file.is_file():
                return file
        return None


class FileAlignmentRepository:
    """Repository that reads alignment data from JSON files."""

    def __init__(self, talks_dir: Path) -> None:
        self._talks_dir = talks_dir

    def get_alignment(self, talk_id: TalkId, language: Language) -> Alignment | None:
        """Load alignment from JSON file."""
        alignment_path = self._talks_dir / talk_id.value / language.value / "alignment.json"

        if not alignment_path.exists():
            return None

        try:
            data = json.loads(alignment_path.read_text(encoding="utf-8"))
            return self._parse_alignment(talk_id, language, data)
        except (json.JSONDecodeError, KeyError):
            return None

    def save_alignment(self, alignment: Alignment) -> None:
        """Save alignment to JSON file."""
        alignment_path = (
            self._talks_dir / alignment.talk_id.value / alignment.language.value / "alignment.json"
        )
        alignment_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "talk_id": alignment.talk_id.value,
            "language": alignment.language.value,
            "version": "1.0",
            "generated_at": datetime.utcnow().isoformat(),
            "segments": [
                {
                    "segment_id": seg.segment_id,
                    "text": seg.text,
                    "start_time": seg.start_time,
                    "end_time": seg.end_time,
                    "words": [
                        {
                            "word": w.word,
                            "start_time": w.start_time,
                            "end_time": w.end_time,
                            "confidence": w.confidence,
                        }
                        for w in seg.words
                    ],
                }
                for seg in alignment.segments
            ],
        }

        alignment_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def has_alignment(self, talk_id: TalkId, language: Language) -> bool:
        """Check if alignment file exists."""
        alignment_path = self._talks_dir / talk_id.value / language.value / "alignment.json"
        return alignment_path.exists()

    def _parse_alignment(
        self, talk_id: TalkId, language: Language, data: dict[str, Any]
    ) -> Alignment:
        """Parse alignment data from JSON structure."""
        segments: list[SegmentAlignment] = []

        for seg_data in data.get("segments", []):
            words = [
                WordAlignment(
                    word=w["word"],
                    start_time=w["start_time"],
                    end_time=w["end_time"],
                    confidence=w.get("confidence", 1.0),
                )
                for w in seg_data.get("words", [])
            ]

            segments.append(
                SegmentAlignment(
                    segment_id=seg_data["segment_id"],
                    text=seg_data["text"],
                    start_time=seg_data["start_time"],
                    end_time=seg_data["end_time"],
                    words=words,
                )
            )

        return Alignment(
            talk_id=talk_id,
            language=language,
            segments=segments,
        )
