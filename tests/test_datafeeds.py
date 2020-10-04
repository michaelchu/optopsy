import os
from datetime import datetime
import optopsy as op


def filepath():
    curr_file = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(curr_file, "./test_data/data.csv")


def test_import_csv_file():
    data = op.datafeeds.csv_data(
        filepath(),
        underlying_symbol=0,
        underlying_price=1,
        option_type=2,
        expiration=3,
        quote_date=4,
        strike=5,
        bid=6,
        ask=7,
    )

    expected_columns = [
        "underlying_symbol",
        "underlying_price",
        "option_type",
        "expiration",
        "quote_date",
        "strike",
        "bid",
        "ask",
    ]
    assert list(data.columns) == expected_columns
    assert not data.empty


def test_import_csv_with_date_range():
    data = op.datafeeds.csv_data(
        filepath(),
        start_date=datetime(1990, 1, 1),
        end_date=datetime(1990, 12, 31),
        underlying_symbol=0,
        underlying_price=1,
        option_type=2,
        expiration=3,
        quote_date=4,
        strike=5,
        bid=6,
        ask=7,
    )
    assert len(data) == 1
    assert data.iloc[0]["expiration"] == datetime(1990, 1, 20)


def test_import_csv_with_start_date():
    data = op.datafeeds.csv_data(
        filepath(),
        start_date=datetime(2000, 1, 1),
        underlying_symbol=0,
        underlying_price=1,
        option_type=2,
        expiration=3,
        quote_date=4,
        strike=5,
        bid=6,
        ask=7,
    )
    assert len(data) == 3
    assert data.iloc[0]["expiration"] == datetime(2000, 1, 20)
    assert data.iloc[1]["expiration"] == datetime(2010, 1, 20)
    assert data.iloc[2]["expiration"] == datetime(2020, 1, 20)


def test_import_csv_with_end_date():
    data = op.datafeeds.csv_data(
        filepath(),
        end_date=datetime(2010, 1, 1),
        underlying_symbol=0,
        underlying_price=1,
        option_type=2,
        expiration=3,
        quote_date=4,
        strike=5,
        bid=6,
        ask=7,
    )
    assert len(data) == 2
    assert data.iloc[0]["expiration"] == datetime(1990, 1, 20)
    assert data.iloc[1]["expiration"] == datetime(2000, 1, 20)


def test_import_csv_with_no_date_range():
    data = op.datafeeds.csv_data(
        filepath(),
        underlying_symbol=0,
        underlying_price=1,
        option_type=2,
        expiration=3,
        quote_date=4,
        strike=5,
        bid=6,
        ask=7,
    )
    assert len(data) == 4
    assert data.iloc[0]["expiration"] == datetime(1990, 1, 20)
    assert data.iloc[1]["expiration"] == datetime(2000, 1, 20)
    assert data.iloc[2]["expiration"] == datetime(2010, 1, 20)
    assert data.iloc[3]["expiration"] == datetime(2020, 1, 20)
