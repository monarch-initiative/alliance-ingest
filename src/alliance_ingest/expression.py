import uuid
import koza
from biolink_model.datamodel.pydanticmodel_v2 import GeneToExpressionSiteAssociation, KnowledgeLevelEnum, AgentTypeEnum
from loguru import logger

# Inline source_map to avoid relative import issues in Koza 2.0
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

def get_data(data, key):
    """Extract data from nested dict using dot notation"""
    keys = key.split('.')
    value = data
    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            return None
    return value

@koza.transform_record()
def transform_record(koza_transform, row):
    try:
        gene_id = get_data(row, "geneId")

        # Not sure if Alliance will stick with this prefix for Xenbase, but for now...
        gene_id = gene_id.replace("DRSC:XB:", "Xenbase:")

        # TODO: Biolink Model provenance likely needs to be changed
        #       soon to something like "aggregator_knowledge_source"
        db = gene_id.split(":")[0]
        source = source_map[db]

        cellular_component_id = get_data(row, "whereExpressed.cellularComponentTermId")
        anatomical_entity_id = get_data(row, "whereExpressed.anatomicalStructureTermId")

        stage_term_id = get_data(row, "whenExpressed.stageTermId")
        # if not stage_term_id:
        # TODO: some databases (e.g. MGI) do not stageTermId's
        #       but may have an UBERON term that we can use
        # stage_term_id = get_data(row, "whenExpressed.stageUberonSlimTerm.uberonTerm")

        publication_ids = [get_data(row, "evidence.publicationId")]

        xref = get_data(row, "crossReference.id")
        if xref:
            publication_ids.append(xref)

        # Our current ingest policy is to first use a reported Anatomical structure term...
        associations = []
        if anatomical_entity_id:
            associations.append(
                GeneToExpressionSiteAssociation(
                    id="uuid:" + str(uuid.uuid1()),
                    subject=gene_id,
                    predicate="biolink:expressed_in",
                    object=anatomical_entity_id,
                    stage_qualifier=stage_term_id,
                    qualifiers=([get_data(row, "assay")] if get_data(row, "assay") else None),
                    publications=publication_ids,
                    aggregator_knowledge_source=["infores:monarchinitiative", "infores:agrkb"],
                    primary_knowledge_source=source,
                    knowledge_level=KnowledgeLevelEnum.knowledge_assertion,
                    agent_type=AgentTypeEnum.manual_agent,
                )
            )

        elif cellular_component_id:
            # ... and failing that, fall back to using a subcellular component
            # (but ignore otherwise ignore it, if reported alongside in the record)
            associations.append(
                GeneToExpressionSiteAssociation(
                    id="uuid:" + str(uuid.uuid1()),
                    subject=gene_id,
                    predicate="biolink:expressed_in",
                    object=cellular_component_id,
                    stage_qualifier=stage_term_id,
                    qualifiers=([get_data(row, "assay")] if get_data(row, "assay") else None),
                    publications=publication_ids,
                    aggregator_knowledge_source=["infores:monarchinitiative", "infores:agrkb"],
                    primary_knowledge_source=source,
                    knowledge_level=KnowledgeLevelEnum.knowledge_assertion,
                    agent_type=AgentTypeEnum.manual_agent,
                )
            )
        else:
            # Print a log error and skip the S-P-O ingest
            logger.error(
                f"Gene expression record: \n\t'{str(row)}'\n has no ontology terms specified for expression site?"
            )
            return []

        return associations

    except Exception as exc:
        logger.error(f"Alliance gene expression ingest parsing exception for data row:\n\t'{str(row)}'\n{str(exc)}")
        return []
