from optopsy.strategies import Side
from optopsy.core import _calls
from optopsy.rules import _rule_non_overlapping_strike


def test_no_overlapping_strikes(data):
    leg_def = [(Side.long, _calls)]
    result = _rule_non_overlapping_strike(_calls(data), leg_def)
    assert len(result) == 4
    assert "call" in list(result["option_type"].values)
