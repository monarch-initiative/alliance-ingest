# alliance-ingest

The [Alliance of Genome Resources](https://www.alliancegenome.org/) contains a subset of model organism data from member databases that is harmonized to the same model. The Alliance has bulk data downloads, ingest data formats, and an API. In some cases it may continue to be more practical to load from individual MODs when data is not yet fully harmonized in the Alliance.

- [Alliance Bulk Downloads](https://www.alliancegenome.org/downloads)
- [Alliance schemas](https://github.com/alliance-genome/agr_schemas)

## Data Source

Data is downloaded from: `https://fms.alliancegenome.org/download/`

### Species Included

- Human (NCBITaxon:9606)
- Mouse (NCBITaxon:10090)
- Rat (NCBITaxon:10116)
- Zebrafish (NCBITaxon:7955)
- Fruit fly (NCBITaxon:7227)
- C. elegans (NCBITaxon:6239)
- Baker's yeast (NCBITaxon:4932)
- Frog (NCBITaxon:8364)

Data sources: MGI, RGD, WormBase, FlyBase, ZFIN, SGD, Xenbase

## Output

### Gene

Gene entities from [BGI (Basic Gene Information)](https://github.com/alliance-genome/agr_schemas/tree/master/ingest/gene) ingest files for all Alliance species.

**Biolink captured:**

- `biolink:Gene`
    - id (gene CURIE)
    - symbol
    - name
    - type (SO term for gene type)
    - in_taxon (NCBI Taxon ID)
    - in_taxon_label (species name)
    - xref (cross-references)
    - synonym
    - provided_by (source database)

### Disease

Disease associations from the combined Alliance disease file. Supports gene, allele, and genotype (affected genomic model) subjects. Only "is_model_of" association types are currently processed; rows with experimental conditions (except "standard conditions") or modifiers are filtered.

**Biolink captured:**

- `biolink:GeneToDiseaseAssociation`
    - id (UUID)
    - subject (gene ID)
    - predicate (`biolink:related_to`)
    - object (DOID)
    - has_evidence (evidence code)
    - publications
    - primary_knowledge_source (source database)
    - aggregator_knowledge_source (`["infores:monarchinitiative", "infores:agrkb"]`)

- `biolink:VariantToDiseaseAssociation`
    - id (UUID)
    - subject (allele ID)
    - predicate (`biolink:related_to`)
    - object (DOID)
    - has_evidence, publications, knowledge sources (as above)

- `biolink:GenotypeToDiseaseAssociation`
    - id (UUID)
    - subject (affected genomic model ID)
    - predicate (`biolink:model_of`)
    - object (DOID)
    - has_evidence, publications, knowledge sources (as above)

### Phenotype

Phenotype associations using the [phenotype ingest format](https://github.com/alliance-genome/agr_schemas/tree/master/ingest/phenotype). This file contains gene, allele, and genotype phenotypes. An entity lookup file is used to determine subject category. Environmental conditions are captured as qualifiers.

**Biolink captured:**

- `biolink:GeneToPhenotypicFeatureAssociation`
    - id (UUID)
    - subject (gene ID)
    - predicate (`biolink:has_phenotype`)
    - object (phenotype term ID)
    - publications
    - qualifiers (condition class IDs)
    - primary_knowledge_source (source database)
    - aggregator_knowledge_source (`["infores:monarchinitiative", "infores:agrkb"]`)

- `biolink:GenotypeToPhenotypicFeatureAssociation`
    - subject (genotype ID), fields as above

- `biolink:VariantToPhenotypicFeatureAssociation`
    - subject (variant ID), fields as above

### Expression

Gene expression data. The full data model of the Alliance expression file includes Species, GeneID, GeneSymbol, Location, StageTerm, AssayID, CellularComponentID, AnatomyTermID, and more. Not all fields are currently populated in all input data sets.

**Discussion Group**: https://www.alliancegenome.org/working-groups#expression
**Download**: https://www.alliancegenome.org/downloads#expression

**Biolink captured:**

- `biolink:GeneToExpressionSiteAssociation`
    - id (UUID)
    - subject (gene ID)
    - predicate (`biolink:expressed_in`)
    - object (anatomical structure term ID or cellular component term ID)
    - stage_qualifier (stage term ID, when available)
    - qualifiers (assay type)
    - publications
    - primary_knowledge_source (source database)
    - aggregator_knowledge_source (`["infores:monarchinitiative", "infores:agrkb"]`)

### Genotype

Genotype/AGM (Affected Genomic Model) entities and their associations to alleles and genes.

**Biolink captured:**

- `biolink:Genotype`
    - id (genotype ID)
    - name
    - type (subtype)
    - in_taxon (NCBI Taxon ID)
    - in_taxon_label

- `biolink:GenotypeToVariantAssociation`
    - id (UUID)
    - subject (genotype ID)
    - predicate (`biolink:has_sequence_variant`)
    - object (allele ID)
    - qualifier (zygosity)
    - primary_knowledge_source, aggregator_knowledge_source

- `biolink:GenotypeToGeneAssociation`
    - id (UUID)
    - subject (genotype ID)
    - predicate (`biolink:related_to`)
    - object (gene ID, from allele lookup)
    - primary_knowledge_source, aggregator_knowledge_source

### Allele

Allele/variant entities and their associations to genes.

**Biolink captured:**

- `biolink:SequenceVariant`
    - id (allele ID)
    - name (allele symbol)
    - in_taxon (NCBI Taxon ID)
    - in_taxon_label
    - synonym

- `biolink:VariantToGeneAssociation`
    - id (UUID)
    - subject (allele ID)
    - predicate (`biolink:is_sequence_variant_of`)
    - original_predicate (variant type SO term)
    - object (gene ID)
    - primary_knowledge_source (source database)
    - aggregator_knowledge_source (`["infores:monarchinitiative", "infores:agrkb"]`)

## Post-Download Processing

The `postdownload` step extracts entity IDs for lookup files used by the phenotype and genotype transforms:
- `data/alliance_gene.tsv` - Gene IDs
- `data/alliance_allele.tsv` - Allele IDs
- `data/alliance_genotype.tsv` - Genotype IDs

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

## Citation

Harmonizing model organism data in the Alliance of Genome Resources. 2022. Alliance of Genome Resources Consortium. Genetics, Volume 220, Issue 4, April 2022. Published Online: 25 February 2022. doi: doi.org/10.1093/genetics/iyac022. PMID: 35380658; PMCID: PMC8982023.

## License

BSD-3-Clause
