from biolink_model.datamodel.pydanticmodel_v2 import (
    GeneToDiseaseAssociation,
    GenotypeToDiseaseAssociation,
    VariantToDiseaseAssociation,
)
from koza.cli_utils import get_koza_app

#  TODO: look at row["source"] to update this map
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

koza_app = get_koza_app("alliance_disease_association")

while (row := koza_app.get_row()) is not None:
    subject_category = row["DBObjectType"]
    if subject_category == 'gene':
        AssociationClass = GeneToDiseaseAssociation
        predicate = "biolink:related_to"  # TODO: sort out accurate predicates for each kind of row
    elif subject_category == 'allele':
        AssociationClass = VariantToDiseaseAssociation
        predicate = "biolink:related_to"  # TODO: sort out accurate predicates for each kind of row
    elif subject_category == 'affected_genomic_model':
        AssociationClass = GenotypeToDiseaseAssociation
        predicate = "biolink:related_to"  # TODO: sort out accurate predicates for each kind of row
    else:
        # skip this row if there's an association with another kind of entity that we don't yet support, consider logging?
        koza_app.next_row()

    association = AssociationClass(
        subject=row["DBObjectID"],
        predicate="",  #
        object=row["DOID"],
        has_evidence=[row["EvidenceCode"]],
        # TODO: capture row["ExperimentalCondition"], probably as qualifier?
        # TODO: capture row["Reference"] as publications
        primary_knowledge_source=source_map[row["objectId"].split(':')[0]],
        aggregator_knowledge_source=["infores:monarchinitiative", "infores:agrkb"],
        # TODO: set KnowledgeLevelEnum and AgentType enum, it looks like there are inferred edges and that can show up in the KL/AT
        # knowledge_level=KnowledgeLevelEnum.knowledge_assertion,
        # agent_type=AgentTypeEnum.manual_agent
    )

    koza_app.write(association)
