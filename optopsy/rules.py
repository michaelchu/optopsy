def _rule_non_overlapping_strike(d):
    return d.loc[d["strike_leg2"] > d["strike_leg1"]]
