"""
Testing configuration and utilities for alliance-ingest.
Provides replacements for Koza 1.x testing utilities to work with Koza 2.0+.
"""
import pytest
from typing import List, Dict, Any, Union


def mock_koza_2x(
    source_name: str,
    data: Union[Dict[str, Any], List[Dict[str, Any]]],
    transform_script: str,
    **kwargs
) -> List[Any]:
    """
    Mock Koza transform for Koza 2.0+ testing.
    
    Replacement for the old koza.utils.testing_utils.mock_koza function.
    This is a simplified placeholder - for full functionality, you would need
    to implement proper Koza 2.0+ transform testing.
    
    Args:
        source_name: Name of the source
        data: Input data (single dict or list of dicts)  
        transform_script: Path to transform script
        **kwargs: Additional config options
    
    Returns:
        List of transformed objects
    """
    # For now, return an empty list as a placeholder
    # TODO: Implement proper Koza 2.0+ testing infrastructure
    print(f"Mock transform called for {source_name} with {len(data) if isinstance(data, list) else 1} rows")
    return []


@pytest.fixture
def mock_koza():
    """Provide mock_koza fixture for backward compatibility with old tests."""
    return mock_koza_2x


# Additional fixtures that might be needed by the tests
@pytest.fixture  
def taxon_label_map_cache():
    """Mock taxon label map cache."""
    return {
        "NCBITaxon:7955": "Danio rerio",
        "NCBITaxon:10090": "Mus musculus", 
        "NCBITaxon:6239": "Caenorhabditis elegans"
    }


@pytest.fixture
def global_table():
    """Mock global table."""
    return {}


@pytest.fixture
def source_name():
    """Default source name for tests."""
    return "test_source"


@pytest.fixture
def script():
    """Default script path for tests."""
    return "./src/test_transform.py"