.PHONY: sync sync-dev unittest test-all test-integration dev help

help:
	@echo "Available commands:"
	@echo "  sync             - Install production dependencies"
	@echo "  sync-dev         - Install all dependencies including development"
	@echo "  unittest         - Run only unit tests (excluding integration)"
	@echo "  test-all         - Run all tests (unit + integration)"
	@echo "  test-integration - Run only integration tests"
	@echo "  dev              - Start MCP server in development mode"

sync:
	uv sync --no-dev

sync-dev:
	uv sync

unittest:
	uv run pytest -m "not integration"

test-all:
	uv run pytest

test-integration:
	uv run pytest -m integration

dev:
	mcp dev ./src/server.py
