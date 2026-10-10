"""Tests for the allele transform: the SequenceVariant node and the allele-to-gene edge."""

import re

import pytest
from biolink_model.datamodel.pydanticmodel_v2 import SequenceVariant, VariantToGeneAssociation
from koza import KozaTransform
from koza.io.writer.passthrough_writer import PassthroughWriter

from alliance_ingest.allele import transform_record

URN_UUID = re.compile(r"^urn:uuid:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


@pytest.fixture
def mgi_allele_row():
    return {
        "AlleleId": "MGI:7297220",
        "AlleleSymbol": "Tyr<em1Example>",
        "AlleleSynonyms": "Tyr-em1, Tyr em1",
        "Taxon": "NCBITaxon:10090",
        "SpeciesName": "Mus musculus",
        "AlleleAssociatedGeneId": "MGI:98880",
        "VariantsTypeId": "SO:0000159",
    }


@pytest.fixture
def mgi_allele(mgi_allele_row):
    koza_transform = KozaTransform(mappings={}, writer=PassthroughWriter(), extra_fields={})
    return transform_record(koza_transform, mgi_allele_row)


def test_allele_node(mgi_allele):
    allele = mgi_allele[0]
    assert isinstance(allele, SequenceVariant)
    assert allele.id == "MGI:7297220"
    assert allele.synonym == ["Tyr-em1", "Tyr em1"]


def test_allele_to_gene_edge(mgi_allele):
    assert len(mgi_allele) == 2
    edge = mgi_allele[1]
    assert isinstance(edge, VariantToGeneAssociation)
    assert edge.subject == "MGI:7297220"
    assert edge.predicate == "biolink:is_sequence_variant_of"
    assert edge.object == "MGI:98880"
    assert edge.primary_knowledge_source == "infores:mgi"
    # urn:uuid ids pass through RDF export as valid IRIs
    assert URN_UUID.match(edge.id)


def test_allele_without_gene_has_no_edge(mgi_allele_row):
    row = {**mgi_allele_row, "AlleleAssociatedGeneId": "-"}
    koza_transform = KozaTransform(mappings={}, writer=PassthroughWriter(), extra_fields={})
    entities = transform_record(koza_transform, row)
    assert len(entities) == 1
