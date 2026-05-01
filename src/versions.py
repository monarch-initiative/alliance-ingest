"""Upstream source version fetcher for alliance-ingest.

Alliance ships ~25 download URLs under one logical release version, so all
collapse into a single SourceVersion entry whose `urls` list is read from
download.yaml at runtime (DRY with the downloader config).
"""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any

import requests

from kozahub_metadata_schema.writer import urls_from_download_yaml


INGEST_DIR = Path(__file__).resolve().parents[1]
DOWNLOAD_YAML = INGEST_DIR / "download.yaml"


def _now_iso() -> str:
    return (
        datetime.datetime.now(datetime.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _alliance_version() -> tuple[str, str]:
    try:
        r = requests.get(
            "https://fms.alliancegenome.org/api/releaseversion/current",
            timeout=10,
        )
        r.raise_for_status()
        return r.json()["releaseVersion"], "alliance_fms_api"
    except Exception:
        return "unknown", "unavailable"


def get_source_versions() -> list[dict[str, Any]]:
    ver, method = _alliance_version()
    return [
        {
            "id": "infores:agr",
            "name": "Alliance of Genome Resources",
            "urls": urls_from_download_yaml(DOWNLOAD_YAML),
            "version": ver,
            "version_method": method,
            "retrieved_at": _now_iso(),
        }
    ]
