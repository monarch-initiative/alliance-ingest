# alliance-ingest justfile

# Package directory
PKG := "src/alliance_ingest"

# Explicitly enumerate transforms
TRANSFORMS := "gene disease phenotype expression genotype allele"

# List all commands
_default:
    @just --list

# ============== Project Management ==============

# Install dependencies
[group('project management')]
install:
    uv sync --group dev

# ============== Ingest Pipeline ==============

# Full pipeline: download -> postdownload -> transform -> postprocess -> metadata
[group('ingest')]
run: download postdownload transform-all postprocess metadata
    @echo "Done!"

# Download source data
[group('ingest')]
download: install
    uv run downloader download.yaml

# Post-download processing (extract entity lookups)
[group('ingest')]
postdownload:
    #!/usr/bin/env bash
    set -euo pipefail
    # Extract gene IDs for entity lookup
    gunzip -c data/BGI_*.json.gz 2>/dev/null | jq '.data[].basicGeneticEntity.primaryId' | sed 's@"@@g' | sed 's@$@\tbiolink:Gene@g' > data/alliance_gene.tsv || \
    cat data/BGI_*.json 2>/dev/null | jq '.data[].basicGeneticEntity.primaryId' | sed 's@"@@g' | sed 's@$@\tbiolink:Gene@g' > data/alliance_gene.tsv
    # Extract allele IDs for entity lookup
    gunzip -c data/VARIANT-ALLELE*.tsv.gz 2>/dev/null | grep -v "^#" | grep -v "^Taxon" | cut -f 3 | sort | uniq | sed 's@$@\tbiolink:SequenceVariant@g' > data/alliance_allele.tsv || \
    cat data/VARIANT-ALLELE*.tsv 2>/dev/null | grep -v "^#" | grep -v "^Taxon" | cut -f 3 | sort | uniq | sed 's@$@\tbiolink:SequenceVariant@g' > data/alliance_allele.tsv
    # Extract genotype IDs for entity lookup
    gunzip -c data/AGM_*.json.gz 2>/dev/null | jq '.data[].primaryID' | sed 's@"@@g' | sed 's@$@\tbiolink:Genotype@g' > data/alliance_genotype.tsv || \
    cat data/AGM_*.json 2>/dev/null | jq '.data[].primaryID' | sed 's@"@@g' | sed 's@$@\tbiolink:Genotype@g' > data/alliance_genotype.tsv

# Run all transforms
[group('ingest')]
transform-all: postdownload
    #!/usr/bin/env bash
    set -euo pipefail
    for t in {{TRANSFORMS}}; do
        if [ -n "$t" ]; then
            echo "Transforming $t..."
            uv run koza transform {{PKG}}/$t.yaml
        fi
    done

# Emit output/release-metadata.yaml describing this build's upstream sources and artifacts
[group('ingest')]
metadata:
    uv run python scripts/write_metadata.py

# Run specific transform
[group('ingest')]
transform NAME:
    uv run koza transform {{PKG}}/{{NAME}}.yaml

# Postprocess (no-op for alliance)
[group('ingest')]
postprocess:
    @echo "No postprocessing required"

# ============== Development ==============

# Run tests
[group('development')]
test: install
    uv run pytest

# Run tests with coverage
[group('development')]
test-cov: install
    uv run pytest --cov=. --cov-report=term-missing

# Lint code
[group('development')]
lint:
    uv run ruff check .

# Format code
[group('development')]
format:
    uv run ruff format .

# Clean output directory
[group('development')]
clean:
    rm -rf output/
