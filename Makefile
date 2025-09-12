ROOTDIR = $(shell pwd)
RUN = uv run

### Help ###

define HELP
╭───────────────────────────────────────────────────────────╮
│  Makefile for alliance-ingest (multi-transform)          │
│ ───────────────────────────────────────────────────────── │
│ Usage:                                                    │
│     make <target>                                         │
│                                                           │
│ Main Targets:                                             │
│     help                Print this help message           │
│     all                 Install everything and test       │
│     install             UV install package                │
│     download            Download data for ALL ingests     │
│     run                 Run ALL transforms                │
│     test                Run all tests                     │
│                                                           │
│ Individual Ingest Targets:                                │
│     run-disease         Run disease association ingest    │
│     run-genotype        Run genotype ingest               │
│     run-phenotype       Run phenotype association ingest  │
│                                                           │
│ Other Targets:                                            │
│     docs                Generate documentation            │
│     lint                Lint all code                     │
│     format              Format all code                   │
│     clean               Clean up build artifacts          │
╰───────────────────────────────────────────────────────────╯
endef
export HELP

.PHONY: help
help:
	@printf "$${HELP}"


### Installation and Setup ###

.PHONY: fresh
fresh: clean clobber all

.PHONY: all
all: install test

.PHONY: install
install: 
	uv sync --dev


### Documentation ###

.PHONY: docs
docs:
	$(RUN) mkdocs build


### Testing ###

.PHONY: test
test:
	$(RUN) pytest tests


### Running ###

.PHONY: download
download:
	$(RUN) ingest download

.PHONY: transform  
transform:
	$(RUN) ingest transform

.PHONY: run
run:
	$(RUN) ingest run
	$(RUN) python scripts/generate-report.py

# Discover what would be run
.PHONY: discover
discover:
	$(RUN) ingest discover


### Linting, Formatting, and Cleaning ###

.PHONY: clean
clean:
	rm -f `find . -type f -name '*.py[co]' `
	rm -rf `find . -name __pycache__` \
		.venv .ruff_cache .pytest_cache **/.ipynb_checkpoints

.PHONY: clobber
clobber:
	# Add any files to remove here
	@echo "Nothing to remove. Add files to remove to clobber target."

.PHONY: lint
lint: 
	$(RUN) ruff check --diff --exit-zero
	$(RUN) black -l 120 --check --diff src tests

.PHONY: format
format: 
	$(RUN) ruff check --fix --exit-zero
	$(RUN) black -l 120 src tests
