PYTHON ?= python3
SRC := src
META ?= bfmaster

.PHONY: help lint typecheck test coverage run all

help:
	@printf "Targets:\n"
	@printf "  make lint        Run ruff\n"
	@printf "  make typecheck   Run mypy\n"
	@printf "  make test        Run pytest\n"
	@printf "  make coverage    Run pytest with coverage\n"
	@printf "  make run META=bayou         Run analysis and write all outputs\n"
	@printf "  make all         lint + typecheck + test\n"

lint:
	PYTHONPATH=$(SRC) $(PYTHON) -m ruff check src tests

typecheck:
	PYTHONPATH=$(SRC) $(PYTHON) -m mypy src

test:
	PYTHONPATH=$(SRC) $(PYTHON) -m pytest

coverage:
	PYTHONPATH=$(SRC) $(PYTHON) -m pytest --cov=src --cov-report=term-missing

run:
	PYTHONPATH=$(SRC) $(PYTHON) -m pogo_team_optimizer.cli.main --meta $(META) --top-threats 10 --top-cores 10 --restarts 80
