def calc_entry_px(data, mode='midpoint'):
    if mode == 'midpoint':
        return data.assign(
            entry_opt_price=data[['bid_entry', 'ask_entry']].mean(axis=1))
    elif mode == 'market':
        return data.assign(entry_opt_price=data['ask_entry'])


def calc_exit_px(data, mode='midpoint'):
    if mode == 'midpoint':
        return data.assign(
            exit_opt_price=data[['bid_exit', 'ask_exit']].mean(axis=1))
    elif mode == 'market':
        return data.assign(exit_opt_price=data['ask_exit'])


def calc_pnl(data):
    # calculate the p/l for the trades
    data['entry_price'] = data['entry_opt_price'] * \
        data['ratio'] * data['contracts']
    data['exit_price'] = data['exit_opt_price'] * \
        data['ratio'] * data['contracts']
    data['profit'] = data['exit_price'] - data['entry_price']
    return data


def calc_total_profit(data):
    return data['profit'].sum().round(2)
