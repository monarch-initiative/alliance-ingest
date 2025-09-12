from typing import List
import uuid

import koza
from monarch_ingest.ingests.alliance.source_translation import source_map

from biolink_model.datamodel.pydanticmodel_v2 import (
    GeneToPhenotypicFeatureAssociation,
    KnowledgeLevelEnum,
    AgentTypeEnum,
)

from loguru import logger


@koza.transform_record()
def transform_record(koza_transform, row: dict) -> List[GeneToPhenotypicFeatureAssociation]:
    results = []
    
    if len(row["phenotypeTermIdentifiers"]) == 0:
        logger.debug("Phenotype ingest record has 0 phenotype terms: " + str(row))
        return results

    if len(row["phenotypeTermIdentifiers"]) > 1:
        logger.debug("Phenotype ingest record has >1 phenotype terms: " + str(row))
        return results

    # For now, we'll skip the gene_ids check since we don't have map access in the new pattern
    # TODO: Implement proper gene filtering if needed
    if len(row["phenotypeTermIdentifiers"]) == 1:

        gene_id = row["objectId"]

        phenotypic_feature_id = row["phenotypeTermIdentifiers"][0]["termId"]

        # Remove the extra WB: prefix if necessary
        phenotypic_feature_id = phenotypic_feature_id.replace("WB:WBPhenotype:", "WBPhenotype:")

        source = source_map[row["objectId"].split(':')[0]]

        association = GeneToPhenotypicFeatureAssociation(
            id="uuid:" + str(uuid.uuid1()),
            subject=gene_id,
            predicate="biolink:has_phenotype",
            object=phenotypic_feature_id,
            publications=[row["evidence"]["publicationId"]],
            aggregator_knowledge_source=["infores:monarchinitiative", "infores:agrkb"],
            primary_knowledge_source=source,
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

        results.append(association)
    
    return results
