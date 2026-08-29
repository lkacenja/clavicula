.PHONY: help lint format typecheck check

help:
	@echo "Available targets:"
	@echo "  run        Run the game"
	@echo "  lint       Run ruff linter"
	@echo "  format     Format code with ruff"
	@echo "  typecheck  Run pyright type checker"
	@echo "  check      Run lint and typecheck together"

# Run the game
run:
	uv run clavicula

# Run ruff linter
lint:
	uv run ruff check .

# Run pyright type checker
typecheck:
	uv run pyright

# Format code with ruff
format:
	uv run ruff format .

# Run both lint and typecheck
check: lint typecheck