#!/usr/bin/env python3
"""Transcribe audio using OpenAI's Whisper API.

This script uses OpenAI's Whisper API to transcribe audio and generate
word-level timestamps for text synchronization.

Usage:
    python scripts/transcribe_openai.py 2025-10-58-oaks eng
    python scripts/transcribe_openai.py 2025-10-58-oaks eng zhs

Requirements:
    pip install openai python-dotenv
    Set OPENAI_API_KEY in .env file
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# Map 3-letter ISO 639-2 codes to 2-letter codes for Whisper
LANG_CODE_MAP = {
    "eng": "en",
    "zhs": "zh",
    "zht": "zh",
    "spa": "es",
    "por": "pt",
    "fra": "fr",
    "deu": "de",
    "ita": "it",
    "jpn": "ja",
    "kor": "ko",
    "rus": "ru",
    "ces": "cs",
}


def find_audio_file(talk_dir: Path) -> Path | None:
    """Find the MP3 audio file in a talk directory."""
    mp3_files = list(talk_dir.glob("*.mp3"))
    if not mp3_files:
        return None
    if len(mp3_files) > 1:
        print(f"Warning: Multiple MP3 files found in {talk_dir}, using first one")
    return mp3_files[0]


def transcribe_with_openai(audio_path: Path, language: str) -> dict:
    """Transcribe audio using OpenAI's Whisper API with word timestamps."""
    import os
    try:
        from openai import OpenAI
    except ImportError:
        print("Error: openai package not installed")
        print("  pip install openai")
        sys.exit(1)

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not set in environment or .env file")
        sys.exit(1)

    client = OpenAI(api_key=api_key)

    # Convert to 2-letter code
    lang_2 = LANG_CODE_MAP.get(language, language[:2])
    print(f"Language: {language} -> {lang_2}")

    print(f"Uploading and transcribing: {audio_path.name}")
    print("(This may take a few minutes for long audio files...)")

    with open(audio_path, "rb") as audio_file:
        response = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language=lang_2,
            response_format="verbose_json",
            timestamp_granularities=["word", "segment"],
        )

    return response


def convert_to_alignment_format(
    response: dict,
    talk_id: str,
    language: str,
) -> dict:
    """Convert OpenAI response to our alignment.json format."""
    segments = []

    # OpenAI returns segments with word-level timestamps
    for i, seg in enumerate(response.segments):
        words = []

        # Get words for this segment if available
        if hasattr(response, 'words') and response.words:
            # Filter words that fall within this segment's time range
            seg_words = [
                w for w in response.words
                if w.start >= seg.start and w.end <= seg.end + 0.1  # small tolerance
            ]
            for word in seg_words:
                words.append({
                    "word": word.word.strip(),
                    "start_time": round(word.start, 3),
                    "end_time": round(word.end, 3),
                    "confidence": 0.95,  # OpenAI doesn't provide confidence
                })

        # If no word-level timestamps, create approximate ones from segment
        if not words and seg.text.strip():
            # Split segment text into words and distribute time evenly
            text_words = seg.text.strip().split()
            if text_words:
                duration = seg.end - seg.start
                word_duration = duration / len(text_words)
                for j, word in enumerate(text_words):
                    words.append({
                        "word": word,
                        "start_time": round(seg.start + j * word_duration, 3),
                        "end_time": round(seg.start + (j + 1) * word_duration, 3),
                        "confidence": 0.9,
                    })

        if words:
            segments.append({
                "segment_id": f"seg-{i:03d}",
                "text": seg.text.strip(),
                "start_time": round(seg.start, 3),
                "end_time": round(seg.end, 3),
                "words": words,
            })

    return {
        "talk_id": talk_id,
        "language": language,
        "segments": segments,
    }


def process_talk(
    talk_id: str,
    language: str,
    data_dir: Path,
    force: bool = False,
) -> bool:
    """Process a single language version of a talk."""
    lang_dir = data_dir / talk_id / language

    if not lang_dir.exists():
        print(f"Warning: Directory not found: {lang_dir}")
        return False

    output_path = lang_dir / "alignment.json"
    if output_path.exists() and not force:
        print(f"Skipping {language}: alignment.json exists (use --force to overwrite)")
        return False

    audio_path = find_audio_file(lang_dir)
    if not audio_path:
        print(f"Warning: No MP3 file found in {lang_dir}")
        return False

    print(f"\n{'='*60}")
    print(f"Processing: {talk_id}/{language}")
    print(f"Audio: {audio_path.name}")
    print(f"{'='*60}\n")

    try:
        response = transcribe_with_openai(audio_path, language)
        alignment = convert_to_alignment_format(response, talk_id, language)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(alignment, f, ensure_ascii=False, indent=2)

        print(f"\nWrote: {output_path}")
        print(f"Segments: {len(alignment['segments'])}")
        total_words = sum(len(s["words"]) for s in alignment["segments"])
        print(f"Words: {total_words}")
        return True

    except Exception as e:
        print(f"Error processing {language}: {e}")
        import traceback
        traceback.print_exc()
        return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Transcribe talk audio using OpenAI Whisper API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s 2025-10-58-oaks eng
    %(prog)s 2025-10-58-oaks eng zhs
    %(prog)s 2025-10-58-oaks eng --force
        """,
    )
    parser.add_argument(
        "talk_id",
        help="Talk identifier (directory name in data/talks/)",
    )
    parser.add_argument(
        "languages",
        nargs="+",
        help="3-letter language codes to process (eng, zhs, spa, etc.)",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(__file__).parent.parent / "data" / "talks",
        help="Path to talks data directory",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing alignment files",
    )

    args = parser.parse_args()

    success_count = 0
    for lang in args.languages:
        if process_talk(args.talk_id, lang, args.data_dir, args.force):
            success_count += 1

    print(f"\n{'='*60}")
    print(f"Completed: {success_count}/{len(args.languages)} languages")
    print(f"{'='*60}")

    return 0 if success_count > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
