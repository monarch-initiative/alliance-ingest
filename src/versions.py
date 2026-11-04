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

A second top-level entry records the uphenotizer binding table
(output/source_map.tsv) that the phenotype transform uses to resolve FlyBase
and SGD post-composed phenotypes to PHENOTYPE: classes. It is tracked from the
HEAD of the uphenotizer main branch, which is also what phenio imports.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import requests

from kozahub_metadata_schema import now_iso, urls_from_download_yaml, version_from_github_branch


INGEST_DIR = Path(__file__).resolve().parents[1]
DOWNLOAD_YAML = INGEST_DIR / "download.yaml"

FMS_BASE = "https://fms.alliancegenome.org/api"
FMS_DOWNLOAD = "https://fms.alliancegenome.org/download/"

UPHENOTIZER_REPO = "monarch-initiative/uphenotizer"
UPHENOTIZER_RAW = f"https://raw.githubusercontent.com/{UPHENOTIZER_REPO}/"

FBCV_OBO_URL = "http://purl.obolibrary.org/obo/fbcv.obo"
FBCV_OBO_PATH = INGEST_DIR / "data" / "fbcv.obo"

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


def _uphenotizer_source(urls: list[str], now: str) -> dict[str, Any]:
    """The uphenotizer binding table: FlyBase/SGD annotation shape -> PHENOTYPE: class."""
    version, method = version_from_github_branch(UPHENOTIZER_REPO)
    return {
        "id": f"https://github.com/{UPHENOTIZER_REPO}",
        "name": "uphenotizer (DPO-ext / APO-ext binding table)",
        "urls": urls,
        "version": version,
        "version_method": method,
        "retrieved_at": now,
    }


def _fbcv_version() -> tuple[str, str]:
    """FBcv release from the OBO header's data-version line (e.g. fbcv/releases/2026-11-02)."""
    try:
        with open(FBCV_OBO_PATH, encoding="utf-8") as f:
            for line in f:
                if line.startswith("[Term]"):
                    break
                if line.startswith("data-version:"):
                    return line.split(":", 1)[1].strip().rsplit("/", 1)[-1], "obo_data_version"
    except OSError:
        pass
    return "unknown", "unavailable"


def _fbcv_source(now: str) -> dict[str, Any]:
    """FBcv, used to classify trailing terms of covered_upstream FlyBase annotations."""
    version, method = _fbcv_version()
    return {
        "id": "http://purl.obolibrary.org/obo/fbcv.owl",
        "name": "FlyBase Controlled Vocabulary (FBcv)",
        "urls": [FBCV_OBO_URL],
        "version": version,
        "version_method": method,
        "retrieved_at": now,
    }


def get_source_versions() -> list[dict[str, Any]]:
    release, method = _alliance_release()
    all_urls = urls_from_download_yaml(DOWNLOAD_YAML)
    alliance_urls = [u for u in all_urls if u.startswith(FMS_DOWNLOAD)]
    uphenotizer_urls = [u for u in all_urls if u.startswith(UPHENOTIZER_RAW)]
    now = now_iso()

    entry: dict[str, Any] = {
        "id": "infores:agr",
        "name": "Alliance of Genome Resources",
        "urls": alliance_urls,
        "version": release,
        "version_method": method,
        "retrieved_at": now,
    }
    if release != "unknown":
        nested = _per_mod_sources(release, alliance_urls, now)
        if nested:
            entry["sources"] = nested

    sources = [entry]
    if uphenotizer_urls:
        sources.append(_uphenotizer_source(uphenotizer_urls, now))
    if FBCV_OBO_URL in all_urls:
        sources.append(_fbcv_source(now))
    return sources
