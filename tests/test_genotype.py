"""
An example test file for the transform script.

It uses pytest fixtures to define the input data and the mock koza transform.
The test_example function then tests the output of the transform script.

See the Koza documentation for more information on testing transforms:
https://koza.monarchinitiative.org/Usage/testing/
"""

from koza import KozaTransform
import pytest

from src.alliance_ingest.genotype import transform_record
from koza.io.writer.passthrough_writer import PassthroughWriter
from biolink_model.datamodel.pydanticmodel_v2 import Genotype, GenotypeToGeneAssociation, GenotypeToVariantAssociation


@pytest.fixture
def map_cache():
    return {
        "ZFIN:ZDB-ALT-060821-6": {
            "AlleleId": "ZFIN:ZDB-ALT-060821-6",
            "AlleleAssociatedGeneId": "ZFIN:ZDB-GENE-000508-1",
        },
        "ZFIN:ZDB-ALT-100701-1": {
            "AlleleId": "ZFIN:ZDB-ALT-100701-1",
            "AlleleAssociatedGeneId": "ZFIN:ZDB-GENE-990415-72",
        },
        "MGI:5569116": {
            "AlleleId": "MGI:5569116",
            "AlleleAssociatedGeneId": "MGI:98880",
        },
    }


# Define the mock koza transform on an example row
@pytest.fixture
def mgi_agm_row():
    return {
        'primaryID': 'MGI:3626201',
        'subtype': 'genotype',
        'name': 'Ep300<sup>tm3Pkb</sup>/Ep300<sup>+</sup> Tg(IghMyc)22Bri/0  [background:] involves: 129S6/SvEvTac * C57BL * SJL',
        'taxonId': 'NCBITaxon:10090',
        'crossReference': {'id': 'MGI:3626201', 'pages': ['genotype']},
        'affectedGenomicModelComponents': [
            {'alleleID': 'MGI:3612049', 'zygosity': 'GENO:0000135'},
            {'alleleID': 'MGI:2447604', 'zygosity': 'GENO:0000606'},
        ],
    }

@pytest.fixture
def mgi_agm(mgi_agm_row, map_cache):
    koza_transform = KozaTransform(
        mappings={"allele_to_gene": map_cache},
        writer=PassthroughWriter(),
        extra_fields={}
    )
    return transform_record(koza_transform, mgi_agm_row)


def test_mgi_agm(mgi_agm):
    entities = mgi_agm
    genotypes = [entity for entity in entities if isinstance(entity, Genotype)]
    genotype = genotypes[0]
    assert genotype.id == 'MGI:3626201'
    assert (
        genotype.name
        == 'Ep300<sup>tm3Pkb</sup>/Ep300<sup>+</sup> Tg(IghMyc)22Bri/0  [background:] involves: 129S6/SvEvTac * C57BL * SJL'
    )
    assert genotype.in_taxon == ['NCBITaxon:10090']
    assert genotype.in_taxon_label == 'Mus musculus'

@pytest.fixture
def zfin_agm_row():
    return {
        'primaryID': 'ZFIN:ZDB-FISH-150901-9455',
        'name': 'acvr1l<sup>sk42/sk42</sup>; f2Tg',
        'affectedGenomicModelComponents': [
            {'alleleID': 'ZFIN:ZDB-ALT-060821-6', 'zygosity': 'GENO:0000137'},
            {'alleleID': 'ZFIN:ZDB-ALT-100701-1', 'zygosity': 'GENO:0000136'},
        ],
        'crossReference': {'id': 'ZFIN:ZDB-FISH-150901-9455', 'pages': ['Fish']},
        'taxonId': 'NCBITaxon:7955',
    }

@pytest.fixture
def zfin_agm(zfin_agm_row, map_cache):
    koza_transform = KozaTransform(
        mappings={"allele_to_gene": map_cache},
        writer=PassthroughWriter(),
        extra_fields={}
    )
    return transform_record(koza_transform, zfin_agm_row)

def test_zfin_agm(zfin_agm):
    entities = zfin_agm
    genotypes = [entity for entity in entities if isinstance(entity, Genotype)]
    assert len(genotypes) == 1
    genotype = genotypes[0]
    assert genotype.id == 'ZFIN:ZDB-FISH-150901-9455'
    assert genotype.name == 'acvr1l<sup>sk42/sk42</sup>; f2Tg'
    assert genotype.in_taxon == ['NCBITaxon:7955']
    assert genotype.in_taxon_label == 'Danio rerio'

def test_zfin_transform_associations(zfin_agm):
    entities = zfin_agm
    gene_to_variant_associations = [entity for entity in entities if isinstance(entity, GenotypeToVariantAssociation)]

    assert len(gene_to_variant_associations) == 2

    # Check first association
    assert gene_to_variant_associations[0].subject == 'ZFIN:ZDB-FISH-150901-9455'
    assert gene_to_variant_associations[0].predicate == 'biolink:has_sequence_variant'
    assert gene_to_variant_associations[0].object == 'ZFIN:ZDB-ALT-060821-6'
    assert gene_to_variant_associations[0].qualifier == 'GENO:0000137'
    assert gene_to_variant_associations[0].primary_knowledge_source == 'infores:zfin'
    assert set(gene_to_variant_associations[0].aggregator_knowledge_source) == {
        'infores:monarchinitiative',
        'infores:agrkb',
    }

    # Check second association
    assert gene_to_variant_associations[1].subject == 'ZFIN:ZDB-FISH-150901-9455'
    assert gene_to_variant_associations[1].predicate == 'biolink:has_sequence_variant'
    assert gene_to_variant_associations[1].object == 'ZFIN:ZDB-ALT-100701-1'
    assert gene_to_variant_associations[1].qualifier == 'GENO:0000136'
    assert gene_to_variant_associations[1].primary_knowledge_source == 'infores:zfin'
    assert set(gene_to_variant_associations[1].aggregator_knowledge_source) == {
        'infores:monarchinitiative',
        'infores:agrkb',
    }

    genotype_to_gene_associations = [entity for entity in entities if isinstance(entity, GenotypeToGeneAssociation)]
    assert len(genotype_to_gene_associations) == 2

    # check first gene to genotype
    assert genotype_to_gene_associations[0].subject == 'ZFIN:ZDB-FISH-150901-9455'
    assert genotype_to_gene_associations[0].predicate == 'biolink:related_to'
    assert genotype_to_gene_associations[0].object == 'ZFIN:ZDB-GENE-000508-1'
    assert genotype_to_gene_associations[0].primary_knowledge_source == 'infores:zfin'
    assert set(genotype_to_gene_associations[0].aggregator_knowledge_source) == {
        'infores:monarchinitiative',
        'infores:agrkb',
    }

    # check second gene to genotype
    assert genotype_to_gene_associations[1].subject == 'ZFIN:ZDB-FISH-150901-9455'
    assert genotype_to_gene_associations[1].predicate == 'biolink:related_to'
    assert genotype_to_gene_associations[1].object == 'ZFIN:ZDB-GENE-990415-72'
    assert genotype_to_gene_associations[1].primary_knowledge_source == 'infores:zfin'
    assert set(genotype_to_gene_associations[1].aggregator_knowledge_source) == {
        'infores:monarchinitiative',
        'infores:agrkb',
    }

def test_mgi_transform_associations(mgi_agm):
    entities = mgi_agm
    associations = [entity for entity in entities if isinstance(entity, GenotypeToVariantAssociation)]
    assert len(associations) == 2

    # Check first association
    assert associations[0].subject == 'MGI:3626201'
    assert associations[0].predicate == 'biolink:has_sequence_variant'
    assert associations[0].object == 'MGI:3612049'
    assert associations[0].qualifier == 'GENO:0000135'
    assert associations[0].primary_knowledge_source == 'infores:mgi'
    assert set(associations[0].aggregator_knowledge_source) == {'infores:monarchinitiative', 'infores:agrkb'}

    # Check second association
    assert associations[1].subject == 'MGI:3626201'
    assert associations[1].predicate == 'biolink:has_sequence_variant'
    assert associations[1].object == 'MGI:2447604'
    assert associations[1].qualifier == 'GENO:0000606'
    assert associations[1].primary_knowledge_source == 'infores:mgi'
    assert set(associations[1].aggregator_knowledge_source) == {'infores:monarchinitiative', 'infores:agrkb'}
