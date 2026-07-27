.PHONY: sync test demo lint factory db-up db-down db-ingest evals

PYTHON ?= .venv/Scripts/python.exe
ifeq ($(OS),Windows_NT)
  PYTHON := .venv/Scripts/python.exe
  DOCKER := $(LOCALAPPDATA)/Programs/DockerDesktop/resources/bin/docker.exe
else
  PYTHON := .venv/bin/python
  DOCKER := docker
endif

sync:
	uv sync --python 3.12 --extra dev --system-certs

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check src tests evals

factory:
	$(PYTHON) -m evals.factory.golden_v1

evals:
	$(PYTHON) -m evals.run handoff
	$(PYTHON) -m evals.run golden
	$(PYTHON) -m evals.run judge
	$(PYTHON) -m evals.run calibrate
	$(PYTHON) -m evals.run ablation

db-up:
	$(DOCKER) compose -f deploy/docker-compose.yml up -d --build

db-down:
	$(DOCKER) compose -f deploy/docker-compose.yml down

db-ingest:
	$(PYTHON) -m geoagent.rag.ingest

demo:
	$(PYTHON) -m geoagent.demo --dry-run
