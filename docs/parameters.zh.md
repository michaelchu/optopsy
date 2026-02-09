# 策略参数

所有 Optopsy 策略都接受一组通用参数,用于过滤、分组和输出格式化。本指南涵盖所有可用参数及其用法。

## 核心参数

#### 进场和出场时机

#### `max_entry_dte`
**类型:** `int` | **默认值:** `90`

策略进场时的最大到期天数。

```python
results = op.iron_condor(data, max_entry_dte=45)  # 在 45 DTE 或更少时进场
```

**使用场景:**
- `max_entry_dte=30` - 短期交易
- `max_entry_dte=60` - 中期交易
- `max_entry_dte=90` - 长期持仓

---

#### `exit_dte`
**类型:** `int` | **默认值:** `0`

策略出场时的到期天数。使用 `0` 持有至到期。

```python
results = op.long_calls(data, max_entry_dte=60, exit_dte=30)  # 在 30 DTE 时出场
```

**使用场景:**
- `exit_dte=0` - 持有至到期
- `exit_dte=21` - 到期前 3 周出场
- `exit_dte=7` - 到期前 1 周出场

---

#### 过滤参数

#### `max_otm_pct`
**类型:** `float` | **默认值:** `0.5`

期权选择的最大虚值百分比。

```python
results = op.short_puts(data, max_otm_pct=0.20)  # 最大 20% OTM
```

**示例:**
- `0.05` - 接近平值期权(最大 5% OTM)
- `0.20` - 适度虚值(最大 20% OTM)
- `0.50` - 宽范围(最大 50% OTM)

**计算方法:**
```python
# 对于 calls: (strike - underlying_price) / underlying_price
# 对于 puts: (underlying_price - strike) / underlying_price
```

---

#### `min_bid_ask`
**类型:** `float` | **默认值:** `0.05`

期权流动性所需的最小买卖价差。

```python
results = op.iron_condor(data, min_bid_ask=0.10)  # 要求 $0.10+ 价差
```

**使用场景:**
- `0.05` - 流动性较低的标的
- `0.10` - 标准流动性要求
- `0.20` - 高流动性要求(SPX、SPY)

---

#### 分组和聚合

#### `dte_interval`
**类型:** `int` | **默认值:** `7`

按 DTE 范围分组结果的间隔。

```python
results = op.long_calls(data, dte_interval=14)  # 按 14 天桶分组
```

**示例:**
- `7` - 每周分组: (0,7], (7,14], (14,21], ...
- `14` - 双周分组: (0,14], (14,28], ...
- `30` - 每月分组: (0,30], (30,60], ...

---

#### `otm_pct_interval`
**类型:** `float` | **默认值:** `0.05`

按 OTM 百分比范围分组结果的间隔。

```python
results = op.short_strangles(data, otm_pct_interval=0.10)  # 10% OTM 桶
```

**示例:**
- `0.05` - 细粒度: (0.0, 0.05], (0.05, 0.10], ...
- `0.10` - 粗粒度桶: (0.0, 0.10], (0.10, 0.20], ...

---

#### 输出控制

#### `raw`
**类型:** `bool` | **默认值:** `False`

返回原始交易数据而不是聚合统计。

```python
# 聚合统计(默认)
results = op.iron_condor(data, raw=False)
# 输出: ['dte_range', 'otm_pct_range', 'count', 'mean', 'std', ...]

# 原始交易数据
trades = op.iron_condor(data, raw=True)
# 输出: ['expiration', 'strike_leg1', 'strike_leg2', 'entry', 'exit', 'pct_change', ...]
```

**使用场景:**
- `raw=False` - 性能统计、回测结果
- `raw=True` - 自定义分析、详细检查、调试

---

#### `drop_nan`
**类型:** `bool` | **默认值:** `True`

删除结果中包含 NaN 值的行。

```python
results = op.long_calls(data, drop_nan=False)  # 保留 NaN 值
```

---

## Greeks 参数

#### Delta 过滤

#### `delta_min` / `delta_max`
**类型:** `float` | **默认值:** `None`

按 delta 范围过滤期权。

```python
# 目标 30-delta 期权
results = op.short_puts(
    data,
    delta_min=0.25,
    delta_max=0.35
)
```

**常见 Delta 范围:**
- `0.15-0.20` - 1 个标准差 OTM(约 15-20% 概率 ITM)
- `0.25-0.35` - 信用价差常用
- `0.40-0.50` - 接近平值期权
- `0.50+` - 实值期权

**注意:** 需要数据中包含 `delta` 列。

---

#### `delta_interval`
**类型:** `float` | **默认值:** `None`

按 delta 范围分组结果。

```python
results = op.iron_condor(
    data,
    delta_interval=0.10  # 分组为: (0.0,0.1], (0.1,0.2], 等
)
```

---

## 滑点参数

#### `slippage`
**类型:** `str` | **默认值:** `'mid'`

成交价格计算的滑点模型。

```python
results = op.long_calls(data, slippage='liquidity')
```

**选项:**

| 模式 | 描述 | 买入成交 | 卖出成交 | 最适合 |
|------|-------------|----------|-----------|----------|
| `'mid'` | 买卖价之间的中间价 | (bid+ask)/2 | (bid+ask)/2 | 理想/乐观 |
| `'spread'` | 最差情况价差 | Ask | Bid | 保守 |
| `'liquidity'` | 基于成交量的动态 | 动态 | 动态 | 现实 |

---

#### `fill_ratio` (仅限 Liquidity 模式)
**类型:** `float` | **默认值:** `0.5`

基于流动性滑点的基础成交比率(0.0 = bid/ask, 1.0 = ask/bid)。

```python
results = op.iron_condor(
    data,
    slippage='liquidity',
    fill_ratio=0.3  # 更保守的成交(通过价差的 30%)
)
```

**示例:**
- `0.0` - 最差情况(以 ask 买入,以 bid 卖出)
- `0.5` - 中点(默认)
- `1.0` - 最佳情况(以 bid 买入,以 ask 卖出 - 不现实)

---

#### `reference_volume` (仅限 Liquidity 模式)
**类型:** `int` | **默认值:** `1000`

流动性模式下确定流动期权的成交量阈值。

```python
results = op.short_strangles(
    data,
    slippage='liquidity',
    reference_volume=5000  # SPX 的更高阈值
)
```

**指南:**
- `500-1000` - 流动性较低的标的
- `1000-2000` - 标准流动性(默认)
- `5000+` - 高流动性(SPX、SPY、QQQ)

**注意:** 需要数据中包含 `volume` 或 `open_interest` 列。

---

## Calendar & Diagonal 参数

Calendar 和 diagonal 价差使用不同的时间参数:

#### `front_dte_min` / `front_dte_max`
**类型:** `int` | **默认值:** `20` / `40`

前月腿的 DTE 范围。

```python
results = op.long_call_calendar(
    data,
    front_dte_min=25,
    front_dte_max=35  # 前月腿在 25-35 DTE 之间
)
```

---

#### `back_dte_min` / `back_dte_max`
**类型:** `int` | **默认值:** `50` / `90`

后月腿的 DTE 范围。

```python
results = op.long_call_diagonal(
    data,
    back_dte_min=60,
    back_dte_max=120  # 后月腿在 60-120 DTE 之间
)
```

---

## 完整示例

组合多个参数:

```python
import optopsy as op

data = op.csv_data('SPX_options.csv')

results = op.iron_condor(
    data,
    # 时机
    max_entry_dte=45,
    exit_dte=21,

    # 过滤
    max_otm_pct=0.30,
    min_bid_ask=0.15,
    delta_min=0.15,
    delta_max=0.20,

    # 分组
    dte_interval=7,
    otm_pct_interval=0.05,
    delta_interval=0.05,

    # 滑点
    slippage='liquidity',
    fill_ratio=0.5,
    reference_volume=5000,

    # 输出
    raw=False,
    drop_nan=True
)

print(results.head())
```

## 默认值参考

#### 标准策略

```python
default_kwargs = {
    "dte_interval": 7,
    "max_entry_dte": 90,
    "exit_dte": 0,
    "otm_pct_interval": 0.05,
    "max_otm_pct": 0.5,
    "min_bid_ask": 0.05,
    "drop_nan": True,
    "raw": False,
    "delta_min": None,
    "delta_max": None,
    "delta_interval": None,
    "slippage": "mid",
    "fill_ratio": 0.5,
    "reference_volume": 1000,
}
```

#### Calendar & Diagonal 策略

```python
calendar_default_kwargs = {
    "front_dte_min": 20,
    "front_dte_max": 40,
    "back_dte_min": 50,
    "back_dte_max": 90,
    "exit_dte": 7,
    "dte_interval": 7,
    "otm_pct_interval": 0.05,
    "max_otm_pct": 0.5,
    "min_bid_ask": 0.05,
    "drop_nan": True,
    "raw": False,
    "slippage": "mid",
    "fill_ratio": 0.5,
    "reference_volume": 1000,
}
```

## 下一步

- 查看 [示例](examples.md) 了解实际参数使用
- 探索 [策略](strategies.md) 了解特定策略的考虑因素
- 查阅 [API 参考](api-reference.md) 了解函数签名
