import uuid
from typing import List

# from source_translation import source_map
from biolink_model.datamodel.pydanticmodel_v2 import (
    AgentTypeEnum,
    GeneToPhenotypicFeatureAssociation,
    GenotypeToPhenotypicFeatureAssociation,
    KnowledgeLevelEnum,
    VariantToPhenotypicFeatureAssociation,
)
import koza
from loguru import logger

source_map = {
    "FB": "infores:flybase",
    "MGI": "infores:mgi",
    "RGD": "infores:rgd",
    "HGNC": "infores:rgd",  # Alliance contains RGD curation of human genes
    "SGD": "infores:sgd",
    "WB": "infores:wormbase",
    "Xenbase": "infores:xenbase",
    "ZFIN": "infores:zfin",
}


@koza.on_data_end()
def report_missing_ids(koza_transform):
    """Report missing ID counts at the end of processing."""
    if "missing_ids" in koza_transform.state and koza_transform.state["missing_ids"]:
        logger.warning("IDs not found in entity lookup:")
        for prefix, count in sorted(koza_transform.state["missing_ids"].items()):
            logger.warning(f"  {prefix}: {count} IDs")


@koza.transform_record()
def transform_record(koza_transform, row: dict) -> List:
    if len(row["phenotypeTermIdentifiers"]) == 0:
        logger.warning("Phenotype ingest record has 0 phenotype terms: " + str(row))
        return []
    if len(row["phenotypeTermIdentifiers"]) > 1:
        logger.warning("Phenotype ingest record has >1 phenotype terms: " + str(row))
        return []

    id = row["objectId"]
    category = koza_transform.lookup(id, "category")

    # If lookup failed, it returns the ID itself due to on_map_failure: warning
    # Check if we got a valid biolink category
    if not category.startswith("biolink:"):
        # Track missing IDs by prefix
        prefix = id.split(":")[0]
        if "missing_ids" not in koza_transform.state:
            koza_transform.state["missing_ids"] = {}
        if prefix not in koza_transform.state["missing_ids"]:
            koza_transform.state["missing_ids"][prefix] = 0
        koza_transform.state["missing_ids"][prefix] += 1
        return []

    phenotypic_feature_id = row["phenotypeTermIdentifiers"][0]["termId"]
    # Remove the extra WB: prefix if necessary
    phenotypic_feature_id = phenotypic_feature_id.replace("WB:WBPhenotype:", "WBPhenotype:")
    prefix = id.split(":")[0]
    if category == 'biolink:Gene':
        EdgeClass = GeneToPhenotypicFeatureAssociation
    elif category == 'biolink:Genotype':
        EdgeClass = GenotypeToPhenotypicFeatureAssociation
    elif category == 'biolink:SequenceVariant':
        EdgeClass = VariantToPhenotypicFeatureAssociation
    else:
        raise ValueError(f"Unknown category {category} for {id}")

    association = EdgeClass(
        id="uuid:" + str(uuid.uuid1()),
        subject=id,
        predicate="biolink:has_phenotype",
        object=phenotypic_feature_id,
        publications=[row["evidence"]["publicationId"]],
        aggregator_knowledge_source=["infores:monarchinitiative", "infores:agrkb"],
        primary_knowledge_source=source_map[row["objectId"].split(':')[0]],
        knowledge_level=KnowledgeLevelEnum.knowledge_assertion,
        agent_type=AgentTypeEnum.manual_agent,
    )

    if "conditionRelations" in row.keys() and row["conditionRelations"] is not None:
        qualifiers: List[str] = []
        for conditionRelation in row["conditionRelations"]:
            for condition in conditionRelation["conditions"]:
                if condition["conditionClassId"]:
                    qualifier_term = condition["conditionClassId"]
                    qualifiers.append(qualifier_term)
        association.qualifiers = qualifiers

    return [association]
