"""Tests for the shared TAXON_LABELS constant."""

import re

import pytest

from src.alliance_ingest.constants import TAXON_LABELS

EXPECTED_TAXA = [
    "NCBITaxon:9606",
    "NCBITaxon:10090",
    "NCBITaxon:10116",
    "NCBITaxon:7955",
    "NCBITaxon:6239",
    "NCBITaxon:7227",
    "NCBITaxon:8355",
    "NCBITaxon:8364",
    "NCBITaxon:4932",
    "NCBITaxon:559292",
]


@pytest.mark.parametrize("taxon_id", EXPECTED_TAXA)
def test_expected_taxa_present(taxon_id):
    assert taxon_id in TAXON_LABELS


@pytest.mark.parametrize("taxon_id,label", list(TAXON_LABELS.items()))
def test_label_is_not_a_curie(taxon_id, label):
    assert not re.match(r"^\w+:\d+$", label), (
        f"TAXON_LABELS['{taxon_id}'] = '{label}' looks like a CURIE, not a species name"
    )
