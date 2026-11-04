import pytest
from biolink_model.datamodel.pydanticmodel_v2 import (
    Gene,
    GeneToPhenotypicFeatureAssociation,
    PhenotypicFeature,
    VariantToPhenotypicFeatureAssociation,
)
from koza import KozaTransform
from koza.io.writer.passthrough_writer import PassthroughWriter

from alliance_ingest.phenotype import transform_record

# mock_koza is now provided by conftest.py fixture


@pytest.fixture
def alliance_entity_lookup_cache():
    return {"RGD:61958": {"category": "biolink:Gene"}}


@pytest.fixture
def rat_row():
    return {
        "dateAssigned": "2006-10-25T18:06:17.000-05:00",
        "evidence": {
            "crossReference": {"id": "RGD:1357201", "pages": ["reference"]},
            "publicationId": "PMID:11549339",
        },
        "objectId": "RGD:61958",
        "phenotypeStatement": "cardiac hypertrophy",
        "phenotypeTermIdentifiers": [{"termId": "MP:0001625", "termOrder": 1}],
    }


@pytest.fixture
def rat(rat_row, alliance_entity_lookup_cache):
    koza_transform = KozaTransform(
        mappings={"alliance-entity-lookup": alliance_entity_lookup_cache},
        writer=PassthroughWriter(),
        extra_fields={}
    )
    return transform_record(koza_transform, rat_row)


def test_association_publication(rat):
    association = [association for association in rat if isinstance(association, GeneToPhenotypicFeatureAssociation)][0]
    assert association.publications[0] == "PMID:11549339"


@pytest.fixture
def conditions_row(rat_row):
    rat_row["conditionRelations"] = [
        {
            "conditionRelationType": "has_condition",
            "conditions": [
                {
                    "conditionClassId": "ZECO:0000111",
                    "conditionStatement": "chemical:glycogen",
                    "chemicalOntologyId": "CHEBI:28087",
                }
            ],
        }
    ]

    return rat_row


@pytest.fixture
def conditions_entities(conditions_row, alliance_entity_lookup_cache):
    koza_transform = KozaTransform(
        mappings={"alliance-entity-lookup": alliance_entity_lookup_cache},
        writer=PassthroughWriter(),
        extra_fields={}
    )
    return transform_record(koza_transform, conditions_row)


def test_conditions(conditions_entities):
    association = [
        association
        for association in conditions_entities
        if isinstance(association, GeneToPhenotypicFeatureAssociation)
    ][0]
    assert "ZECO:0000111" in association.qualifiers
    assert association.primary_knowledge_source == "infores:rgd"
    assert "infores:monarchinitiative" in association.aggregator_knowledge_source
    assert "infores:agrkb" in association.aggregator_knowledge_source


# TODO: can this test be shared across all g2p loads?
@pytest.mark.parametrize("cls", [Gene, PhenotypicFeature, GeneToPhenotypicFeatureAssociation])
def confirm_one_of_each_classes(cls, rat):
    class_entities = [entity for entity in rat if isinstance(entity, cls)]
    assert class_entities
    assert len(class_entities) == 1
    assert class_entities[0]


# ---- FlyBase / SGD: post-composed phenotypes resolved via the uphenotizer binding table ----


@pytest.fixture
def uphenotizer_lookup_cache():
    return {
        "FB|FBbt:00004729|": {"status": "routed", "phenotype_id": "PHENOTYPE:1001742"},
        "FB|FBcv:0000351|FBcv:0000298|": {"status": "covered_upstream", "phenotype_id": "FBcv:0000351"},
        "FB|GO:0016028|FBdv:00007001|": {"status": "unrouted", "phenotype_id": ""},
        "FB||": {"status": "skipped", "phenotype_id": ""},
        "SGD|APO:0000003|APO:0000087|": {"status": "routed", "phenotype_id": "PHENOTYPE:2000535"},
        "SGD|APO:0000003|APO:0000087|CHEBI:25255": {"status": "routed", "phenotype_id": "PHENOTYPE:2000571"},
        "SGD|APO:0000003|APO:0000087|CHEBI:44423": {"status": "routed", "phenotype_id": "PHENOTYPE:2001137"},
        "SGD|APO:0000113|": {"status": "skipped", "phenotype_id": ""},
    }


@pytest.fixture
def entity_lookup_cache():
    return {
        "FB:FBal0038206": {"category": "biolink:SequenceVariant"},
        "FB:FBgn0000014": {"category": "biolink:Gene"},
        "SGD:S000000890": {"category": "biolink:Gene"},
        "SGD:S000281279": {"category": "biolink:SequenceVariant"},
    }


@pytest.fixture
def bound_transform(entity_lookup_cache, uphenotizer_lookup_cache):
    return KozaTransform(
        mappings={
            "alliance-entity-lookup": entity_lookup_cache,
            "uphenotizer-phenotype-lookup": uphenotizer_lookup_cache,
        },
        writer=PassthroughWriter(),
        extra_fields={},
    )


def _fb_row(terms, object_id="FB:FBal0038206", conditions=None):
    row = {
        "dateAssigned": "2026-03-04T11:28:07-05:00",
        "evidence": {
            "crossReference": {"id": "FB:FBrf0076549", "pages": ["reference"]},
            "publicationId": "PMID:7828824",
        },
        "objectId": object_id,
        "phenotypeStatement": "wing",
        "phenotypeTermIdentifiers": [{"termId": t, "termOrder": i + 1} for i, t in enumerate(terms)],
    }
    if conditions is not None:
        row["conditionRelations"] = [{"conditionRelationType": "has_condition", "conditions": conditions}]
    return row


def _sgd_row(terms, object_id="SGD:S000000890", conditions=None):
    row = _fb_row(terms, object_id, conditions)
    row["evidence"] = {"publicationId": "PMID:21179023"}
    return row


def test_fb_routed_anatomy_phenotype(bound_transform):
    # Terms arrive out of termOrder to check they are sorted before keying
    row = _fb_row(["FBbt:00004729"])
    result = transform_record(bound_transform, row)
    assert len(result) == 1
    association = result[0]
    assert isinstance(association, VariantToPhenotypicFeatureAssociation)
    assert association.subject == "FB:FBal0038206"
    assert association.object == "PHENOTYPE:1001742"
    assert association.primary_knowledge_source == "infores:flybase"
    assert association.publications == ["PMID:7828824"]
    assert bound_transform.state["binding_status"] == {("FB", "routed"): 1}


def test_fb_covered_upstream_uses_head_dpo_term(bound_transform):
    row = _fb_row(["FBcv:0000351", "FBcv:0000298"], object_id="FB:FBgn0000014")
    row["phenotypeTermIdentifiers"].reverse()  # termOrder, not list order, decides the head term
    result = transform_record(bound_transform, row)
    assert len(result) == 1
    assert isinstance(result[0], GeneToPhenotypicFeatureAssociation)
    assert result[0].object == "FBcv:0000351"
    assert bound_transform.state["binding_status"] == {("FB", "covered_upstream"): 1}


def test_fb_unrouted_and_skipped_shapes_are_dropped_and_counted(bound_transform):
    assert transform_record(bound_transform, _fb_row(["GO:0016028", "FBdv:00007001"])) == []
    assert transform_record(bound_transform, _fb_row([])) == []
    assert bound_transform.state["binding_status"] == {("FB", "unrouted"): 1, ("FB", "skipped"): 1}


def test_fb_shape_missing_from_binding_table_is_dropped_and_counted(bound_transform):
    assert transform_record(bound_transform, _fb_row(["FBbt:99999999"])) == []
    assert bound_transform.state["binding_status"] == {("FB", "not_in_binding_table"): 1}


def test_fb_does_not_fall_back_to_single_term_logic(bound_transform):
    # A lone FBbt term absent from the table must not be emitted as-is
    assert transform_record(bound_transform, _fb_row(["FBbt:99999999"])) == []


def test_sgd_without_chemical_binds_to_fallback_class(bound_transform):
    result = transform_record(bound_transform, _sgd_row(["APO:0000003", "APO:0000087"]))
    assert [a.object for a in result] == ["PHENOTYPE:2000535"]
    assert isinstance(result[0], GeneToPhenotypicFeatureAssociation)
    assert result[0].primary_knowledge_source == "infores:sgd"
    assert result[0].qualifiers is None or result[0].qualifiers == []


def test_sgd_chemical_condition_binds_to_specific_class(bound_transform):
    conditions = [{"conditionClassId": "ZECO:0000111", "conditionStatement": "chemical:tunicamycin",
                   "chemicalOntologyId": "CHEBI:25255", "conditionQuantity": "0.6 uM"}]
    result = transform_record(bound_transform, _sgd_row(["APO:0000003", "APO:0000087"],
                                                        object_id="SGD:S000281279", conditions=conditions))
    assert len(result) == 1
    assert isinstance(result[0], VariantToPhenotypicFeatureAssociation)
    assert result[0].object == "PHENOTYPE:2000571"
    assert result[0].qualifiers == ["ZECO:0000111"]


def test_sgd_multiple_chemicals_yield_one_association_each(bound_transform):
    conditions = [
        {"conditionClassId": "ZECO:0000111", "conditionStatement": "chemical:a", "chemicalOntologyId": "CHEBI:25255"},
        {"conditionClassId": "ZECO:0000111", "conditionStatement": "chemical:b", "chemicalOntologyId": "CHEBI:44423"},
    ]
    result = transform_record(bound_transform, _sgd_row(["APO:0000003", "APO:0000087"], conditions=conditions))
    assert sorted(a.object for a in result) == ["PHENOTYPE:2000571", "PHENOTYPE:2001137"]
    assert all(a.qualifiers == ["ZECO:0000111", "ZECO:0000111"] for a in result)
    assert bound_transform.state["binding_status"] == {("SGD", "routed"): 2}


def test_sgd_unmapped_chemical_is_keyed_by_statement(bound_transform):
    conditions = [{"conditionClassId": "ZECO:0000111", "conditionStatement": "media:YPD"}]
    assert transform_record(bound_transform, _sgd_row(["APO:0000003", "APO:0000087"], conditions=conditions)) == []
    assert bound_transform.state["binding_status"] == {("SGD", "not_in_binding_table"): 1}


def test_sgd_skipped_qualifier_is_dropped(bound_transform):
    assert transform_record(bound_transform, _sgd_row(["APO:0000113"])) == []
    assert bound_transform.state["binding_status"] == {("SGD", "skipped"): 1}


def test_subject_missing_from_entity_lookup_is_dropped_before_binding(bound_transform):
    assert transform_record(bound_transform, _fb_row(["FBbt:00004729"], object_id="FB:FBal9999999")) == []
    assert bound_transform.state["missing_ids"] == {"FB": 1}
    assert "binding_status" not in bound_transform.state


def test_other_sources_still_use_single_term_directly(bound_transform, rat_row):
    bound_transform.mappings["alliance-entity-lookup"]["RGD:61958"] = {"category": "biolink:Gene"}
    result = transform_record(bound_transform, rat_row)
    assert [a.object for a in result] == ["MP:0001625"]
    assert "binding_status" not in bound_transform.state
