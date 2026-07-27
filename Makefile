.PHONY: sync test demo lint factory

PYTHON ?= .venv/Scripts/python.exe
ifeq ($(OS),Windows_NT)
  PYTHON := .venv/Scripts/python.exe
else
  PYTHON := .venv/bin/python
endif

sync:
	uv sync --python 3.12 --extra dev --system-certs

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check src tests evals

factory:
	$(PYTHON) -m evals.factory.seed

demo:
	$(PYTHON) -m geoagent.demo --dry-run
