import koza
from biolink_model.datamodel.pydanticmodel_v2 import Gene

from alliance_ingest.constants import TAXON_LABELS

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

@koza.transform_record()
def transform_record(koza_transform, row):

    # curie prefix as source?
    gene_id = row["basicGeneticEntity"]["primaryId"]

    # Not sure if Alliance will stick with this prefix for Xenbase, but for now...
    gene_id = gene_id.replace("DRSC:XB:", "Xenbase:")

    source = source_map[gene_id.split(":")[0]]

    if "name" not in row.keys():
        row["name"] = row["symbol"]

    in_taxon = row["basicGeneticEntity"]["taxonId"]
    in_taxon_label = TAXON_LABELS.get(in_taxon)
    if in_taxon_label is None:
        raise ValueError(f"Can't find taxon name for: {in_taxon}")

    gene = Gene(
        id=gene_id,
        symbol=row["symbol"],
        name=row["symbol"],
        full_name=row["name"].replace("\r", ""),  # Replacement to remove stray carriage returns in XenBase files
        type=[row["soTermId"]],
        in_taxon=[in_taxon],
        in_taxon_label=in_taxon_label,
        provided_by=[source],
    )

    if row["basicGeneticEntity"]["crossReferences"]:
        gene.xref = [xref["id"] for xref in row["basicGeneticEntity"]["crossReferences"]]
    if "synonyms" in row["basicGeneticEntity"].keys():
        # more handling for errant carriage returns
        gene.synonym = [synonym.replace("\r", "") for synonym in row["basicGeneticEntity"]["synonyms"]]

    return [gene]
