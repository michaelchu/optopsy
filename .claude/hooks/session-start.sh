#!/bin/bash
set -euo pipefail

# Only run in remote (web) environments
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "$CLAUDE_PROJECT_DIR"

VENV_DIR="$CLAUDE_PROJECT_DIR/venv"
PYTHON="python3.12"

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
  "$PYTHON" -m venv "$VENV_DIR"
fi

# Activate the virtual environment
source "$VENV_DIR/bin/activate"

# Install package in editable mode + dev tools
# Prefer uv for speed, fall back to pip
if command -v uv &>/dev/null; then
  uv pip install -e .
  uv pip install ruff mypy pytest pytest-cov pre-commit types-requests
else
  pip install -e .
  pip install ruff mypy pytest pytest-cov pre-commit types-requests
fi

# Install pre-commit hooks into the git repo
pre-commit install
