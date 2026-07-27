.PHONY: sync test demo lint

PYTHON ?= .venv/Scripts/python.exe
ifeq ($(OS),Windows_NT)
  PYTHON := .venv/Scripts/python.exe
else
  PYTHON := .venv/bin/python
endif

sync:
	uv sync --python 3.12 --extra dev

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check src tests

demo:
	$(PYTHON) -m geoagent.demo --dry-run
