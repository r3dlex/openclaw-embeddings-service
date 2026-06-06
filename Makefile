# openclaw-embeddings-service Makefile
# Variant 3-PR sequence sub-PR 2 (RALPLAN §4.3 Wave 2.PY.C, F3).
# `make ci` is the local-gate for sub-PR 2 — must pass before sub-PR 3
# turns on the 90% hard gate. Sub-PR 3 swaps `make ci` to include a
# --cov-fail-under check, and the .coverage_baseline ratchet becomes a
# hard floor.
.PHONY: ci lint test coverage-ratchet help

help:
	@echo "Usage: make [target]"
	@echo "  ci                 — Run the full local CI gate (lint + test + ratchet)"
	@echo "  lint               — Run ruff lint"
	@echo "  test               — Run pytest with coverage"
	@echo "  coverage-ratchet   — Assert coverage >= .coverage_baseline"

ci: lint test coverage-ratchet

lint:
	uv run ruff check server.py tests/

test:
	uv run pytest --cov=. --cov-report=term-missing -v

coverage-ratchet:
	@PCT=$$(uv run pytest --cov=. --cov-report=term -q 2>&1 \
		| grep -E '^TOTAL\s+[0-9]+\s+[0-9]+\s+([0-9]+)%' \
		| awk '{print $$4}' | tr -d '%'); \
	if [ -z "$$PCT" ]; then \
		echo "ERROR: could not parse coverage from pytest output"; \
		exit 1; \
	fi; \
	BASELINE=$$(grep '^current_pct' .coverage_baseline | awk -F'= ' '{print $$2}'); \
	echo "Coverage: $${PCT}% (baseline: $${BASELINE}%)"; \
	if [ "$$PCT" -lt "$$BASELINE" ]; then \
		echo "ERROR: coverage $${PCT}% is below the .coverage_baseline ratchet ($${BASELINE}%)"; \
		echo "If this is a justified drop, update .coverage_baseline with a justification comment."; \
		exit 1; \
	fi
