# API 参考

Optopsy 函数的完整 API 文档。

!!! info "通用参数"
    所有策略函数共享通用参数。请参阅下面的 [通用参数](#通用参数) 部分,了解 `max_entry_dte`、`exit_dte`、`max_otm_pct`、`min_bid_ask`、滑点设置等的详细文档。

## 数据加载

#### csv_data

从 CSV 文件加载期权数据。

::: optopsy.datafeeds.csv_data

---

## 单腿策略

!!! note
    所有单腿策略接受相同的参数。完整文档请参阅 [通用参数](#通用参数)。

#### long_calls

::: optopsy.strategies.long_calls

#### short_calls

::: optopsy.strategies.short_calls

#### long_puts

::: optopsy.strategies.long_puts

#### short_puts

::: optopsy.strategies.short_puts

---

## Straddles & Strangles

!!! note
    所有 straddle/strangle 策略接受相同的参数。完整文档请参阅 [通用参数](#通用参数)。

#### long_straddles

::: optopsy.strategies.long_straddles

#### short_straddles

::: optopsy.strategies.short_straddles

#### long_strangles

::: optopsy.strategies.long_strangles

#### short_strangles

::: optopsy.strategies.short_strangles

---

## 垂直价差

!!! note
    所有垂直价差策略接受相同的参数。完整文档请参阅 [通用参数](#通用参数)。

#### long_call_spread

::: optopsy.strategies.long_call_spread

#### short_call_spread

::: optopsy.strategies.short_call_spread

#### long_put_spread

::: optopsy.strategies.long_put_spread

#### short_put_spread

::: optopsy.strategies.short_put_spread

---

## 蝶式价差

!!! note
    所有蝶式策略接受相同的参数。完整文档请参阅 [通用参数](#通用参数)。

#### long_call_butterfly

::: optopsy.strategies.long_call_butterfly

#### short_call_butterfly

::: optopsy.strategies.short_call_butterfly

#### long_put_butterfly

::: optopsy.strategies.long_put_butterfly

#### short_put_butterfly

::: optopsy.strategies.short_put_butterfly

---

## Iron 策略

!!! note
    所有 iron 策略接受相同的参数。完整文档请参阅 [通用参数](#通用参数)。

#### iron_condor

::: optopsy.strategies.iron_condor

#### reverse_iron_condor

::: optopsy.strategies.reverse_iron_condor

#### iron_butterfly

::: optopsy.strategies.iron_butterfly

#### reverse_iron_butterfly

::: optopsy.strategies.reverse_iron_butterfly

---

## 备兑策略

!!! note
    所有备兑策略接受相同的参数。完整文档请参阅 [通用参数](#通用参数)。

#### covered_call

::: optopsy.strategies.covered_call

#### protective_put

::: optopsy.strategies.protective_put

---

## 日历价差

!!! note
    日历价差除了通用参数外,还有额外的时间参数(`front_dte_min`、`front_dte_max`、`back_dte_min`、`back_dte_max`)。完整文档请参阅 [通用参数](#通用参数) 和 [Calendar/Diagonal 参数](#calendardiagonal-参数)。

#### long_call_calendar

::: optopsy.strategies.long_call_calendar

#### short_call_calendar

::: optopsy.strategies.short_call_calendar

#### long_put_calendar

::: optopsy.strategies.long_put_calendar

#### short_put_calendar

::: optopsy.strategies.short_put_calendar

---

## 对角价差

!!! note
    对角价差除了通用参数外,还有额外的时间参数(`front_dte_min`、`front_dte_max`、`back_dte_min`、`back_dte_max`)。完整文档请参阅 [通用参数](#通用参数) 和 [Calendar/Diagonal 参数](#calendardiagonal-参数)。

#### long_call_diagonal

::: optopsy.strategies.long_call_diagonal

#### short_call_diagonal

::: optopsy.strategies.short_call_diagonal

#### long_put_diagonal

::: optopsy.strategies.long_put_diagonal

#### short_put_diagonal

::: optopsy.strategies.short_put_diagonal

---

## 通用参数

所有策略函数都接受这些通用参数:

#### 时间参数

- **max_entry_dte** (int, 默认=90): 进场时的最大到期天数
- **exit_dte** (int, 默认=0): 出场时的到期天数
- **dte_interval** (int, 默认=7): DTE 范围的分组间隔

#### 过滤参数

- **max_otm_pct** (float, 默认=0.5): 最大虚值百分比
- **otm_pct_interval** (float, 默认=0.05): OTM 范围的分组间隔
- **min_bid_ask** (float, 默认=0.05): 最小买卖价差过滤器

#### Greeks 参数

- **delta_min** (float, 可选): 最小 delta 过滤器
- **delta_max** (float, 可选): 最大 delta 过滤器
- **delta_interval** (float, 可选): delta 范围的分组间隔

#### 滑点参数

- **slippage** (str, 默认='mid'): 滑点模式 - 'mid'、'spread' 或 'liquidity'
- **fill_ratio** (float, 默认=0.5): liquidity 模式的成交比率(0.0-1.0)
- **reference_volume** (int, 默认=1000): 流动期权的成交量阈值

#### 输出参数

- **raw** (bool, 默认=False): 返回原始交易数据而不是聚合统计
- **drop_nan** (bool, 默认=True): 删除包含 NaN 值的行

#### Calendar/Diagonal 参数

这些策略有额外的时间参数:

- **front_dte_min** (int, 默认=20): 前月腿的最小 DTE
- **front_dte_max** (int, 默认=40): 前月腿的最大 DTE
- **back_dte_min** (int, 默认=50): 后月腿的最小 DTE
- **back_dte_max** (int, 默认=90): 后月腿的最大 DTE

---

## 返回值

#### 聚合结果(默认)

当 `raw=False`(默认)时,策略返回聚合统计:

**列:**
- `dte_range`: DTE 间隔组
- `otm_pct_range`: OTM 百分比间隔组
- `count`: 组中的交易数量
- `mean`: 平均收益
- `std`: 收益标准差
- `min`: 最小收益
- `25%`: 第 25 百分位
- `50%`: 中位收益
- `75%`: 第 75 百分位
- `max`: 最大收益

#### 原始交易数据

当 `raw=True` 时,策略返回单个交易详情:

**列(因策略而异):**
- `underlying_symbol`: 股票代码
- `expiration`: 期权到期日
- `dte_entry`: 进场时的到期天数
- `strike` / `strike_leg1`、`strike_leg2` 等: 行权价
- `entry`: 进场价格/成本
- `exit`: 出场价格/收益
- `pct_change`: 百分比收益
- 其他特定于策略的列

---

## 示例

详细使用示例请参阅 [示例页面](examples.md)。

## 类型提示

所有函数都包含完整的类型提示,使用 TypedDict 提供 IDE 自动完成支持:

```python
import pandas as pd
from typing_extensions import Unpack
from optopsy import StrategyParams

def long_calls(data: pd.DataFrame, **kwargs: Unpack[StrategyParams]) -> pd.DataFrame:
    ...
```

### 使用类型提示

导入 `StrategyParams` 或 `CalendarStrategyParams` 以获得更好的 IDE 支持:

```python
import optopsy as op
from optopsy import StrategyParams

# 您的 IDE 现在将为所有参数提供自动完成
results = op.iron_condor(
    data,
    max_entry_dte=45,      # 类型: int
    exit_dte=21,           # 类型: int
    slippage='liquidity',  # 类型: Literal['mid', 'spread', 'liquidity']
    fill_ratio=0.5,        # 类型: float
)
```

有关在 Optopsy 中使用类型提示的详细文档,请参阅 [TYPE_HINTS.md](https://github.com/michaelchu/optopsy/blob/master/TYPE_HINTS.md)。
