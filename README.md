# alliance-ingest

Koza ingest for Alliance of Genome Resources data, transforming gene, allele, genotype, disease association, phenotype association, and expression data into Biolink model format.

## Data Source

[Alliance of Genome Resources](https://www.alliancegenome.org/) aggregates data from model organism databases including MGI, RGD, WormBase, FlyBase, ZFIN, SGD, and Xenbase.

Data is downloaded from: `https://fms.alliancegenome.org/download/`

## Output

This ingest produces:
- **Gene nodes** - Gene entities from BGI (Basic Gene Information) files
- **Allele/Variant nodes** - Allele and variant entities
- **Genotype nodes** - Genotype/AGM (Affected Genomic Model) entities
- **Gene-disease associations** - Links genes/alleles to diseases
- **Gene-phenotype associations** - Links genes/alleles to phenotypes
- **Gene-expression associations** - Gene expression data in anatomical structures

## Transforms

| Transform | Description | Input Files |
|-----------|-------------|-------------|
| gene | Gene entities | BGI_*.json.gz |
| disease | Disease associations | DISEASE-ALLIANCE_COMBINED.tsv.gz |
| phenotype | Phenotype associations | PHENOTYPE_*.json.gz |
| expression | Expression data | EXPRESSION_*.json.gz |
| genotype | Genotype/AGM entities | AGM_*.json.gz |
| allele | Allele/variant entities | VARIANT-ALLELE_*.tsv.gz |

## Usage

```bash
# Install dependencies
just install

# Run full pipeline
just run

# Or run steps individually
just download        # Download Alliance data files
just postdownload    # Extract entity lookup files
just transform-all   # Run all Koza transforms
just test            # Run tests

# Run specific transform
just transform gene
just transform disease
```

## Requirements

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) package manager
- [just](https://github.com/casey/just) command runner

## License

BSD-3-Clause
