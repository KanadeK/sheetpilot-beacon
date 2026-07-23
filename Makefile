PYTHON ?= python

.PHONY: install lint format-check typecheck test build verify

install:
	$(PYTHON) -m pip install -e ".[dev]"

lint:
	$(PYTHON) -m ruff check .

format-check:
	$(PYTHON) -m ruff format --check .

typecheck:
	$(PYTHON) -m mypy src

test:
	$(PYTHON) -m pytest -q --cov=src --cov-report=term-missing --cov-fail-under=80

build:
	$(PYTHON) -m build

verify: lint format-check typecheck test build
