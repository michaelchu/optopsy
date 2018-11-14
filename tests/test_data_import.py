import os

import optopsy as op
from .support.struct_fixtures import *


@pytest.fixture
def mock_daily_dir():
    return os.path.join(os.path.dirname(__file__), "test_data_dir")


@pytest.fixture
def mock_daily_file():
    return os.path.join(
        os.path.dirname(__file__), "test_data_dir", "test_cboe_20160104.csv"
    )


@pytest.fixture
def mock_file_dir():
    return os.path.abspath(__file__)


def test_invalid_fields(mock_file_dir, invalid_fields):
    with pytest.raises(ValueError):
        op.get(mock_file_dir, struct=invalid_fields)


def test_valid_fields(mock_daily_file, cboe_struct):
    try:
        op.get(mock_daily_file, struct=cboe_struct, prompt=False)
    except ValueError:
        pytest.fail("ValueError raised")


def test_invalid_idx(mock_file_dir, invalid_idx):
    with pytest.raises(ValueError):
        op.get(mock_file_dir, struct=invalid_idx, prompt=False)


def test_duplicate_idx_in_struct(mock_file_dir, invalid_struct):
    with pytest.raises(ValueError):
        op.get(mock_file_dir, struct=invalid_struct, prompt=False)


def test_invalid_path_data_import(mock_daily_dir, cboe_struct):
    with pytest.raises(ValueError):
        op.get(mock_daily_dir, struct=cboe_struct, prompt=False)


def test_invalid_path_data_import_bulk(mock_daily_file, cboe_struct):
    with pytest.raises(ValueError):
        op.gets(mock_daily_file, struct=cboe_struct, prompt=False)


def test_data_import(mock_daily_file, cboe_struct):
    data = op.get(mock_daily_file, struct=cboe_struct, prompt=False)
    assert data.shape == (2, 13)


def test_data_import_bulk(mock_daily_dir, cboe_struct):
    data = op.gets(mock_daily_dir, struct=cboe_struct, prompt=False)
    assert data.shape == (6, 13)
