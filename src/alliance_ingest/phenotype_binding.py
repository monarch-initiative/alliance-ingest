"""Bind FlyBase and SGD phenotype annotations to uphenotizer phenotype classes.

FlyBase and SGD annotate phenotypes post-composed: an ordered list of terms
(an FBbt anatomy or GO term plus FBcv qualifiers; an APO qualifier plus an APO
observable) and, for SGD, often a ChEBI chemical condition. There is no single
ontology term to use as the association object.

uphenotizer (https://github.com/monarch-initiative/uphenotizer) pre-composes a
class for each annotation shape and phenio imports them as the DPO-ext and
APO-ext components (CURIE prefix ``PHENOTYPE``). Its binding table,
``output/source_map.tsv``, maps every shape ``(source, source_terms, chemical)``
to the class it is bound to.

This module reproduces uphenotizer's key for an Alliance phenotype record so
the phenotype transform can look the record up in that table. The key logic
mirrors ``uphenotizer/src/uphenotizer/alliance.py`` and must stay in step with it.
"""

from __future__ import annotations

# Sources whose phenotypes are resolved through the uphenotizer binding table.
UPHENOTIZER_SOURCES = frozenset({"FB", "SGD"})

# Binding statuses in source_map.tsv (uphenotizer/src/uphenotizer/model.py).
ROUTED = "routed"  # bound to a pre-composed PHENOTYPE: class
COVERED_UPSTREAM = "covered_upstream"  # head term is already a DPO (FBcv) class
# Other statuses (unrouted, skipped, pending) have no phenotype class yet.

CHEMICAL_CONDITION = "ZECO:0000111"
UNMAPPED_CHEMICAL = "unmapped:"

KEY_SEPARATOR = "|"


def ordered_terms(record: dict) -> list[str]:
    """Phenotype term IDs of an Alliance record, in ``termOrder``."""
    ids = record.get("phenotypeTermIdentifiers") or []
    ids = sorted(ids, key=lambda t: t.get("termOrder", 0))
    return [t["termId"] for t in ids if t.get("termId")]


def chemicals(record: dict) -> list[str]:
    """ChEBI IDs of the record's chemical conditions, in order of appearance.

    A chemical condition without a ChEBI ID is kept as ``unmapped:<statement>``,
    exactly as uphenotizer keys it, so the record binds to the same row.
    """
    found: list[str] = []
    for relation in record.get("conditionRelations") or []:
        for condition in relation.get("conditions") or []:
            chem = condition.get("chemicalOntologyId")
            if not chem and condition.get("conditionClassId") == CHEMICAL_CONDITION:
                chem = UNMAPPED_CHEMICAL + condition.get("conditionStatement", "")
            if chem and chem not in found:
                found.append(chem)
    return found


def binding_key(source: str, terms: list[str], chemical: str | None = None) -> str:
    """Lookup key for one ``(source, ordered terms, chemical)`` binding.

    The same function builds the key on both sides: from a source_map.tsv row
    when the mapping is loaded, and from an Alliance record when it is looked up.
    Parts are stripped because koza's CSV reader strips fields, and some
    ``unmapped:`` chemical statements end in whitespace.
    """
    joined_terms = KEY_SEPARATOR.join(term.strip() for term in terms)
    return KEY_SEPARATOR.join([source.strip(), joined_terms, (chemical or "").strip()])


def bound_phenotype_id(status: str, terms: list[str], class_id: str) -> str:
    """The phenotype ID a binding resolves to, or ``""`` if it has none.

    ``routed`` rows resolve to their pre-composed class. ``covered_upstream``
    rows are FlyBase annotations whose head term is already a DPO class, so the
    head term itself is the phenotype; the remaining terms are non-phenotypic
    context (dominance, stage, clone type) that uphenotizer also drops.
    """
    if status == ROUTED:
        return class_id
    if status == COVERED_UPSTREAM and terms:
        return terms[0]
    return ""
