#!/usr/bin/env python3
"""Clean PDF text using LLM, optionally guided by transcript.

This script takes raw PDF text and uses an LLM to:
1. Remove noise (headers, footers, timestamps, URLs, page numbers)
2. Extract just the talk content
3. Optionally compare with transcript to note discrepancies

Usage:
    # Basic cleaning (no transcript reference)
    python scripts/clean_text.py data/talks/2025-10-58-oaks/eng/talk.pdf

    # Guided by transcript (better results)
    python scripts/clean_text.py data/talks/2025-10-58-oaks/eng/talk.pdf --with-transcript

    # Process all languages for a talk
    python scripts/clean_text.py --talk 2025-10-58-oaks --all-langs

Requirements:
    pip install openai python-dotenv
    Set OPENAI_API_KEY in .env file or environment
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, rely on environment variables


def check_pdftotext() -> bool:
    """Check if pdftotext is available."""
    return shutil.which("pdftotext") is not None


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract raw text from PDF using pdftotext."""
    result = subprocess.run(
        ["pdftotext", "-layout", str(pdf_path), "-"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def load_transcript(alignment_path: Path) -> str | None:
    """Load transcript from alignment.json if it exists."""
    if not alignment_path.exists():
        return None

    with open(alignment_path, encoding="utf-8") as f:
        alignment = json.load(f)

    # Combine all segment texts into a transcript
    segments = alignment.get("segments", [])
    transcript = "\n\n".join(seg["text"] for seg in segments)
    return transcript


def clean_with_anthropic(
    raw_text: str,
    transcript: str | None,
    language: str,
) -> dict[str, Any]:
    """Use Claude to clean the text."""
    try:
        import anthropic
    except ImportError:
        print("Error: anthropic package not installed")
        print("  pip install anthropic")
        sys.exit(1)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable not set")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    system_prompt = """You are a text processing assistant. Your job is to clean up text extracted from PDF files of religious conference talks.

The PDF extraction includes noise like:
- Page headers/footers
- Timestamps (e.g., "1/11/26, 2:27 PM")
- URLs and website references
- Page numbers
- Print metadata

Your task is to extract ONLY the actual talk content - the title, speaker attribution, and the body of the talk itself.

Return a JSON object with:
{
  "title": "The talk title",
  "speaker": "Speaker Name",
  "cleaned_text": "The full cleaned talk text",
  "notes": ["Any notes about the cleaning process or discrepancies found"]
}"""

    user_content = f"Here is raw text extracted from a PDF of a conference talk in {language}:\n\n---RAW PDF TEXT---\n{raw_text}\n---END RAW PDF TEXT---\n\n"

    if transcript:
        user_content += f"""For reference, here is a transcript of what was actually spoken in the audio recording:

---TRANSCRIPT---
{transcript}
---END TRANSCRIPT---

Use the transcript to help identify the actual talk content. Note any significant differences between the official text and transcript in the 'notes' field (e.g., sections that were added/removed, significant wording changes).

"""

    user_content += "Please clean this text and return the JSON response."

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8000,
        messages=[
            {"role": "user", "content": user_content}
        ],
        system=system_prompt,
    )

    # Extract JSON from response
    response_text = response.content[0].text

    # Try to parse JSON (handle markdown code blocks)
    if "```json" in response_text:
        json_str = response_text.split("```json")[1].split("```")[0]
    elif "```" in response_text:
        json_str = response_text.split("```")[1].split("```")[0]
    else:
        json_str = response_text

    return json.loads(json_str)


def clean_with_openai(
    raw_text: str,
    transcript: str | None,
    language: str,
) -> dict[str, Any]:
    """Use OpenAI to clean the text."""
    try:
        import openai
    except ImportError:
        print("Error: openai package not installed")
        print("  pip install openai")
        sys.exit(1)

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set")
        sys.exit(1)

    client = openai.OpenAI(api_key=api_key)

    system_prompt = """You are a text processing assistant. Your job is to clean up text extracted from PDF files of religious conference talks.

The PDF extraction includes noise like:
- Page headers/footers
- Timestamps (e.g., "1/11/26, 2:27 PM")
- URLs and website references
- Page numbers
- Print metadata

Your task is to extract ONLY the actual talk content - the title, speaker attribution, and the body of the talk itself.

Return a JSON object with:
{
  "title": "The talk title",
  "speaker": "Speaker Name",
  "cleaned_text": "The full cleaned talk text",
  "notes": ["Any notes about the cleaning process or discrepancies found"]
}"""

    user_content = f"Here is raw text extracted from a PDF of a conference talk in {language}:\n\n---RAW PDF TEXT---\n{raw_text}\n---END RAW PDF TEXT---\n\n"

    if transcript:
        user_content += f"""For reference, here is a transcript of what was actually spoken in the audio recording:

---TRANSCRIPT---
{transcript}
---END TRANSCRIPT---

Use the transcript to help identify the actual talk content. Note any significant differences between the official text and transcript in the 'notes' field.

"""

    user_content += "Please clean this text and return the JSON response."

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        response_format={"type": "json_object"},
    )

    return json.loads(response.choices[0].message.content)


def process_pdf(
    pdf_path: Path,
    output_path: Path | None = None,
    use_transcript: bool = True,
    provider: str = "anthropic",
) -> Path:
    """Process a PDF file and output cleaned text.

    Args:
        pdf_path: Path to the PDF file
        output_path: Optional output path for text file
        use_transcript: Whether to use alignment.json transcript as guide
        provider: LLM provider ('anthropic' or 'openai')

    Returns:
        Path to the output text file
    """
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    lang_dir = pdf_path.parent
    lang = lang_dir.name

    if output_path is None:
        output_path = lang_dir / "text.txt"

    # Extract raw text
    print(f"Extracting text from: {pdf_path}")
    raw_text = extract_text_from_pdf(pdf_path)

    # Load transcript if available and requested
    transcript = None
    if use_transcript:
        alignment_path = lang_dir / "alignment.json"
        transcript = load_transcript(alignment_path)
        if transcript:
            print(f"Using transcript from: {alignment_path}")
        else:
            print("No transcript available, cleaning without reference")

    # Clean with LLM
    print(f"Cleaning with {provider}...")
    if provider == "anthropic":
        result = clean_with_anthropic(raw_text, transcript, lang)
    elif provider == "openai":
        result = clean_with_openai(raw_text, transcript, lang)
    else:
        raise ValueError(f"Unknown provider: {provider}")

    # Write cleaned text
    cleaned_text = result.get("cleaned_text", "")
    output_path.write_text(cleaned_text, encoding="utf-8")
    print(f"Wrote: {output_path}")

    # Write metadata/notes if present
    if result.get("notes"):
        notes_path = lang_dir / "cleaning_notes.json"
        with open(notes_path, "w", encoding="utf-8") as f:
            json.dump({
                "title": result.get("title"),
                "speaker": result.get("speaker"),
                "notes": result.get("notes"),
            }, f, ensure_ascii=False, indent=2)
        print(f"Wrote notes: {notes_path}")

    # Stats
    line_count = len(cleaned_text.split("\n"))
    char_count = len(cleaned_text)
    print(f"Lines: {line_count}, Characters: {char_count}")

    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Clean PDF text using LLM, optionally guided by transcript",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment variables:
    ANTHROPIC_API_KEY - Required for Anthropic/Claude
    OPENAI_API_KEY    - Required for OpenAI

Examples:
    # Clean single PDF (uses transcript if alignment.json exists)
    %(prog)s data/talks/2025-10-58-oaks/eng/talk.pdf

    # Clean without transcript reference
    %(prog)s data/talks/2025-10-58-oaks/eng/talk.pdf --no-transcript

    # Use OpenAI instead of Anthropic
    %(prog)s data/talks/2025-10-58-oaks/eng/talk.pdf --provider openai
        """,
    )
    parser.add_argument(
        "pdf_path",
        type=Path,
        nargs="?",
        help="Path to the PDF file",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        help="Output text file path (default: text.txt in same directory)",
    )
    parser.add_argument(
        "--no-transcript",
        action="store_true",
        help="Don't use transcript for guidance even if available",
    )
    parser.add_argument(
        "--provider", "-p",
        choices=["anthropic", "openai"],
        default="anthropic",
        help="LLM provider to use (default: anthropic)",
    )
    parser.add_argument(
        "--talk",
        help="Process all PDFs for a talk ID",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(__file__).parent.parent / "data" / "talks",
        help="Path to talks data directory",
    )

    args = parser.parse_args()

    if not check_pdftotext():
        print("Error: pdftotext not found")
        print("\nInstall poppler:")
        print("  macOS: brew install poppler")
        print("  Ubuntu: apt install poppler-utils")
        return 1

    # Process single PDF or all for a talk
    if args.talk:
        talk_dir = args.data_dir / args.talk
        if not talk_dir.exists():
            print(f"Error: Talk directory not found: {talk_dir}")
            return 1

        success = 0
        for lang_dir in talk_dir.iterdir():
            if not lang_dir.is_dir():
                continue
            pdfs = list(lang_dir.glob("*.pdf"))
            if pdfs:
                try:
                    process_pdf(
                        pdfs[0],
                        use_transcript=not args.no_transcript,
                        provider=args.provider,
                    )
                    success += 1
                except Exception as e:
                    print(f"Error processing {lang_dir.name}: {e}")

        print(f"\nProcessed {success} language(s)")
        return 0 if success > 0 else 1

    elif args.pdf_path:
        try:
            process_pdf(
                args.pdf_path,
                output_path=args.output,
                use_transcript=not args.no_transcript,
                provider=args.provider,
            )
            return 0
        except Exception as e:
            print(f"Error: {e}")
            return 1

    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
