"""Tests for optopsy/ui/_compat.py — optional dependency import helper."""

import pytest

from optopsy.ui._compat import import_optional_dependency


def test_import_existing_module():
    """Importing a stdlib module should return the module object."""
    mod = import_optional_dependency("json")
    assert hasattr(mod, "dumps")
    assert mod.__name__ == "json"


def test_import_missing_module():
    """Importing a nonexistent module should raise ImportError with install hint."""
    with pytest.raises(ImportError, match=r"pip install optopsy\[ui\]"):
        import_optional_dependency("nonexistent_module_xyz_12345")
