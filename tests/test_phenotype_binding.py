"""Tests for the uphenotizer binding key and the lookup mapping built from source_map.tsv."""

from koza import KozaTransform
from koza.io.writer.passthrough_writer import PassthroughWriter

from alliance_ingest.phenotype_binding import binding_key, bound_phenotype_id, chemicals, ordered_terms
from alliance_ingest.uphenotizer_phenotype_lookup import transform_record as lookup_transform_record


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


def test_bound_phenotype_id_by_status():
    assert bound_phenotype_id("routed", ["FBbt:00004729"], "PHENOTYPE:1001742") == "PHENOTYPE:1001742"
    assert bound_phenotype_id("covered_upstream", ["FBcv:0000351", "FBcv:0000298"], "") == "FBcv:0000351"
    assert bound_phenotype_id("unrouted", ["APO:0000003", "APO:0000110"], "") == ""
    assert bound_phenotype_id("skipped", [], "") == ""


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
    koza_transform = KozaTransform(mappings={}, writer=PassthroughWriter(), extra_fields={})
    for row in rows:
        lookup_transform_record(koza_transform, row)
    return {r["key"]: r for r in koza_transform.writer.result()}


def test_lookup_mapping_rows():
    lookup = _run_lookup(
        _source_map_row(source_terms="FBbt:00004729", status="routed", class_id="PHENOTYPE:1001742"),
        _source_map_row(source_terms="FBcv:0000351|FBcv:0000298", status="covered_upstream"),
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
    assert lookup["SGD|APO:0000003|APO:0000087|CHEBI:25255"]["phenotype_id"] == "PHENOTYPE:2000571"
    assert lookup["SGD|APO:0000003|APO:0000110|unmapped:media:YPD"] == {
        "key": "SGD|APO:0000003|APO:0000110|unmapped:media:YPD",
        "status": "unrouted",
        "phenotype_id": "",
    }
    assert lookup["FB||"]["status"] == "skipped"
