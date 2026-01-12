# Gospel Language Study - Project Makefile
#
# Quick start:
#   make install        - Install all dependencies
#   make dev            - Start backend + frontend
#   make process-new    - Process all new talks (preprocess PDFs + generate alignments)

.PHONY: help dev backend frontend test lint install install-alignment \
        align preprocess-pdf process-new preprocess-all align-all status clean

DATA_DIR := data/talks

# Default target
help:
	@echo "Gospel Language Study - Available targets:"
	@echo ""
	@echo "Development:"
	@echo "  make dev              - Start backend and frontend (in parallel)"
	@echo "  make backend          - Start FastAPI backend on :8000"
	@echo "  make frontend         - Start SvelteKit frontend on :5173"
	@echo ""
	@echo "Testing & Quality:"
	@echo "  make test             - Run all tests"
	@echo "  make lint             - Run all linters"
	@echo ""
	@echo "Setup:"
	@echo "  make install          - Install all dependencies"
	@echo "  make install-alignment - Install WhisperX (~3GB download)"
	@echo ""
	@echo "Data Processing (auto-discovery):"
	@echo "  make status           - Show what needs processing"
	@echo "  make process-new      - Process all new talks (align + clean)"
	@echo "  make align-all        - Generate transcripts (WhisperX) for talks with MP3"
	@echo "  make clean-all        - Clean PDFs with LLM (uses transcript as guide)"
	@echo ""
	@echo "Data Processing (manual):"
	@echo "  make align TALK=<id> LANGS=\"eng zhs\"  - Generate alignment for specific talk"
	@echo "  make clean-pdf PDF=<path>  - Clean single PDF with LLM"
	@echo ""
	@echo "Environment variables:"
	@echo "  ANTHROPIC_API_KEY     - Required for LLM text cleaning"
	@echo "  PROVIDER=openai       - Use OpenAI instead of Anthropic for cleaning"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean            - Remove build artifacts"

# =============================================================================
# Development
# =============================================================================

dev:
	@echo "Starting backend and frontend..."
	@make -j2 backend frontend

backend:
	cd backend && source .venv/bin/activate && uvicorn gls.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

# =============================================================================
# Testing
# =============================================================================

test: test-backend test-frontend

test-backend:
	cd backend && source .venv/bin/activate && pytest -v

test-frontend:
	cd frontend && npm run test 2>/dev/null || echo "No tests configured yet"

# =============================================================================
# Linting
# =============================================================================

lint: lint-backend lint-frontend

lint-backend:
	cd backend && source .venv/bin/activate && ruff check src tests && mypy src --ignore-missing-imports

lint-frontend:
	cd frontend && npm run check && npm run lint

# =============================================================================
# Installation
# =============================================================================

install: install-backend install-frontend

install-backend:
	cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"

install-frontend:
	cd frontend && npm install

install-alignment:
	@echo "Installing WhisperX alignment dependencies..."
	@echo "This will download ~3GB of models on first use."
	cd backend && source .venv/bin/activate && pip install -e ".[alignment]"

# =============================================================================
# Data Processing
# =============================================================================

MODEL ?= large-v3

# Show status of all talks - what needs processing
status:
	@echo "=== Talk Processing Status ==="
	@echo ""
	@for talk_dir in $(DATA_DIR)/*/; do \
		talk_id=$$(basename "$$talk_dir"); \
		echo "Talk: $$talk_id"; \
		for lang_dir in "$$talk_dir"*/; do \
			[ -d "$$lang_dir" ] || continue; \
			lang=$$(basename "$$lang_dir"); \
			pdf_count=$$(find "$$lang_dir" -name "*.pdf" 2>/dev/null | wc -l | tr -d ' '); \
			txt_count=$$(find "$$lang_dir" -name "*.txt" 2>/dev/null | wc -l | tr -d ' '); \
			has_align=$$([ -f "$$lang_dir/alignment.json" ] && echo "yes" || echo "no"); \
			has_mp3=$$(find "$$lang_dir" -name "*.mp3" 2>/dev/null | head -1); \
			echo "  $$lang: pdf=$$pdf_count txt=$$txt_count aligned=$$has_align"; \
		done; \
		echo ""; \
	done

# Process everything that needs it
# Order: 1) Generate transcripts (WhisperX), 2) Clean PDFs (LLM guided by transcript)
process-new: align-all clean-all
	@echo ""
	@echo "=== All processing complete ==="

# Clean all PDFs using LLM (uses transcript from alignment.json if available)
# Set PROVIDER=openai to use OpenAI instead of Anthropic
PROVIDER ?= anthropic

clean-all:
	@echo "=== Cleaning PDFs with LLM ==="
	@found=0; \
	for talk_dir in $(DATA_DIR)/*/; do \
		[ -d "$$talk_dir" ] || continue; \
		for lang_dir in "$$talk_dir"*/; do \
			[ -d "$$lang_dir" ] || continue; \
			if [ ! -f "$$lang_dir/text.txt" ]; then \
				pdf=$$(find "$$lang_dir" -name "*.pdf" 2>/dev/null | head -1); \
				if [ -n "$$pdf" ]; then \
					echo "Cleaning: $$pdf"; \
					cd backend && source .venv/bin/activate && python ../scripts/clean_text.py "../$$pdf" --provider $(PROVIDER) || true; \
					cd ..; \
					found=1; \
				fi; \
			fi; \
		done; \
	done; \
	if [ $$found -eq 0 ]; then echo "All PDFs already cleaned."; fi

# Legacy: basic regex preprocessing (use clean-all instead for better results)
preprocess-all:
	@echo "=== Preprocessing PDFs (basic) ==="
	@found=0; \
	for pdf in $$(find $(DATA_DIR) -name "*.pdf" 2>/dev/null); do \
		txt="$${pdf%.pdf}.txt"; \
		if [ ! -f "$$txt" ]; then \
			echo "Processing: $$pdf"; \
			lang_dir=$$(dirname "$$pdf"); \
			lang=$$(basename "$$lang_dir"); \
			python scripts/preprocess_pdf.py "$$pdf" --language "$$lang" --output "$$txt" || true; \
			found=1; \
		fi; \
	done; \
	if [ $$found -eq 0 ]; then echo "No unprocessed PDFs found."; fi

# Generate alignments for all language dirs that have MP3 but no alignment.json
# Uses OpenAI Whisper API (requires OPENAI_API_KEY in .env)
align-all:
	@echo "=== Generating Alignments (OpenAI Whisper) ==="
	@found=0; \
	for talk_dir in $(DATA_DIR)/*/; do \
		[ -d "$$talk_dir" ] || continue; \
		talk_id=$$(basename "$$talk_dir"); \
		langs_to_process=""; \
		for lang_dir in "$$talk_dir"*/; do \
			[ -d "$$lang_dir" ] || continue; \
			lang=$$(basename "$$lang_dir"); \
			has_mp3=$$(find "$$lang_dir" -name "*.mp3" 2>/dev/null | head -1); \
			if [ -n "$$has_mp3" ] && [ ! -f "$$lang_dir/alignment.json" ]; then \
				langs_to_process="$$langs_to_process $$lang"; \
			fi; \
		done; \
		if [ -n "$$langs_to_process" ]; then \
			echo "Processing: $$talk_id -$$langs_to_process"; \
			cd backend && source .venv/bin/activate && python ../scripts/transcribe_openai.py "$$talk_id" $$langs_to_process; \
			cd ..; \
			found=1; \
		fi; \
	done; \
	if [ $$found -eq 0 ]; then echo "No talks need alignment."; fi

# Alternative: Use local WhisperX (requires make install-alignment, may have PyTorch issues)
align-whisperx:
	@echo "=== Generating Alignments (WhisperX local) ==="
	@for talk_dir in $(DATA_DIR)/*/; do \
		[ -d "$$talk_dir" ] || continue; \
		talk_id=$$(basename "$$talk_dir"); \
		langs_to_process=""; \
		for lang_dir in "$$talk_dir"*/; do \
			[ -d "$$lang_dir" ] || continue; \
			lang=$$(basename "$$lang_dir"); \
			has_mp3=$$(find "$$lang_dir" -name "*.mp3" 2>/dev/null | head -1); \
			if [ -n "$$has_mp3" ] && [ ! -f "$$lang_dir/alignment.json" ]; then \
				langs_to_process="$$langs_to_process $$lang"; \
			fi; \
		done; \
		if [ -n "$$langs_to_process" ]; then \
			cd backend && source .venv/bin/activate && python ../scripts/generate_alignment.py "$$talk_id" $$langs_to_process --model $(MODEL); \
			cd ..; \
		fi; \
	done

# Manual: align specific talk
# Usage: make align TALK=2025-10-58-oaks LANGS="eng zhs"
TALK ?=
LANGS ?=

align:
ifndef TALK
	$(error TALK is required. Usage: make align TALK=2025-10-58-oaks LANGS="eng zhs")
endif
ifndef LANGS
	$(error LANGS is required. Usage: make align TALK=2025-10-58-oaks LANGS="eng zhs")
endif
	cd backend && source .venv/bin/activate && python ../scripts/generate_alignment.py $(TALK) $(LANGS) --model $(MODEL)

# Manual: clean single PDF with LLM
# Usage: make clean-pdf PDF=path/to/talk.pdf
PDF ?=

clean-pdf:
ifndef PDF
	$(error PDF is required. Usage: make clean-pdf PDF=path/to/talk.pdf)
endif
	python scripts/clean_text.py "$(PDF)" --provider $(PROVIDER)

# Legacy: basic regex preprocessing (use clean-pdf instead)
preprocess-pdf:
ifndef PDF
	$(error PDF is required. Usage: make preprocess-pdf PDF=path/to/talk.pdf)
endif
	@lang_dir=$$(dirname "$(PDF)"); \
	lang=$$(basename "$$lang_dir"); \
	txt="$${PDF%.pdf}.txt"; \
	python scripts/preprocess_pdf.py "$(PDF)" --language "$$lang" --output "$$txt"

# =============================================================================
# Cleanup
# =============================================================================

clean:
	@echo "Cleaning build artifacts..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "node_modules/.cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".svelte-kit" -exec rm -rf {} + 2>/dev/null || true
	@echo "Done."
