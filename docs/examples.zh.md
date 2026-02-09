# 示例

本页提供使用 Optopsy 进行期权回测的实际示例。

## 基础示例

#### 简单的 Long Calls 回测

```python
import optopsy as op

# 加载数据
data = op.csv_data('SPX_2023.csv')

# 回测 long calls
results = op.long_calls(data)

print(results.head())
```

#### 自定义参数的 Iron Condor

```python
results = op.iron_condor(
    data,
    max_entry_dte=45,
    exit_dte=21,
    max_otm_pct=0.25,
    min_bid_ask=0.10
)

# 过滤出表现最佳的 DTE 范围
best_dte = results[results['mean'] > 0.20]
print(best_dte)
```

## 高级示例

#### Delta 中性 Iron Condors

针对空头行权价的特定 delta 范围:

```python
results = op.iron_condor(
    data,
    max_entry_dte=45,
    exit_dte=21,
    delta_min=0.15,  # 目标 15-20 delta
    delta_max=0.20,
    delta_interval=0.05,
    min_bid_ask=0.10
)

# 按 delta 范围分析
print(results.groupby('delta_range')['mean'].describe())
```

#### 财报 Straddle 策略

回测财报期间的 long straddles:

```python
# 加载财报日期
earnings_dates = ['2023-01-15', '2023-04-15', '2023-07-15', '2023-10-15']

# 过滤财报周围的数据(±7 天)
import pandas as pd
data['quote_date'] = pd.to_datetime(data['quote_date'])

earnings_data = []
for date in pd.to_datetime(earnings_dates):
    mask = (data['quote_date'] >= date - pd.Timedelta(days=7)) & \
           (data['quote_date'] <= date + pd.Timedelta(days=7))
    earnings_data.append(data[mask])

earnings_df = pd.concat(earnings_data)

# 回测 straddles
results = op.long_straddles(
    earnings_df,
    max_entry_dte=7,  # 提前 1 周进场
    exit_dte=0,       # 持有至财报后
    max_otm_pct=0.05  # ATM straddles
)

print(results)
```

#### 时间衰减分析

比较 short strangles 的不同出场时间:

```python
exit_times = [0, 7, 14, 21, 30]
results_by_exit = {}

for exit_dte in exit_times:
    results = op.short_strangles(
        data,
        max_entry_dte=45,
        exit_dte=exit_dte,
        max_otm_pct=0.30
    )
    results_by_exit[exit_dte] = results['mean'].mean()

# 绘制结果
import matplotlib.pyplot as plt
plt.bar(exit_times, results_by_exit.values())
plt.xlabel('Exit DTE')
plt.ylabel('Mean Return')
plt.title('Short Strangle Returns by Exit Time')
plt.show()
```

#### 滑点比较

比较不同的滑点模型:

```python
slippage_modes = ['mid', 'spread', 'liquidity']
results_comparison = {}

for mode in slippage_modes:
    results = op.iron_condor(
        data,
        max_entry_dte=45,
        exit_dte=21,
        slippage=mode,
        fill_ratio=0.5,
        reference_volume=1000
    )
    results_comparison[mode] = results['mean'].mean()

print("Slippage Model Comparison:")
for mode, avg_return in results_comparison.items():
    print(f"{mode}: {avg_return:.2%}")
```

## 数据分析示例

#### 原始交易数据分析

获取单个交易进行自定义分析:

```python
# 获取原始交易数据
trades = op.iron_condor(
    data,
    max_entry_dte=45,
    exit_dte=21,
    raw=True  # 返回单个交易
)

# 自定义分析
import pandas as pd

# 胜率
win_rate = (trades['pct_change'] > 0).mean()
print(f"Win Rate: {win_rate:.1%}")

# 平均盈利 vs 平均亏损
avg_winner = trades[trades['pct_change'] > 0]['pct_change'].mean()
avg_loser = trades[trades['pct_change'] < 0]['pct_change'].mean()
print(f"Avg Winner: {avg_winner:.2%}")
print(f"Avg Loser: {avg_loser:.2%}")

# 盈亏比
total_profit = trades[trades['pct_change'] > 0]['pct_change'].sum()
total_loss = abs(trades[trades['pct_change'] < 0]['pct_change'].sum())
profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
print(f"Profit Factor: {profit_factor:.2f}")
```

#### 月度表现

按月份分析策略表现:

```python
trades = op.short_puts(data, raw=True)

# 转换为 datetime
trades['entry_date'] = pd.to_datetime(trades['quote_date'])
trades['month'] = trades['entry_date'].dt.to_period('M')

# 按月分组
monthly_perf = trades.groupby('month').agg({
    'pct_change': ['count', 'mean', 'std', 'sum']
})

print(monthly_perf)
```

#### 行权价选择分析

按 OTM 百分比分析表现:

```python
results = op.short_puts(
    data,
    max_entry_dte=45,
    exit_dte=21,
    max_otm_pct=0.50,
    otm_pct_interval=0.05
)

# 找到最优 OTM 范围
optimal = results.loc[results['mean'].idxmax()]
print(f"Optimal OTM Range: {optimal['otm_pct_range']}")
print(f"Mean Return: {optimal['mean']:.2%}")
print(f"Count: {optimal['count']:.0f}")
```

## 多策略比较

比较多种策略:

```python
strategies = {
    'Long Calls': op.long_calls,
    'Short Puts': op.short_puts,
    'Iron Condor': op.iron_condor,
    'Long Straddle': op.long_straddles
}

comparison = {}
for name, strategy_func in strategies.items():
    results = strategy_func(
        data,
        max_entry_dte=45,
        exit_dte=21
    )
    comparison[name] = {
        'mean': results['mean'].mean(),
        'std': results['std'].mean(),
        'max': results['max'].max(),
        'min': results['min'].min()
    }

# 显示比较
df_comparison = pd.DataFrame(comparison).T
print(df_comparison)
```

## 投资组合模拟

模拟多策略投资组合:

```python
# 定义投资组合配置
portfolio = {
    'iron_condor': 0.50,
    'short_strangles': 0.30,
    'long_call_spread': 0.20
}

# 获取每个策略的原始交易
trades = {}
trades['iron_condor'] = op.iron_condor(data, raw=True)
trades['short_strangles'] = op.short_strangles(data, raw=True)
trades['long_call_spread'] = op.long_call_spread(data, raw=True)

# 按配置加权收益
for strategy, weight in portfolio.items():
    trades[strategy]['weighted_return'] = trades[strategy]['pct_change'] * weight

# 合并所有交易
all_trades = pd.concat([
    trades[s][['quote_date', 'weighted_return']]
    for s in portfolio.keys()
])

# 按日期聚合
portfolio_returns = all_trades.groupby('quote_date')['weighted_return'].sum()

print(f"Portfolio Mean Return: {portfolio_returns.mean():.2%}")
print(f"Portfolio Std Dev: {portfolio_returns.std():.2%}")
print(f"Sharpe Ratio (annualized): {(portfolio_returns.mean() / portfolio_returns.std()) * (252**0.5):.2f}")
```

## 性能指标

计算综合性能统计:

```python
def calculate_metrics(trades_df):
    """计算策略的性能指标。"""
    returns = trades_df['pct_change']

    metrics = {
        'Total Trades': len(returns),
        'Win Rate': (returns > 0).mean(),
        'Mean Return': returns.mean(),
        'Median Return': returns.median(),
        'Std Dev': returns.std(),
        'Max Win': returns.max(),
        'Max Loss': returns.min(),
        'Profit Factor': returns[returns > 0].sum() / abs(returns[returns < 0].sum()),
        'Sharpe Ratio': returns.mean() / returns.std() if returns.std() > 0 else 0
    }

    return pd.Series(metrics)

# 应用于策略
trades = op.iron_condor(data, raw=True)
metrics = calculate_metrics(trades)
print(metrics)
```

## 处理不同数据源

#### 历史期权数据提供商

```python
# 示例: 从不同 CSV 格式加载

# 格式 1: CBOE 数据导出
data = op.csv_data(
    'cboe_spx.csv',
    underlying_symbol='underlying_symbol',
    underlying_price='underlying_bid_1545',
    option_type='option_type',
    expiration='expiration',
    quote_date='quote_date',
    strike='strike',
    bid='bid',
    ask='ask'
)

# 格式 2: 索引列
data = op.csv_data(
    'provider_data.csv',
    underlying_symbol=0,
    underlying_price=1,
    option_type=2,
    expiration=3,
    quote_date=4,
    strike=5,
    bid=6,
    ask=7
)
```

## 最佳实践

#### 1. 始终使用过滤器

```python
# 不好: 没有过滤
results = op.iron_condor(data)

# 好: 过滤以确保质量
results = op.iron_condor(
    data,
    max_entry_dte=45,
    exit_dte=21,
    min_bid_ask=0.10,  # 确保流动性
    max_otm_pct=0.30
)
```

#### 2. 比较同类事物

```python
# 比较策略时使用相同参数
params = {
    'max_entry_dte': 45,
    'exit_dte': 21,
    'max_otm_pct': 0.25
}

ic_results = op.iron_condor(data, **params)
strangle_results = op.short_strangles(data, **params)
```

#### 3. 现实的滑点

```python
# 使用 liquidity 模式获得现实结果
results = op.iron_condor(
    data,
    slippage='liquidity',
    fill_ratio=0.5,
    reference_volume=1000
)
```

## 下一步

- 查看 [策略文档](strategies.md) 了解特定策略详情
- 查看 [参数](parameters.md) 了解所有配置选项
- 查阅 [API 参考](api-reference.md) 了解函数签名
- 探索代码仓库中的 `samples/` 目录获取更多示例
