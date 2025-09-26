"""
Testing configuration and utilities for alliance-ingest.
Provides replacements for Koza 1.x testing utilities to work with Koza 2.0+.
"""
import tempfile
import json
import importlib.util
import sys
from pathlib import Path
from typing import List, Dict, Any, Union, Optional
import pytest


# Additional fixtures that might be needed by the tests
@pytest.fixture  
def taxon_label_map_cache():
    """Mock taxon label map cache."""
    return {
        "NCBITaxon:7955": "Danio rerio",
        "NCBITaxon:10090": "Mus musculus", 
        "NCBITaxon:6239": "Caenorhabditis elegans"
    }

