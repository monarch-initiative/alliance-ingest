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
- `tests/` - Unit tests for transforms
- `output/` - Generated nodes and edges (gitignored)
- `data/` - Downloaded source data (gitignored)

## Key Commands

- `just run` - Full pipeline (download -> postdownload -> transform -> postprocess)
- `just download` - Download Alliance data files
- `just postdownload` - Extract entity lookup files from downloaded data
- `just transform-all` - Run all transforms
- `just transform <name>` - Run specific transform (gene, disease, phenotype, expression, genotype, allele)
- `just test` - Run tests

## Transforms

1. **gene** - Gene entities from Basic Gene Information (BGI) files
2. **disease** - Gene/allele to disease associations (DISEASE-ALLIANCE_COMBINED.tsv)
3. **phenotype** - Gene/allele to phenotype associations (PHENOTYPE_*.json)
4. **expression** - Gene expression data (EXPRESSION_*.json)
5. **genotype** - Genotype/AGM entities (AGM_*.json)
6. **allele** - Allele/variant entities and gene associations (VARIANT-ALLELE_*.tsv)

## Post-Download Processing

The `postdownload` step extracts entity IDs for lookup files used by some transforms:
- `data/alliance_gene.tsv` - Gene IDs for entity lookup
- `data/alliance_allele.tsv` - Allele IDs for entity lookup
- `data/alliance_genotype.tsv` - Genotype IDs for entity lookup

## Data Sources

All data is downloaded from the Alliance of Genome Resources FMS: `https://fms.alliancegenome.org/download/`

Includes data from: MGI, RGD, WB (WormBase), FB (FlyBase), ZFIN, SGD, Xenbase
