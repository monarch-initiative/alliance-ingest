"""Tests for the uphenotizer binding key and the lookup mapping built from source_map.tsv."""

from pathlib import Path

import pytest
from koza import KozaTransform
from koza.io.writer.passthrough_writer import PassthroughWriter

from alliance_ingest.phenotype_binding import (
    binding_key,
    chemicals,
    fbcv_namespaces,
    ordered_terms,
    resolve_binding,
)
from alliance_ingest.uphenotizer_phenotype_lookup import load_fbcv_namespaces
from alliance_ingest.uphenotizer_phenotype_lookup import transform_record as lookup_transform_record

FBCV_MINI = Path(__file__).parent / "fixtures" / "fbcv_mini.obo"


def test_ordered_terms_follow_term_order():
    record = {
        "phenotypeTermIdentifiers": [
            {"termId": "APO:0000087", "termOrder": 2},
            {"termId": "APO:0000003", "termOrder": 1},
        ]
    }
    assert ordered_terms(record) == ["APO:0000003", "APO:0000087"]


def test_ordered_terms_empty():
    assert ordered_terms({"phenotypeTermIdentifiers": []}) == []
    assert ordered_terms({}) == []


def test_chemicals_prefers_chebi_and_keeps_unmapped_statement():
    record = {
        "conditionRelations": [
            {
                "conditions": [
                    {
                        "conditionClassId": "ZECO:0000111",
                        "conditionStatement": "chemical:tunicamycin",
                        "chemicalOntologyId": "CHEBI:29699",
                    },
                    {"conditionClassId": "ZECO:0000111", "conditionStatement": "media:YPD"},
                    {"conditionClassId": "ZECO:0000160", "conditionStatement": "heat sensitive"},
                    {
                        "conditionClassId": "ZECO:0000111",
                        "conditionStatement": "chemical:tunicamycin",
                        "chemicalOntologyId": "CHEBI:29699",
                    },
                ]
            }
        ]
    }
    assert chemicals(record) == ["CHEBI:29699", "unmapped:media:YPD"]


def test_binding_key_matches_source_map_shape():
    # Same layout as source_map.tsv: source, pipe-joined terms, chemical
    assert binding_key("FB", ["FBbt:00004729"]) == "FB|FBbt:00004729|"
    assert binding_key("FB", ["FBcv:0000351", "FBcv:0000298"]) == "FB|FBcv:0000351|FBcv:0000298|"
    sgd_key = binding_key("SGD", ["APO:0000003", "APO:0000087"], "CHEBI:25255")
    assert sgd_key == "SGD|APO:0000003|APO:0000087|CHEBI:25255"
    assert binding_key("FB", []) == "FB||"


@pytest.fixture
def namespaces():
    return fbcv_namespaces(FBCV_MINI)


def test_fbcv_namespaces_reads_terms_only(namespaces):
    assert namespaces["FBcv:0000298"] == "dominance_qualifier"
    assert namespaces["FBcv:0000351"] == "phenotypic_class"
    assert "part_of" not in namespaces


def test_resolve_routed(namespaces):
    assert resolve_binding("routed", ["FBbt:00004729"], "PHENOTYPE:1001742", namespaces) == (
        "routed",
        "PHENOTYPE:1001742",
    )


def test_resolve_covered_upstream_with_context_trailers_uses_head_term(namespaces):
    assert resolve_binding("covered_upstream", ["FBcv:0000351"], "", namespaces) == ("covered_upstream", "FBcv:0000351")
    # dominance qualifier, clone qualifier and FBdv stage are droppable context
    terms = ["FBcv:0000351", "FBcv:0000298", "FBcv:0000700", "FBdv:00007001"]
    assert resolve_binding("covered_upstream", terms, "", namespaces) == ("covered_upstream", "FBcv:0000351")


@pytest.mark.parametrize(
    "trailer",
    [
        "GO:0048477",  # a process: "decreased cell number | oogenesis"
        "FBcv:0000325",  # a second phenotypic class
        "FBcv:0000340",  # extent: partially
        "FBcv:0000065",  # spatial: posterior
        "FBcv:9999999",  # unknown to FBcv: fail safe
        "SO:0000730",
    ],
)
def test_resolve_covered_upstream_with_phenotype_changing_trailer_has_no_edge(namespaces, trailer):
    assert resolve_binding("covered_upstream", ["FBcv:0000351", trailer], "", namespaces) == (
        "covered_upstream_unhandled_qualifiers",
        "",
    )


def test_resolve_other_statuses_have_no_edge(namespaces):
    assert resolve_binding("unrouted", ["APO:0000003", "APO:0000110"], "", namespaces) == ("unrouted", "")
    assert resolve_binding("skipped", [], "", namespaces) == ("skipped", "")
    assert resolve_binding("covered_upstream", [], "", namespaces) == ("covered_upstream", "")


def _source_map_row(**overrides):
    row = {
        "source": "FB",
        "source_terms": "",
        "chemical": "",
        "annotations": "1",
        "example_statement": "",
        "status": "unrouted",
        "rule": "",
        "pattern": "",
        "key": "",
        "class_id": "",
        "upheno_id": "",
        "reason": "",
    }
    row.update(overrides)
    return row


def _run_lookup(*rows):
    koza_transform = KozaTransform(mappings={}, writer=PassthroughWriter(), extra_fields={"fbcv_obo": str(FBCV_MINI)})
    load_fbcv_namespaces(koza_transform)
    for row in rows:
        lookup_transform_record(koza_transform, row)
    return {r["key"]: r for r in koza_transform.writer.result()}


def test_lookup_mapping_rows():
    lookup = _run_lookup(
        _source_map_row(source_terms="FBbt:00004729", status="routed", class_id="PHENOTYPE:1001742"),
        _source_map_row(source_terms="FBcv:0000351|FBcv:0000298", status="covered_upstream"),
        _source_map_row(source_terms="FBcv:0000351|GO:0048477", status="covered_upstream"),
        _source_map_row(
            source="SGD",
            source_terms="APO:0000003|APO:0000087",
            chemical="CHEBI:25255",
            status="routed",
            class_id="PHENOTYPE:2000571",
        ),
        _source_map_row(
            source="SGD", source_terms="APO:0000003|APO:0000110", chemical="unmapped:media:YPD", status="unrouted"
        ),
        _source_map_row(status="skipped"),
    )
    assert lookup["FB|FBbt:00004729|"] == {
        "key": "FB|FBbt:00004729|",
        "status": "routed",
        "phenotype_id": "PHENOTYPE:1001742",
    }
    assert lookup["FB|FBcv:0000351|FBcv:0000298|"]["phenotype_id"] == "FBcv:0000351"
    assert lookup["FB|FBcv:0000351|GO:0048477|"] == {
        "key": "FB|FBcv:0000351|GO:0048477|",
        "status": "covered_upstream_unhandled_qualifiers",
        "phenotype_id": "",
    }
    assert lookup["SGD|APO:0000003|APO:0000087|CHEBI:25255"]["phenotype_id"] == "PHENOTYPE:2000571"
    assert lookup["SGD|APO:0000003|APO:0000110|unmapped:media:YPD"] == {
        "key": "SGD|APO:0000003|APO:0000110|unmapped:media:YPD",
        "status": "unrouted",
        "phenotype_id": "",
    }
    assert lookup["FB||"]["status"] == "skipped"
