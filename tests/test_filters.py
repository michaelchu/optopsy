import pytest

import optopsy as op


@pytest.mark.parametrize('params',
                         [(0.5, 0.4, 0.6),
                          (1.0, 0.9, 1.10),
                          (0.1, 0.0, 0.2)
                          ])
def test_abs_delta_filter(vertical_strategies, params):
    f = op.filters.EntryAbsDelta(ideal=params[0], lower=params[1], upper=params[2])
    res = f(vertical_strategies)
    assert all(params[1] <= v <= params[2] for v in res.get('delta'))


@pytest.mark.parametrize('params',
                         [(0.5, 0.4, 0.6),
                          (1.0, 0.9, 1.10),
                          (0.1, 0.0, 0.2)
                          ])
def test_entry_spread_price(vertical_strategies, params):
    f = op.filters.EntrySpreadPrice(ideal=params[0], lower=params[1], upper=params[2])
    res = f(vertical_strategies)
    assert all(params[1] <= v <= params[2] for v in res.get('mark'))
