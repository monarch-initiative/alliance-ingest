import pytest

from biolink_model.datamodel.pydanticmodel_v2 import Gene, GeneToPhenotypicFeatureAssociation, PhenotypicFeature
from koza import KozaTransform
from koza.io.writer.passthrough_writer import PassthroughWriter

from src.alliance_ingest.phenotype import transform_record
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
