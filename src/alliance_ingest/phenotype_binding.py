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

# Status this ingest assigns to a covered_upstream row whose trailing terms
# change the phenotype (see resolve_binding).
COVERED_UPSTREAM_UNHANDLED_QUALIFIERS = "covered_upstream_unhandled_qualifiers"

# FBcv namespaces that describe genetic or experimental context rather than the
# phenotype, and term prefixes that only give the stage of observation. Mirrors
# context_namespaces / drop_prefixes in uphenotizer/config/flybase.yaml.
CONTEXT_NAMESPACES = frozenset(
    {
        "dominance_qualifier",
        "clone_qualifier",
        "genotype_to_phenotype_relation",
        "sex_qualifier",
        "temporal_qualifier",
    }
)
DROP_PREFIXES = frozenset({"FBdv"})

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


def fbcv_namespaces(obo_path) -> dict[str, str]:
    """FBcv term ID -> OBO namespace, read from fbcv.obo."""
    namespaces: dict[str, str] = {}
    in_term = False
    current: str | None = None
    with open(obo_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("["):
                in_term = line == "[Term]"
                current = None
            elif in_term and line.startswith("id: "):
                current = line[4:]
            elif in_term and line.startswith("namespace: ") and current:
                namespaces[current] = line[len("namespace: ") :]
    return namespaces


def is_context_term(term: str, namespaces: dict[str, str]) -> bool:
    """True if a trailing FlyBase term is context that may be dropped (uphenotizer's rule)."""
    prefix = term.split(":", 1)[0]
    return prefix in DROP_PREFIXES or namespaces.get(term) in CONTEXT_NAMESPACES


def resolve_binding(status: str, terms: list[str], class_id: str, namespaces: dict[str, str]) -> tuple[str, str]:
    """Resolve a source_map.tsv row to ``(status, phenotype_id)``; an empty ID means no edge.

    ``routed`` rows resolve to their pre-composed class.

    ``covered_upstream`` rows are FlyBase annotations whose head term is already
    a DPO class, which uphenotizer leaves to DPO without emitting anything. The
    head term is used as the phenotype only when every trailing term is context
    that uphenotizer itself drops when routing (dominance, clone, sex, temporal,
    genotype-to-phenotype relation, or an FBdv stage). A trailing term that
    changes the phenotype (a GO process, a second phenotypic class, a spatial,
    intensity or extent qualifier) would make the head term lossy, so the row
    gets status ``covered_upstream_unhandled_qualifiers`` and no edge, matching
    uphenotizer's no-lossy-translation rule.
    """
    if status == ROUTED:
        return status, class_id
    if status == COVERED_UPSTREAM and terms:
        if all(is_context_term(term, namespaces) for term in terms[1:]):
            return status, terms[0]
        return COVERED_UPSTREAM_UNHANDLED_QUALIFIERS, ""
    return status, ""
