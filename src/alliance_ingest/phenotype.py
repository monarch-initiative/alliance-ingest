import uuid
from typing import List

import koza
from biolink_model.datamodel.pydanticmodel_v2 import (
    AgentTypeEnum,
    GeneToPhenotypicFeatureAssociation,
    GenotypeToPhenotypicFeatureAssociation,
    KnowledgeLevelEnum,
    VariantToPhenotypicFeatureAssociation,
)
from loguru import logger

from alliance_ingest.phenotype_binding import UPHENOTIZER_SOURCES, binding_key, chemicals, ordered_terms

ENTITY_LOOKUP = "alliance-entity-lookup"
PHENOTYPE_LOOKUP = "uphenotizer-phenotype-lookup"
NOT_IN_BINDING_TABLE = "not_in_binding_table"

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


def _count(koza_transform, bucket: str, key) -> None:
    counts = koza_transform.state.setdefault(bucket, {})
    counts[key] = counts.get(key, 0) + 1


@koza.on_data_end()
def report_counts(koza_transform):
    """Report missing-ID and FlyBase/SGD binding counts at the end of processing."""
    missing = koza_transform.state.get("missing_ids")
    if missing:
        logger.warning("IDs not found in entity lookup:")
        for prefix, count in sorted(missing.items()):
            logger.warning(f"  {prefix}: {count} IDs")

    binding = koza_transform.state.get("binding_status")
    if binding:
        logger.info("FlyBase/SGD phenotype bindings (only routed and covered_upstream produce edges):")
        for (source, status), count in sorted(binding.items()):
            logger.info(f"  {source} {status}: {count}")


def direct_phenotype_ids(row: dict) -> List[str]:
    """Phenotype ID for a record that carries a single, pre-composed phenotype term."""
    terms = ordered_terms(row)
    if len(terms) == 0:
        logger.warning("Phenotype ingest record has 0 phenotype terms: " + str(row))
        return []
    if len(terms) > 1:
        logger.warning("Phenotype ingest record has >1 phenotype terms: " + str(row))
        return []
    # Remove the extra WB: prefix if necessary
    return [terms[0].replace("WB:WBPhenotype:", "WBPhenotype:")]


def bound_phenotype_ids(koza_transform, row: dict, source: str) -> List[str]:
    """Phenotype IDs for a FlyBase or SGD record, via the uphenotizer binding table.

    The record's ordered terms (and, for SGD, each chemical condition) are keyed
    the way uphenotizer keys them and looked up in the mapping built from
    source_map.tsv. An SGD record with several chemicals binds once per
    chemical; when several chemicals bind to the same class (rules whose filler
    is the GO observable ignore the chemical) the class is returned once.
    Records whose shape has no phenotype class yet (unrouted, skipped, or absent
    from the table) produce nothing and are counted for the end report.
    """
    terms = ordered_terms(row)
    record_chemicals = chemicals(row) if source == "SGD" else []
    phenotype_ids: List[str] = []
    for chemical in record_chemicals or [None]:
        key = binding_key(source, terms, chemical)
        status = koza_transform.lookup(key, "status", map_name=PHENOTYPE_LOOKUP)
        # A failed lookup returns the key itself (on_map_failure: warning)
        if status == key:
            status = NOT_IN_BINDING_TABLE
        _count(koza_transform, "binding_status", (source, status))
        phenotype_id = koza_transform.lookup(key, "phenotype_id", map_name=PHENOTYPE_LOOKUP)
        if phenotype_id and phenotype_id != key and phenotype_id not in phenotype_ids:
            phenotype_ids.append(phenotype_id)
    return phenotype_ids


@koza.transform_record()
def transform_record(koza_transform, row: dict) -> List:
    id = row["objectId"]
    source = id.split(":")[0]

    category = koza_transform.lookup(id, "category", map_name=ENTITY_LOOKUP)
    # If lookup failed, it returns the ID itself due to on_map_failure: warning
    if not category.startswith("biolink:"):
        _count(koza_transform, "missing_ids", source)
        return []

    if source in UPHENOTIZER_SOURCES:
        phenotype_ids = bound_phenotype_ids(koza_transform, row, source)
    else:
        phenotype_ids = direct_phenotype_ids(row)
    if not phenotype_ids:
        return []

    if category == "biolink:Gene":
        EdgeClass = GeneToPhenotypicFeatureAssociation
    elif category == "biolink:Genotype":
        EdgeClass = GenotypeToPhenotypicFeatureAssociation
    elif category == "biolink:SequenceVariant":
        EdgeClass = VariantToPhenotypicFeatureAssociation
    else:
        raise ValueError(f"Unknown category {category} for {id}")

    qualifiers: List[str] = []
    for conditionRelation in row.get("conditionRelations") or []:
        for condition in conditionRelation["conditions"]:
            if condition["conditionClassId"]:
                qualifiers.append(condition["conditionClassId"])

    associations = []
    for phenotype_id in phenotype_ids:
        association = EdgeClass(
            id="uuid:" + str(uuid.uuid1()),
            subject=id,
            predicate="biolink:has_phenotype",
            object=phenotype_id,
            publications=[row["evidence"]["publicationId"]],
            aggregator_knowledge_source=["infores:monarchinitiative", "infores:agrkb"],
            primary_knowledge_source=source_map[source],
            knowledge_level=KnowledgeLevelEnum.knowledge_assertion,
            agent_type=AgentTypeEnum.manual_agent,
        )
        if qualifiers:
            association.qualifiers = qualifiers
        associations.append(association)

    return associations
