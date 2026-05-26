CONDA_ENV ?= pogo-team-optimizer
CONDA_RUN ?= conda run -n $(CONDA_ENV)
PYTHON ?= $(CONDA_RUN) python
SRC := src
META ?= bfmaster
DIAGNOSTICS ?= 0
WORKERS ?= 8
DIAGNOSTICS_FLAG := $(if $(filter 1 true yes,$(DIAGNOSTICS)),--diagnostics,)

.PHONY: help env-create env-update lint typecheck test coverage run all

help:
	@printf "Targets:\n"
	@printf "  make env-create  Create Conda environment from environment.yml\n"
	@printf "  make env-update  Update Conda environment from environment.yml\n"
	@printf "  make lint        Run ruff\n"
	@printf "  make typecheck   Run mypy\n"
	@printf "  make test        Run pytest\n"
	@printf "  make coverage    Run pytest with coverage\n"
	@printf "  make run META=bayou         Run analysis and write all outputs\n"
	@printf "  make run META=bayou DIAGNOSTICS=1  Run analysis with progress logging\n"
	@printf "  make run META=bayou WORKERS=2      Run analysis with process workers\n"
	@printf "  make all         lint + typecheck + test\n"

env-create:
	conda env create -f environment.yml

env-update:
	conda env update -n $(CONDA_ENV) -f environment.yml --prune

lint:
	PYTHONPATH=$(SRC) $(PYTHON) -m ruff check src tests

typecheck:
	PYTHONPATH=$(SRC) $(PYTHON) -m mypy src

test:
	PYTHONPATH=$(SRC) $(PYTHON) -m pytest

coverage:
	PYTHONPATH=$(SRC) $(PYTHON) -m pytest --cov=src --cov-report=term-missing

run:
	PYTHONPATH=$(SRC) $(PYTHON) -m pogo_team_optimizer.cli.main --meta $(META) --top-threats 10 --top-lineups 10 --restarts 80 --workers $(WORKERS) $(DIAGNOSTICS_FLAG)
