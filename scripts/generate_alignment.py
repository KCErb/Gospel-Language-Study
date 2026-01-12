#!/usr/bin/env python3
"""Generate word-level alignment data for a talk using WhisperX.

This script transcribes audio and produces word-level timestamps that sync
with the audio for text highlighting during playback.

The transcription from WhisperX may differ slightly from the official printed
text (speakers ad-lib, skip sections, etc.). The alignment.json contains
WhisperX's transcription with accurate timestamps - this is what gets
highlighted during playback.

Usage:
    python scripts/generate_alignment.py 2025-10-58-oaks eng
    python scripts/generate_alignment.py 2025-10-58-oaks eng zhs --model large-v3

Requirements:
    pip install whisperx torch

First run will download models (~3GB for large-v3).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


# Map 3-letter ISO 639-2 codes (our directories) to 2-letter codes (WhisperX)
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
    "pol": "pl",
    "nld": "nl",
    "swe": "sv",
    "dan": "da",
    "nor": "no",
    "fin": "fi",
    "hun": "hu",
    "tur": "tr",
    "tha": "th",
    "vie": "vi",
    "ind": "id",
    "ukr": "uk",
}


def get_whisper_lang_code(lang_3: str) -> str:
    """Convert 3-letter ISO 639-2 code to 2-letter code for WhisperX."""
    if lang_3 in LANG_CODE_MAP:
        return LANG_CODE_MAP[lang_3]
    # If already 2-letter or unknown, return as-is
    if len(lang_3) == 2:
        return lang_3
    # Try first 2 chars as fallback
    return lang_3[:2]


def find_audio_file(talk_dir: Path) -> Path | None:
    """Find the MP3 audio file in a talk directory."""
    mp3_files = list(talk_dir.glob("*.mp3"))
    if not mp3_files:
        return None
    if len(mp3_files) > 1:
        print(f"Warning: Multiple MP3 files found in {talk_dir}, using first one")
    return mp3_files[0]


def generate_alignment(
    audio_path: Path,
    talk_id: str,
    lang_code_3: str,
    model_name: str = "large-v3",
    device: str = "auto",
    compute_type: str = "auto",
) -> dict[str, Any]:
    """Generate word-level alignment using WhisperX.

    Args:
        audio_path: Path to the audio file
        talk_id: Talk identifier
        lang_code_3: 3-letter ISO 639-2 language code (e.g., 'eng', 'zhs')
        model_name: Whisper model size
        device: 'cuda', 'cpu', or 'auto'
        compute_type: 'float16', 'int8', or 'auto'

    Returns:
        Alignment data in our expected format
    """
    try:
        import torch
        import whisperx
    except ImportError as e:
        print(f"Error: {e}")
        print("\nInstall alignment dependencies:")
        print("  cd backend && pip install -e '.[alignment]'")
        sys.exit(1)

    # Convert to 2-letter code for WhisperX
    lang_code_2 = get_whisper_lang_code(lang_code_3)
    print(f"Language: {lang_code_3} -> {lang_code_2} (for WhisperX)")

    # Auto-detect device
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"

    # Auto-detect compute type
    if compute_type == "auto":
        compute_type = "float16" if device == "cuda" else "int8"

    print(f"Using device: {device}, compute_type: {compute_type}")
    print(f"Loading Whisper model: {model_name}")

    # Load model
    model = whisperx.load_model(
        model_name,
        device,
        compute_type=compute_type,
        language=lang_code_2,
    )

    print(f"Transcribing: {audio_path}")
    audio = whisperx.load_audio(str(audio_path))
    result = model.transcribe(audio, batch_size=16, language=lang_code_2)

    print("Loading alignment model...")
    model_a, metadata = whisperx.load_align_model(
        language_code=lang_code_2,
        device=device,
    )

    print("Aligning transcription to audio...")
    result = whisperx.align(
        result["segments"],
        model_a,
        metadata,
        audio,
        device,
        return_char_alignments=False,
    )

    # Convert to our format
    segments = []
    for i, seg in enumerate(result["segments"]):
        words = []
        for word_data in seg.get("words", []):
            # WhisperX may not have timing for all words
            if "start" in word_data and "end" in word_data:
                words.append({
                    "word": word_data["word"].strip(),
                    "start_time": round(word_data["start"], 3),
                    "end_time": round(word_data["end"], 3),
                    "confidence": round(word_data.get("score", 0.9), 3),
                })

        if words:  # Only include segments that have word timings
            segments.append({
                "segment_id": f"seg-{i:03d}",
                "text": seg["text"].strip(),
                "start_time": round(seg["start"], 3),
                "end_time": round(seg["end"], 3),
                "words": words,
            })

    return {
        "talk_id": talk_id,
        "language": lang_code_3,  # Store as 3-letter code
        "segments": segments,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate word-level alignment for talk audio",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Language codes (3-letter ISO 639-2):
    eng (English), zhs (Chinese Simplified), zht (Chinese Traditional),
    spa (Spanish), por (Portuguese), fra (French), deu (German),
    ces (Czech), rus (Russian), jpn (Japanese), kor (Korean), etc.

Examples:
    %(prog)s 2025-10-58-oaks eng
    %(prog)s 2025-10-58-oaks eng zhs --model medium
    %(prog)s 2025-10-58-oaks eng --device cpu
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
        "--model",
        default="large-v3",
        choices=["tiny", "base", "small", "medium", "large-v2", "large-v3"],
        help="Whisper model size (default: large-v3)",
    )
    parser.add_argument(
        "--device",
        default="auto",
        choices=["auto", "cuda", "cpu"],
        help="Device to use (default: auto)",
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

    talk_dir = args.data_dir / args.talk_id
    if not talk_dir.exists():
        print(f"Error: Talk directory not found: {talk_dir}")
        return 1

    success_count = 0
    for lang in args.languages:
        lang_dir = talk_dir / lang
        if not lang_dir.exists():
            print(f"Warning: Language directory not found: {lang_dir}")
            continue

        output_path = lang_dir / "alignment.json"
        if output_path.exists() and not args.force:
            print(f"Skipping {lang}: alignment.json exists (use --force to overwrite)")
            continue

        audio_path = find_audio_file(lang_dir)
        if not audio_path:
            print(f"Warning: No MP3 file found in {lang_dir}")
            continue

        print(f"\n{'='*60}")
        print(f"Processing: {args.talk_id}/{lang}")
        print(f"Audio: {audio_path.name}")
        print(f"{'='*60}\n")

        try:
            alignment = generate_alignment(
                audio_path=audio_path,
                talk_id=args.talk_id,
                lang_code_3=lang,
                model_name=args.model,
                device=args.device,
            )

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(alignment, f, ensure_ascii=False, indent=2)

            print(f"\nWrote: {output_path}")
            print(f"Segments: {len(alignment['segments'])}")
            total_words = sum(len(s["words"]) for s in alignment["segments"])
            print(f"Words: {total_words}")
            success_count += 1

        except Exception as e:
            print(f"Error processing {lang}: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'='*60}")
    print(f"Completed: {success_count}/{len(args.languages)} languages")
    print(f"{'='*60}")

    return 0 if success_count > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
