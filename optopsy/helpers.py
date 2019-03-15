def assign_dte(data):
    if "dte" not in data.columns:
        return data.assign(dte=lambda r: (r["expiration"] - r["quote_date"]).dt.days)
    return data


def inspect(data):
    print(data)
    return data
