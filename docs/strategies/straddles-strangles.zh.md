# Straddles & Strangles

Straddles 和 strangles 是基于波动率的策略,结合 calls 和 puts 以从大幅价格波动(long)或低波动率(short)中获利。

## Long Straddle

#### 描述
Long straddle 由在**相同行权价**买入一个 call 和一个 put 组成,通常在平值。该策略从任一方向的大幅价格波动中获利。

**组成:**
- Long 1 个 call,行权价为 X
- Long 1 个 put,行权价为 X

#### 市场观点
- **预期高波动率** - 预期大幅上涨或下跌
- 方向无关紧要,只在乎幅度
- 在财报公告或重大事件之前常见

#### 盈亏
- **最大盈利**: 无限(任一方向)
- **最大损失**: 支付的总权利金(如果价格保持在行权价)
- **盈亏平衡点**: 行权价 ± 支付的总权利金

#### 示例

```python
import optopsy as op

data = op.csv_data('SPX_options.csv')

# 回测 long straddles
results = op.long_straddles(
    data,
    max_entry_dte=30,
    exit_dte=0,  # 持有至到期
    max_otm_pct=0.05  # 接近 ATM
)

print(results)
```

#### 使用场景
- 预期大幅波动的财报交易
- 在美联储公告或重大经济数据发布前
- 当隐含波动率低但您预期爆发时
- 二元事件(FDA 批准、法院裁决)

---

## Short Straddle

#### 描述
Short straddle 由在**相同行权价**卖出一个 call 和一个 put 组成。该策略在价格在到期时保持在行权价附近时获利。

**组成:**
- Short 1 个 call,行权价为 X
- Short 1 个 put,行权价为 X

#### 市场观点
- **预期低波动率** - 价格保持稳定
- 如果价格在到期时恰好在行权价则最大盈利
- 如果价格在任一方向大幅移动,利润会侵蚀

#### 盈亏
- **最大盈利**: 收到的总权利金
- **最大损失**: 无限(如果价格远离行权价)
- **盈亏平衡点**: 行权价 ± 收到的总权利金

#### 示例

```python
results = op.short_straddles(
    data,
    max_entry_dte=45,
    exit_dte=21,
    max_otm_pct=0.05,  # ATM straddles
    min_bid_ask=0.20    # 确保流动期权
)
```

#### 使用场景
- 高隐含波动率环境
- 财报后预期 IV 挤压
- 区间震荡市场
- 低波动率期间的收益创造

#### ⚠️ 风险警告
Short straddles 在两个方向都有无限风险。考虑使用 iron butterflies 作为有限风险的替代方案。

---

## Long Strangle

#### 描述
Long strangle 由买入虚值 call 和虚值 put 在**不同行权价**组成。这类似于 long straddle,但成本更低,盈亏平衡点更宽。

**组成:**
- Long 1 个虚值 put,行权价为 X
- Long 1 个虚值 call,行权价为 Y(Y > X)

#### 市场观点
- **预期高波动率** - 预期大幅波动
- 成本低于 straddles,但需要更大的波动才能获利
- 对于爆炸性波动,风险/回报比 straddles 更好

#### 盈亏
- **最大盈利**: 无限(任一方向)
- **最大损失**: 支付的总权利金
- **盈亏平衡点**: Put 行权价 - 总权利金, Call 行权价 + 总权利金

#### 示例

```python
results = op.long_strangles(
    data,
    max_entry_dte=45,
    exit_dte=21,
    max_otm_pct=0.20  # 更宽的行权价以降低成本
)
```

#### 使用场景
- 成本更低的波动率交易
- 在结果未知的重大事件之前
- 当您预期大幅波动但想降低成本时
- 在大规模波动时比 straddles 有更高的盈利概率

---

## Short Strangle

#### 描述
Short strangle 由卖出虚值 call 和虚值 put 在**不同行权价**组成。这提供了比 short straddle 更宽的盈利区间。

**组成:**
- Short 1 个虚值 put,行权价为 X
- Short 1 个虚值 call,行权价为 Y(Y > X)

#### 市场观点
- **低至中等波动率** - 价格保持在区间内
- 盈利区间比 short straddles 更宽
- 如果价格适度移动更宽容

#### 盈亏
- **最大盈利**: 收到的总权利金
- **最大损失**: 无限(超过空头行权价)
- **盈亏平衡点**: Put 行权价 - 总权利金, Call 行权价 + 总权利金

#### 示例

```python
results = op.short_strangles(
    data,
    max_entry_dte=45,
    exit_dte=21,
    max_otm_pct=0.30,  # 宽行权价以获得更安全的区间
    min_bid_ask=0.15
)
```

#### 使用场景
- 在区间震荡市场中的收益
- 比 short straddles 有更高的成功概率
- 高 IV 事件后(财报后)
- 当您预期低波动率但想要缓冲时

#### 管理技巧
- 考虑在最大盈利的 50% 时平仓
- 如果需要,滚动未测试的一侧
- 由于未定义风险,仔细监控头寸规模

---

## 策略比较

| 策略 | 行权价 | 权利金 | 盈利区间 | 最佳用于 |
|----------|---------|---------|-------------|----------|
| Long Straddle | 相同 | 成本较高 | 宽(任何大幅波动) | 最大波动率交易 |
| Long Strangle | 不同 | 成本较低 | 更宽的盈亏平衡点 | 成本更低的波动率 |
| Short Straddle | 相同 | 信用较高 | 窄(在行权价) | 最大收益,低波动率 |
| Short Strangle | 不同 | 信用较低 | 更宽的区间 | 更安全的收益,中等波动率 |

## Greeks 考虑

#### 对于 Long Straddles/Strangles
- **正 Vega** - 从波动率增加中受益
- **负 Theta** - 时间衰减对您不利
- **交易**: 在 IV 低时买入,在 IV 飙升时卖出

#### 对于 Short Straddles/Strangles
- **负 Vega** - 受波动率增加伤害
- **正 Theta** - 时间衰减对您有利
- **交易**: 在 IV 高时卖出,从 IV 挤压中受益

## 示例: IV 过滤

```python
# 针对 short strangles 的高 IV 环境
results = op.short_strangles(
    data,
    max_entry_dte=45,
    exit_dte=21,
    max_otm_pct=0.25,
    # 过滤流动、高 IV 期权
    min_bid_ask=0.15,
    slippage='liquidity'
)
```

## 风险管理

**对于 Long 头寸:**
- 风险限于支付的权利金
- 考虑在 100% 损失或 200%+ 收益时退出
- 大幅波动时利润可能相当可观

**对于 Short 头寸:**
- ⚠️ 风险是无限的
- 考虑止损或转换为 iron condors/butterflies
- 在最大盈利的 50-75% 时提前平仓
- 保守地确定头寸规模(账户的小百分比)

## 下一步

- 了解 [垂直价差](spreads.md) 以获得有限风险的替代方案
- 探索 [Iron Butterflies](iron-strategies.md) 以获得有限风险的波动率交易
- 查看包含 IV 分析的更多 [示例](../examples.md)
