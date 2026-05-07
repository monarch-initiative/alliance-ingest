"""Upstream source version fetcher for alliance-ingest.

Alliance ships ~25 download URLs under one logical release version, so the
top-level entry collapses them into a single SourceVersion whose `urls` list
is read from download.yaml at runtime (DRY with the downloader config).

Nested under that AGR entry, one SourceVersion per contributing MOD records
the per-MOD submission date as observed in the AGR FMS snapshot for the
current release. Edges in this ingest's output carry per-MOD
`primary_knowledge_source` (see src/alliance_ingest/phenotype.py::source_map),
so a downstream consumer (e.g. monarch-app) can resolve an edge's exact
upstream version even though everything was retrieved via AGR.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import requests

from kozahub_metadata_schema import now_iso, urls_from_download_yaml


INGEST_DIR = Path(__file__).resolve().parents[1]
DOWNLOAD_YAML = INGEST_DIR / "download.yaml"

FMS_BASE = "https://fms.alliancegenome.org/api"

# AGR dataSubType.name -> Biolink infores. Mirrors source_map in
# src/alliance_ingest/phenotype.py; XBXL+XBXT collapse to infores:xenbase.
MOD_INFORES = {
    "FB": ("infores:flybase", "FlyBase"),
    "MGI": ("infores:mgi", "Mouse Genome Informatics"),
    "RGD": ("infores:rgd", "Rat Genome Database"),
    "SGD": ("infores:sgd", "Saccharomyces Genome Database"),
    "WB": ("infores:wormbase", "WormBase"),
    "ZFIN": ("infores:zfin", "ZFIN"),
    "XBXL": ("infores:xenbase", "Xenbase"),
    "XBXT": ("infores:xenbase", "Xenbase"),
}


def _alliance_release() -> tuple[str, str]:
    try:
        r = requests.get(f"{FMS_BASE}/releaseversion/current", timeout=10)
        r.raise_for_status()
        return r.json()["releaseVersion"], "alliance_fms_api"
    except Exception:
        return "unknown", "unavailable"


def _alliance_snapshot(release: str) -> list[dict[str, Any]]:
    try:
        r = requests.get(f"{FMS_BASE}/snapshot/release/{release}", timeout=15)
        r.raise_for_status()
        return r.json().get("snapShot", {}).get("dataFiles", []) or []
    except Exception:
        return []


def _per_mod_sources(release: str, our_urls: list[str], now: str) -> list[dict[str, Any]]:
    """Build nested SourceVersion entries, one per MOD whose data we ingest.

    Filters the AGR snapshot to dataFiles whose stableURL we actually pulled
    (avoids declaring versions for MOD data we didn't consume), groups by
    MOD, takes the most recent uploadDate as the per-MOD version.
    """
    files = _alliance_snapshot(release)
    if not files:
        return []

    our_url_set = set(our_urls)
    by_mod: dict[str, dict[str, Any]] = {}
    for f in files:
        stable = f.get("stableURL")
        if stable not in our_url_set:
            continue
        sub = (f.get("dataSubType") or {}).get("name")
        if sub not in MOD_INFORES:
            continue
        upload = f.get("uploadDate")
        if not upload:
            continue
        bucket = by_mod.setdefault(sub, {"latest": upload, "urls": []})
        bucket["urls"].append(stable)
        if upload > bucket["latest"]:
            bucket["latest"] = upload

    # XBXL + XBXT collapse to one infores:xenbase entry — merge here.
    merged: dict[str, dict[str, Any]] = {}
    for sub, bucket in by_mod.items():
        infores, name = MOD_INFORES[sub]
        m = merged.setdefault(infores, {"name": name, "latest": bucket["latest"], "urls": []})
        m["urls"].extend(bucket["urls"])
        if bucket["latest"] > m["latest"]:
            m["latest"] = bucket["latest"]

    sources: list[dict[str, Any]] = []
    for infores, m in sorted(merged.items()):
        sources.append({
            "id": infores,
            "name": m["name"],
            "urls": sorted(set(m["urls"])),
            "version": m["latest"].split("T")[0],
            "version_method": "alliance_fms_submission",
            "retrieved_at": now,
        })
    return sources


def get_source_versions() -> list[dict[str, Any]]:
    release, method = _alliance_release()
    urls = urls_from_download_yaml(DOWNLOAD_YAML)
    now = now_iso()

    entry: dict[str, Any] = {
        "id": "infores:agr",
        "name": "Alliance of Genome Resources",
        "urls": urls,
        "version": release,
        "version_method": method,
        "retrieved_at": now,
    }
    if release != "unknown":
        nested = _per_mod_sources(release, urls, now)
        if nested:
            entry["sources"] = nested
    return [entry]
