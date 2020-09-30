def filter_on_exit_dte(data, exit_dte):
    return data.loc[data["dte_exit"] == exit_dte]
