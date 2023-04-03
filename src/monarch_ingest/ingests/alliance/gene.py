from koza.cli_runner import get_koza_app
from source_translation import source_map

from biolink.pydanticmodel import Gene

koza_app = get_koza_app("alliance_gene")

while (row := koza_app.get_row()) is not None:

    # curie prefix as source?
    gene_id = row["basicGeneticEntity"]["primaryId"]

    # Not sure if Alliance will stick with this prefix for Xenbase, but for now...
    gene_id = gene_id.replace("DRSC:XB:", "Xenbase:")

    source = source_map[gene_id.split(":")[0]]

    if "name" not in row.keys():
        row["name"] = row["symbol"]

    gene = Gene(
        id=gene_id,
        symbol=row["symbol"],
        name=row["name"],
        type=row["soTermId"],
        in_taxon=[row["basicGeneticEntity"]["taxonId"]],
        provided_by=[source]
    )

    if row["basicGeneticEntity"]["crossReferences"]:
        gene.xref = [
            koza_app.curie_cleaner.clean(xref["id"])
            for xref in row["basicGeneticEntity"]["crossReferences"]
        ]
    if "synonyms" in row["basicGeneticEntity"].keys():
        gene.synonym = row["basicGeneticEntity"]["synonyms"]

    koza_app.write(gene)
