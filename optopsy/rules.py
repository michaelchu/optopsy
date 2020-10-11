def _rule_non_overlapping_strike(data, leg_def):
    leg_count = len(leg_def)
    if leg_count == 1:
        return data

    query = " & ".join(
        [f"strike_leg{leg + 1} > strike_leg{leg}" for leg in range(1, leg_count)]
    )

    return data.query(query)
