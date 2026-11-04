"""Build the FlyBase/SGD phenotype lookup from the uphenotizer binding table.

Each row of uphenotizer's ``output/source_map.tsv`` is one annotation shape.
It is re-keyed here with :func:`binding_key` so ``phenotype.py`` can look up an
Alliance record by the key it builds from the record's own terms and conditions.
"""

import koza

from alliance_ingest.phenotype_binding import binding_key, bound_phenotype_id


@koza.transform_record()
def transform_record(koza_transform, row: dict):
    terms = row["source_terms"].split("|") if row["source_terms"] else []
    koza_transform.write(
        {
            "key": binding_key(row["source"], terms, row["chemical"] or None),
            "status": row["status"],
            "phenotype_id": bound_phenotype_id(row["status"], terms, row["class_id"]),
        }
    )
