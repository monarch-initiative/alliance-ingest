import koza
from biolink_model.datamodel.pydanticmodel_v2 import Gene
from typing import List

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
def transform_record(koza_transform, row: dict) -> List[Gene]:
    # curie prefix as source?
    gene_id = row["basicGeneticEntity"]["primaryId"]

    # Not sure if Alliance will stick with this prefix for Xenbase, but for now...
    gene_id = gene_id.replace("DRSC:XB:", "Xenbase:")

    source = source_map[gene_id.split(":")[0]]

    if "name" not in row.keys():
        row["name"] = row["symbol"]

    in_taxon = row["basicGeneticEntity"]["taxonId"]
    
    # Try taxon label lookup first, fall back to hardcoded values
    try:
        in_taxon_label = koza_transform.lookup(in_taxon, "label", "taxon-labels")
    except Exception:
        if in_taxon == "NCBITaxon:10090":
            in_taxon_label = "Mus musculus"
        elif in_taxon == "NCBITaxon:7955":
            in_taxon_label = "Danio rerio"
        elif in_taxon == "NCBITaxon:10116":
            in_taxon_label = "Rattus norvegicus"
        elif in_taxon == "NCBITaxon:6239":
            in_taxon_label = "Caenorhabditis elegans"
        elif in_taxon == "NCBITaxon:7227":
            in_taxon_label = "Drosophila melanogaster"
        elif in_taxon == "NCBITaxon:8355":
            in_taxon_label = "Xenopus laevis"
        elif in_taxon == "NCBITaxon:8364":
            in_taxon_label = "Xenopus tropicalis"
        elif in_taxon == "NCBITaxon:4932":
            in_taxon_label = "Saccharomyces cerevisiae"
        elif in_taxon == "NCBITaxon:559292":
            in_taxon_label = "Saccharomyces cerevisiae S288C"
        else:
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
        # Note: curie_cleaner is not available in Koza 2.0, will need to handle this differently if needed
        gene.xref = [xref["id"] for xref in row["basicGeneticEntity"]["crossReferences"]]
    if "synonyms" in row["basicGeneticEntity"].keys():
        # more handling for errant carriage returns
        gene.synonym = [synonym.replace("\r", "") for synonym in row["basicGeneticEntity"]["synonyms"]]

    return [gene]
