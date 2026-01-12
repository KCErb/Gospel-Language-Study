#!/usr/bin/env python3
"""Preprocess PDF files to extract and clean text for talks.

This script:
1. Runs pdftotext to extract raw text from PDF
2. Cleans common noise (timestamps, URLs, page numbers, headers/footers)
3. Outputs clean text file

The cleaned text is the "official" text for reading. The alignment.json
(from generate_alignment.py) contains WhisperX's transcription of what
was actually spoken - these may differ slightly.

Usage:
    python scripts/preprocess_pdf.py path/to/talk.pdf
    python scripts/preprocess_pdf.py path/to/talk.pdf --output path/to/text.txt

Requirements:
    pdftotext (from poppler-utils)
    macOS: brew install poppler
    Ubuntu: apt install poppler-utils
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path


def check_pdftotext() -> bool:
    """Check if pdftotext is available."""
    return shutil.which("pdftotext") is not None


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract text from PDF using pdftotext."""
    result = subprocess.run(
        ["pdftotext", "-layout", str(pdf_path), "-"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def clean_lds_talk_text(text: str) -> str:
    """Clean extracted text from LDS conference talk PDFs.

    Removes common noise patterns:
    - Page numbers
    - URLs and website references
    - Timestamps (MM:SS format)
    - Headers/footers with dates
    - Extra whitespace
    - Form feed characters
    """
    lines = text.split("\n")
    cleaned_lines = []

    for line in lines:
        # Skip empty lines (will consolidate later)
        stripped = line.strip()
        if not stripped:
            cleaned_lines.append("")
            continue

        # Skip lines that are just page numbers
        if re.match(r"^\d+$", stripped):
            continue

        # Skip lines that are URLs or website references
        if re.match(r"^(https?://|www\.)", stripped, re.IGNORECASE):
            continue
        if "churchofjesuschrist.org" in stripped.lower():
            continue

        # Skip timestamp lines (e.g., "12:34" or "[12:34]")
        if re.match(r"^\[?\d{1,2}:\d{2}\]?$", stripped):
            continue

        # Skip common header/footer patterns
        if re.match(r"^(october|april|january|july)\s+\d{4}$", stripped, re.IGNORECASE):
            continue
        if re.match(r"^general\s+conference$", stripped, re.IGNORECASE):
            continue
        if re.match(r"^(saturday|sunday)\s+(morning|afternoon|evening)", stripped, re.IGNORECASE):
            continue

        # Remove inline timestamps like [12:34]
        line = re.sub(r"\s*\[\d{1,2}:\d{2}\]\s*", " ", line)

        # Remove form feed and other control characters
        line = re.sub(r"[\x0c\x00-\x08\x0b\x0e-\x1f]", "", line)

        # Clean up multiple spaces
        line = re.sub(r"  +", " ", line)

        cleaned_lines.append(line.rstrip())

    # Join and clean up multiple blank lines
    text = "\n".join(cleaned_lines)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Strip leading/trailing whitespace
    text = text.strip()

    return text


def clean_chinese_text(text: str) -> str:
    """Additional cleaning for Chinese text."""
    # Chinese text may have different patterns
    # Remove any ASCII timestamps that might appear
    text = re.sub(r"\[\d{1,2}:\d{2}\]", "", text)

    # Remove page numbers that might be formatted differently
    text = re.sub(r"^\s*第?\d+页?\s*$", "", text, flags=re.MULTILINE)

    return text


def process_pdf(
    pdf_path: Path,
    output_path: Path | None = None,
    language: str = "eng",
) -> Path:
    """Process a PDF file and output cleaned text.

    Args:
        pdf_path: Path to the PDF file
        output_path: Optional output path (defaults to same dir with .txt extension)
        language: Language code for language-specific cleaning

    Returns:
        Path to the output text file
    """
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    if output_path is None:
        output_path = pdf_path.with_suffix(".txt")

    print(f"Extracting text from: {pdf_path}")
    raw_text = extract_text_from_pdf(pdf_path)

    print("Cleaning text...")
    cleaned_text = clean_lds_talk_text(raw_text)

    # Apply language-specific cleaning
    if language in ("zhs", "zht", "zh"):
        cleaned_text = clean_chinese_text(cleaned_text)

    # Write output
    output_path.write_text(cleaned_text, encoding="utf-8")
    print(f"Wrote: {output_path}")

    # Stats
    line_count = len(cleaned_text.split("\n"))
    word_count = len(cleaned_text.split())
    char_count = len(cleaned_text)
    print(f"Lines: {line_count}, Words: {word_count}, Characters: {char_count}")

    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract and clean text from conference talk PDFs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s talk.pdf
    %(prog)s talk.pdf --output text.txt
    %(prog)s talk.pdf --language zhs
        """,
    )
    parser.add_argument(
        "pdf_path",
        type=Path,
        help="Path to the PDF file",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        help="Output text file path (default: same name with .txt extension)",
    )
    parser.add_argument(
        "--language", "-l",
        default="eng",
        help="Language code for language-specific cleaning (default: eng)",
    )

    args = parser.parse_args()

    if not check_pdftotext():
        print("Error: pdftotext not found")
        print("\nInstall poppler:")
        print("  macOS: brew install poppler")
        print("  Ubuntu: apt install poppler-utils")
        return 1

    try:
        process_pdf(
            pdf_path=args.pdf_path,
            output_path=args.output,
            language=args.language,
        )
        return 0
    except subprocess.CalledProcessError as e:
        print(f"Error running pdftotext: {e}")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
