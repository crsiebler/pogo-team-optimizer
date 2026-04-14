PYTHON ?= python3
SRC := src

.PHONY: help lint typecheck test coverage run run-json run-md run-pvpoke all

help:
	@printf "Targets:\n"
	@printf "  make lint        Run ruff\n"
	@printf "  make typecheck   Run mypy\n"
	@printf "  make test        Run pytest\n"
	@printf "  make coverage    Run pytest with coverage\n"
	@printf "  make run         Run text analysis report\n"
	@printf "  make run-json    Write JSON analysis report\n"
	@printf "  make run-md      Write Markdown analysis report\n"
	@printf "  make run-pvpoke  Write PvPoke import export\n"
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
	PYTHONPATH=$(SRC) $(PYTHON) -m pogo_team_optimizer.cli.main --meta bfmaster --format text --top-threats 10 --top-cores 5 --restarts 80

run-json:
	PYTHONPATH=$(SRC) $(PYTHON) -m pogo_team_optimizer.cli.main --meta bfmaster --format json --output analysis.json --top-threats 10 --top-cores 5 --restarts 80

run-md:
	PYTHONPATH=$(SRC) $(PYTHON) -m pogo_team_optimizer.cli.main --meta bfmaster --format markdown --output analysis.md --top-threats 10 --top-cores 5 --restarts 80

run-pvpoke:
	PYTHONPATH=$(SRC) $(PYTHON) -m pogo_team_optimizer.cli.main --meta bfmaster --format pvpoke --output analysis.pvpoke --top-threats 10 --top-cores 5 --restarts 80

all: lint typecheck test
