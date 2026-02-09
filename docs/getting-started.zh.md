# 入门指南

本指南将引导您完成 Optopsy 的设置并运行第一次回测。

## 安装

使用 pip 安装 Optopsy:

```bash
pip install optopsy
```

### 系统要求

- Python 3.8 或更高版本
- Pandas 2.0 或更高版本
- NumPy 1.26 或更高版本

## 数据格式

Optopsy 需要包含以下列的历史期权链数据:

| 列名 | 描述 | 示例 |
|--------|-------------|---------|
| `underlying_symbol` | 股票代码 | SPX, SPY, QQQ |
| `underlying_price` | 股票/指数价格 | 4500.00 |
| `option_type` | Call 或 Put | 'c', 'p', 'call', 'put' |
| `expiration` | 期权到期日 | 2023-01-20 |
| `quote_date` | 报价日期 | 2023-01-01 |
| `strike` | 行权价 | 4500 |
| `bid` | 买入价 | 10.50 |
| `ask` | 卖出价 | 11.00 |

### 用于 Greeks 过滤的可选列

| 列名 | 描述 |
|--------|-------------|
| `delta` | Delta 值 |
| `gamma` | Gamma 值 |
| `theta` | Theta 值 |
| `vega` | Vega 值 |
| `volume` | 交易量 |
| `open_interest` | 持仓量 |

## 加载数据

### 从 CSV 加载

使用 `csv_data()` 从 CSV 文件加载期权数据:

```python
import optopsy as op

data = op.csv_data(
    'options_data.csv',
    underlying_symbol=0,      # 列索引或列名
    underlying_price=1,
    option_type=2,
    expiration=3,
    quote_date=4,
    strike=5,
    bid=6,
    ask=7
)
```

该函数接受以下两种方式:
- **列索引**(整数): 每列的位置
- **列名**(字符串): CSV 文件的表头名称

### 从 DataFrame 加载

如果您已有 pandas DataFrame,请确保它包含所需的列:

```python
import pandas as pd
import optopsy as op

# 您现有的 DataFrame
df = pd.read_csv('options_data.csv')

# 重命名列以匹配 Optopsy 的预期格式
df = df.rename(columns={
    'Symbol': 'underlying_symbol',
    'UnderlyingPrice': 'underlying_price',
    'Type': 'option_type',
    'Expiration': 'expiration',
    'QuoteDate': 'quote_date',
    'Strike': 'strike',
    'Bid': 'bid',
    'Ask': 'ask'
})

# 现在可以直接使用
results = op.long_calls(df)
```

## 运行第一次回测

### 示例: Long Calls

让我们回测一个简单的 long call 策略:

```python
import optopsy as op

# 加载数据
data = op.csv_data('SPX_2023.csv')

# 使用默认参数运行回测
results = op.long_calls(data)

print(results)
```

### 自定义参数示例

自定义回测参数:

```python
results = op.long_calls(
    data,
    max_entry_dte=60,        # 在 60 天 DTE 时进场
    exit_dte=30,             # 在 30 DTE 时出场
    dte_interval=7,          # 按 7 天间隔分组结果
    max_otm_pct=0.20,        # 最大 20% 虚值
    otm_pct_interval=0.05,   # 按 5% OTM 间隔分组
    min_bid_ask=0.10         # 最小 $0.10 买卖价差
)

print(results.head())
```

## 理解输出结果

### 聚合结果(默认)

默认情况下,策略返回按 DTE 和 OTM% 范围分组的聚合统计数据:

```python
results = op.long_calls(data)
print(results.columns)
# ['dte_range', 'otm_pct_range', 'count', 'mean', 'std', 'min', '25%', '50%', '75%', 'max']
```

输出示例:

| dte_range | otm_pct_range | count | mean | std | min | 50% | max |
|-----------|---------------|-------|------|-----|-----|-----|-----|
| (0, 7] | (0.0, 0.05] | 1250 | 0.23 | 0.45 | -1.0 | 0.15 | 2.8 |
| (0, 7] | (0.05, 0.10] | 980 | 0.18 | 0.52 | -1.0 | 0.10 | 3.2 |

### 原始交易数据

通过设置 `raw=True` 获取单个交易详情:

```python
results = op.long_calls(data, raw=True)
print(results.columns)
# ['underlying_symbol', 'expiration', 'dte_entry', 'strike', 'entry', 'exit', 'pct_change', ...]
```

这将为您提供每笔交易的详细信息,用于自定义分析。

## 下一步

- 探索 [全部 28 种策略](strategies.md)
- 了解 [策略参数](parameters.md)
- 查看更多包含 Greeks 过滤和滑点的 [示例](examples.md)
- 阅读 [API 参考](api-reference.md) 获取详细的函数文档

## 常见问题

### 日期格式错误

如果遇到日期解析错误,请确保您的日期使用标准格式:
- ISO 格式: `2023-01-20`
- 美国格式: `01/20/2023`
- 欧洲格式: `20/01/2023`

`csv_data()` 函数将尝试自动检测日期格式。

### 缺少列

如果看到列的 "KeyError" 错误,请检查:
1. 该列是否存在于您的数据中
2. 您在 `csv_data()` 中指定的列索引或名称是否正确
3. 列名是否完全匹配(区分大小写)

### 结果为空

如果回测没有返回结果:
- 检查您的参数范围(DTE、OTM% 等)
- 验证您的数据覆盖了您正在测试的时间段
- 确保买卖价差满足 `min_bid_ask` 阈值
