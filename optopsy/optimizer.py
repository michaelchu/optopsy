# def _gen_scenarios(params):
#     for v in product(*params.values()):
#         yield dict(zip(params.keys(), v))


# def optimize(data, func, round=2, **params):
#     # iterate over each param and gather the items
#     scenarios = list(_gen_scenarios(params))
#     res = []
#     tot = len(scenarios)
#     bar = py.ProgBar(len(scenarios), bar_char="█")

#     for i, scenario in enumerate(scenarios):
#         test = func(data, scenario)
#         if test is not None:
#             res.append(calc_stats(test, scenario))
#         bar.update()

#     if not res:
#         raise ValueError(
#             "No results returned from optimizer, please check your inputs..."
#         )
#     return (
#         pd.DataFrame.from_dict(res)
#         .sort_values(by=["Exp Val"], ascending=False)
#         .reset_index(drop=True)
#         .round(round)
#     )
