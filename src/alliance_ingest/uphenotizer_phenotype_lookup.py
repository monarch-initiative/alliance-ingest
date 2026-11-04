"""Build the FlyBase/SGD phenotype lookup from the uphenotizer binding table.

Each row of uphenotizer's ``output/source_map.tsv`` is one annotation shape.
It is re-keyed here with :func:`binding_key` so ``phenotype.py`` can look up an
Alliance record by the key it builds from the record's own terms and conditions.
FBcv namespaces (from the ``fbcv_obo`` path in the mapping config, relative to
this file) decide whether a ``covered_upstream`` row may use its head term.
"""

from pathlib import Path

import koza

from alliance_ingest.phenotype_binding import binding_key, fbcv_namespaces, resolve_binding


@koza.on_data_begin()
def load_fbcv_namespaces(koza_transform):
    obo_path = Path(__file__).resolve().parent / koza_transform.extra_fields["fbcv_obo"]
    koza_transform.state["fbcv_namespaces"] = fbcv_namespaces(obo_path)


@koza.transform_record()
def transform_record(koza_transform, row: dict):
    terms = row["source_terms"].split("|") if row["source_terms"] else []
    status, phenotype_id = resolve_binding(
        row["status"], terms, row["class_id"], koza_transform.state["fbcv_namespaces"]
    )
    koza_transform.write(
        {
            "key": binding_key(row["source"], terms, row["chemical"] or None),
            "status": status,
            "phenotype_id": phenotype_id,
        }
    )
