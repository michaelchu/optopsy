from datetime import date

import pandas.util.testing as pt
import pytest

from .base import *


def test_invalid_fields():
    with pytest.raises(ValueError):
        op.get(os.path.join(os.path.dirname(__file__), 'test_data', 'test_dod_a.csv'),
               start=date(2016, 1, 1),
               end=date(2016, 12, 31),
               struct=invalid_fields
               )


def test_valid_fields():
    try:
        op.get(os.path.join(os.path.dirname(__file__), 'test_data', 'test_dod_a.csv'),
               start=date(2016, 1, 1),
               end=date(2016, 12, 31),
               struct=valid_fields,
               prompt=False
               )
    except ValueError:
        pytest.fail('ValueError raised')


def test_invalid_idx():
    with pytest.raises(ValueError):
        op.get(os.path.join(os.path.dirname(__file__), 'test_data', 'test_dod_a.csv'),
               start=date(2016, 1, 1),
               end=date(2016, 12, 31),
               struct=invalid_idx,
               prompt=False
               )


def test_invalid_start_end():
    start = date(2016, 1, 1)
    end = date(2015, 1, 1)

    with pytest.raises(ValueError):
        op.get(os.path.join(os.path.dirname(__file__), 'test_data', 'test_dod_a.csv'),
               start=start,
               end=end,
               struct=valid_fields,
               prompt=False
               )


def test_invalid_start_end_fields():
    start = date(2016, 1, 1)
    end = date(2015, 1, 1)

    with pytest.raises(ValueError):
        op.get(os.path.join(os.path.dirname(__file__), 'test_data', 'test_dod_a.csv'),
               start=start,
               end=end,
               struct=invalid_fields,
               prompt=False
               )


def test_data_cboe_import():
    cols = list(zip(*cboe_struct))[0]
    test_df = pd.DataFrame(cboe_test_data, columns=cols)
    test_df['expiration'] = pd.to_datetime(test_df.expiration,
                                           infer_datetime_format=True,
                                           format='%Y-%m-%d'
                                           )
    test_df['quote_date'] = pd.to_datetime(test_df.quote_date,
                                           infer_datetime_format=True,
                                           format='%Y-%m-%d'
                                           )
    test_df.set_index('quote_date', inplace=True, drop=False)

    data = op.get(os.path.join(os.path.dirname(__file__), 'test_data', 'test_cboe_spx.csv'),
                  start=date(2016, 1, 1),
                  end=date(2016, 12, 31),
                  struct=cboe_struct,
                  prompt=False
                  )

    pt.assert_frame_equal(test_df, data)


def test_data_dod_import():
    cols = list(zip(*dod_struct))[0]
    test_df = pd.DataFrame(dod_test_data, columns=cols)
    test_df['expiration'] = pd.to_datetime(test_df.expiration, format='%Y-%m-%d')
    test_df['quote_date'] = pd.to_datetime(test_df.quote_date, format='%Y-%m-%d')
    test_df.set_index(['quote_date'], inplace=True, drop=False)

    data = op.get(os.path.join(os.path.dirname(__file__), 'test_data', 'test_dod_a.csv'),
                  start=date(2016, 1, 1),
                  end=date(2016, 12, 31),
                  struct=dod_struct,
                  prompt=False
                  )

    pt.assert_frame_equal(test_df, data)


def test_data_dod_with_sym_import():
    cols = list(zip(*dod_struct))[0]
    test_df = pd.DataFrame(dod_test_data, columns=cols)
    test_df['expiration'] = pd.to_datetime(test_df.expiration, format='%Y-%m-%d')
    test_df['quote_date'] = pd.to_datetime(test_df.quote_date, format='%Y-%m-%d')
    test_df.set_index(['quote_date'], inplace=True, drop=False)

    data = op.get(os.path.join(os.path.dirname(__file__), 'test_data', 'test_dod_a.csv'),
                  start=date(2016, 1, 1),
                  end=date(2016, 12, 31),
                  struct=dod_struct_with_opt_sym,
                  prompt=False
                  )

    pt.assert_frame_equal(test_df, data)


def test_data_cboe_import_bulk():
    cols = list(zip(*cboe_struct))[0]
    test_df = pd.DataFrame(cboe_test_data, columns=cols)
    test_df['expiration'] = pd.to_datetime(test_df.expiration, infer_datetime_format=True,
                                           format='%Y-%m-%d')
    test_df['quote_date'] = pd.to_datetime(test_df.quote_date, infer_datetime_format=True,
                                           format='%Y-%m-%d')
    test_df.set_index(['quote_date'], inplace=True, drop=False)

    data = op.gets(os.path.join(os.path.dirname(__file__), 'test_data', 'daily'),
                   start=date(2016, 1, 4),
                   end=date(2016, 1, 6),
                   struct=cboe_struct,
                   prompt=False
                   )

    pt.assert_frame_equal(test_df, data)


def test_data_cboe_date_range():
    cols = list(zip(*cboe_struct))[0]
    test_df = pd.DataFrame(cboe_test_data[2:], columns=cols)
    test_df['expiration'] = pd.to_datetime(test_df.expiration, infer_datetime_format=True,
                                           format='%Y-%m-%d')
    test_df['quote_date'] = pd.to_datetime(test_df.quote_date, infer_datetime_format=True,
                                           format='%Y-%m-%d')
    test_df.set_index(['quote_date'], inplace=True, drop=False)

    data = op.gets(os.path.join(os.path.dirname(__file__), 'test_data', 'daily'),
                   start=date(2016, 1, 5),
                   end=date(2016, 1, 6),
                   struct=cboe_struct,
                   prompt=False
                   )

    pt.assert_frame_equal(test_df, data)


def test_duplicate_idx_in_struct():
    with pytest.raises(ValueError):
        op.get(os.path.join(os.path.dirname(__file__), 'test_data', 'daily'),
               start=date(2016, 1, 5),
               end=date(2016, 1, 6),
               struct=invalid_struct,
               prompt=False
               )
