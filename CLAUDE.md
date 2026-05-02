# alliance-ingest

Koza ingest repository for transforming Alliance of Genome Resources data into Biolink model format.

## Project Structure

- `download.yaml` - Configuration for downloading Alliance data files
- `src/alliance_ingest/` - Transform code and configuration
  - `gene.py` / `gene.yaml` - Gene entities from BGI files
  - `disease.py` / `disease.yaml` - Gene/allele to disease associations
  - `phenotype.py` / `phenotype.yaml` - Gene/allele to phenotype associations
  - `expression.py` / `expression.yaml` - Gene expression data
  - `genotype.py` / `genotype.yaml` - Genotype/AGM entities
  - `allele.py` / `allele.yaml` - Allele/variant entities and gene associations
  - `alliance_entity_lookup.yaml` - Entity type lookup for phenotype/genotype transforms
  - `versions.py` - Per-ingest upstream version fetcher (consumed by `just metadata`)
- `scripts/write_metadata.py` - Emits `output/release-metadata.yaml` from `versions.py`
- `tests/` - Unit tests for transforms
- `output/` - Generated nodes and edges (gitignored)
  - `release-metadata.yaml` - Per-build manifest of upstream sources, versions, artifacts (kozahub-metadata-schema)
- `data/` - Downloaded source data (gitignored)

## Key Commands

- `just run` - Full pipeline (download -> postdownload -> transform -> postprocess)
- `just download` - Download Alliance data files
- `just postdownload` - Extract entity lookup files from downloaded data
- `just transform-all` - Run all transforms
- `just transform <name>` - Run specific transform (gene, disease, phenotype, expression, genotype, allele)
- `just metadata` - Emit `output/release-metadata.yaml`
- `just test` - Run tests

## Transforms

1. **gene** - Gene entities from Basic Gene Information (BGI) files
2. **disease** - Gene/allele to disease associations (DISEASE-ALLIANCE_COMBINED.tsv)
3. **phenotype** - Gene/allele to phenotype associations (PHENOTYPE_*.json)
4. **expression** - Gene expression data (EXPRESSION_*.json)
5. **genotype** - Genotype/AGM entities (AGM_*.json)
6. **allele** - Allele/variant entities and gene associations (VARIANT-ALLELE_*.tsv)

## Release Metadata

Every kozahub ingest emits an `output/release-metadata.yaml` describing the upstream sources, their versions, the artifacts produced, and the versions of build-time tools. This file is the contract monarch-ingest reads to assemble the merged knowledge graph's release receipt.

`src/versions.py` is the only per-ingest piece — it implements `get_source_versions()` returning a list of SourceVersion dicts. The `kozahub_metadata_schema` package provides reusable fetchers for the common patterns (HTTP Last-Modified, GitHub releases, URL-path regex, file-header parsing). The boilerplate (transform-content hashing, tool versions, build_version composition, yaml emission) is handled by `scripts/write_metadata.py`.

The `kozahub-metadata-schema` repo is expected as a sibling checkout (path-dep). Switch to a git or PyPI dep once published.

## Post-Download Processing

The `postdownload` step extracts entity IDs for lookup files used by some transforms:
- `data/alliance_gene.tsv` - Gene IDs for entity lookup
- `data/alliance_allele.tsv` - Allele IDs for entity lookup
- `data/alliance_genotype.tsv` - Genotype IDs for entity lookup

## Data Sources

All data is downloaded from the Alliance of Genome Resources FMS: `https://fms.alliancegenome.org/download/`

Includes data from: MGI, RGD, WB (WormBase), FB (FlyBase), ZFIN, SGD, Xenbase

## Skills

- `.claude/skills/create-koza-ingest.md` - Create new koza ingests
- `.claude/skills/update-template.md` - Update to latest template version
