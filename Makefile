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

.PHONY: post-download
post-download:
	gunzip -c data/BGI_*.json.gz 2>/dev/null | jq '.data[].basicGeneticEntity.primaryId' | sed 's@\"@@g'  | sed 's@$$@\tbiolink:Gene@g' > data/alliance_gene.tsv || \
	cat data/BGI_*.json 2>/dev/null | jq '.data[].basicGeneticEntity.primaryId' | sed 's@\"@@g'  | sed 's@$$@\tbiolink:Gene@g' > data/alliance_gene.tsv
	gunzip -c data/VARIANT-ALLELE*.tsv.gz 2>/dev/null | grep -v "^#" | grep -v "^Taxon" | cut -f 3 | sort | uniq | sed 's@$$@\tbiolink:SequenceVariant@g' > data/alliance_allele.tsv || \
	cat data/VARIANT-ALLELE*.tsv 2>/dev/null | grep -v "^#" | grep -v "^Taxon" | cut -f 3 | sort | uniq | sed 's@$$@\tbiolink:SequenceVariant@g' > data/alliance_allele.tsv
	gunzip -c data/AGM_*.json.gz 2>/dev/null | jq '.data[].primaryID' | sed 's@\"@@g'  | sed 's@$$@\tbiolink:Genotype@g' > data/alliance_genotype.tsv || \
	cat data/AGM_*.json 2>/dev/null | jq '.data[].primaryID' | sed 's@\"@@g'  | sed 's@$$@\tbiolink:Genotype@g' > data/alliance_genotype.tsv

.PHONY: transform
transform:
	$(RUN) koza transform src/alliance_ingest/gene.yaml --output-dir output --output-format tsv
	$(RUN) koza transform src/alliance_ingest/disease.yaml --output-dir output --output-format tsv
	$(RUN) koza transform src/alliance_ingest/phenotype.yaml --output-dir output --output-format tsv
	$(RUN) koza transform src/alliance_ingest/expression.yaml --output-dir output --output-format tsv
	$(RUN) koza transform src/alliance_ingest/genotype.yaml --output-dir output --output-format tsv
	$(RUN) koza transform src/alliance_ingest/allele.yaml --output-dir output --output-format tsv

# Individual transform targets for testing
.PHONY: transform-gene
transform-gene:
	$(RUN) koza transform src/alliance_ingest/gene.yaml --output-dir output --output-format tsv

.PHONY: transform-disease
transform-disease:
	$(RUN) koza transform src/alliance_ingest/disease.yaml --output-dir output --output-format tsv

.PHONY: transform-phenotype
transform-phenotype:
	$(RUN) koza transform src/alliance_ingest/phenotype.yaml --output-dir output --output-format tsv

.PHONY: transform-expression
transform-expression:
	$(RUN) koza transform src/alliance_ingest/expression.yaml --output-dir output --output-format tsv

.PHONY: transform-genotype
transform-genotype:
	$(RUN) koza transform src/alliance_ingest/genotype.yaml --output-dir output --output-format tsv

.PHONY: transform-allele
transform-allele:
	$(RUN) koza transform src/alliance_ingest/allele.yaml --output-dir output --output-format tsv

.PHONY: run
run: download post-download transform
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
