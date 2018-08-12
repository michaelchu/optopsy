import os
from datetime import date
from .struct_fixtures import invalid_fields, invalid_idx, invalid_struct, valid_struct, cboe_struct

import pytest

import optopsy as op


@pytest.fixture
def mock_daily_dir():
    return os.path.join(os.path.dirname(__file__), 'test_data')


@pytest.fixture
def mock_daily_file():
    return os.path.join(os.path.dirname(__file__), 'test_data', 'test_cboe_20160104.csv')


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
        pytest.fail('ValueError raised')


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


# TODO: finish this
def test_data_import(mock_daily_file, cboe_struct):
    data = op.get(mock_daily_file, struct=cboe_struct, prompt=False)


# TODO: finish this
def test_data_import_bulk(mock_daily_dir, cboe_struct):
    data = op.gets(mock_daily_dir, struct=cboe_struct, prompt=False)
