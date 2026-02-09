# 策略概览

Optopsy 包含 28 种内置期权策略,涵盖单腿、多腿和基于时间的策略。

## 策略分类

### 单腿策略 (4)
使用 call 或 put 的基本方向性交易。

- [Long Calls](strategies/singles.md#long-calls) - 看涨方向性押注
- [Short Calls](strategies/singles.md#short-calls) - 看跌或中性收益
- [Long Puts](strategies/singles.md#long-puts) - 看跌方向性押注
- [Short Puts](strategies/singles.md#short-puts) - 看涨收益策略

[了解更多 →](strategies/singles.md)

### Straddles & Strangles (4)
基于波动率的策略,结合 call 和 put。

- [Long Straddle](strategies/straddles-strangles.md#long-straddle) - 从大幅波动中获利
- [Short Straddle](strategies/straddles-strangles.md#short-straddle) - 从低波动率获得收益
- [Long Strangle](strategies/straddles-strangles.md#long-strangle) - 成本更低的波动率交易
- [Short Strangle](strategies/straddles-strangles.md#short-strangle) - 更宽的盈利区间收益

[了解更多 →](strategies/straddles-strangles.md)

### 垂直价差 (4)
有限风险的方向性策略。

- [Long Call Spread](strategies/spreads.md#long-call-spread) - 看涨借记价差
- [Short Call Spread](strategies/spreads.md#short-call-spread) - 看跌信用价差
- [Long Put Spread](strategies/spreads.md#long-put-spread) - 看跌借记价差
- [Short Put Spread](strategies/spreads.md#short-put-spread) - 看涨信用价差

[了解更多 →](strategies/spreads.md)

### 蝶式价差 (4)
针对特定价格区间的中性策略。

- [Long Call Butterfly](strategies/butterflies.md#long-call-butterfly) - 在中间行权价获利
- [Short Call Butterfly](strategies/butterflies.md#short-call-butterfly) - 从价格移动获利
- [Long Put Butterfly](strategies/butterflies.md#long-put-butterfly) - 看跌蝶式
- [Short Put Butterfly](strategies/butterflies.md#short-put-butterfly) - 反向 put 蝶式

[了解更多 →](strategies/butterflies.md)

### Iron 策略 (4)
具有确定风险的四腿策略。

- [Iron Condor](strategies/iron-strategies.md#iron-condor) - 区间震荡收益
- [Reverse Iron Condor](strategies/iron-strategies.md#reverse-iron-condor) - 突破交易
- [Iron Butterfly](strategies/iron-strategies.md#iron-butterfly) - 更紧的盈利区间
- [Reverse Iron Butterfly](strategies/iron-strategies.md#reverse-iron-butterfly) - Long 波动率

[了解更多 →](strategies/iron-strategies.md)

### 备兑策略 (2)
股票 + 期权组合(合成)。

- [Covered Call](strategies/covered.md#covered-call) - 持股收益
- [Protective Put](strategies/covered.md#protective-put) - 下行保护

[了解更多 →](strategies/covered.md)

### 日历价差 (4)
相同行权价,不同到期日。

- [Long Call Calendar](strategies/calendars.md#long-call-calendar) - 时间衰减交易
- [Short Call Calendar](strategies/calendars.md#short-call-calendar) - 反向日历
- [Long Put Calendar](strategies/calendars.md#long-put-calendar) - 看跌时间价差
- [Short Put Calendar](strategies/calendars.md#short-put-calendar) - 反向 put 日历

[了解更多 →](strategies/calendars.md)

### 对角价差 (4)
不同行权价和不同到期日。

- [Long Call Diagonal](strategies/diagonals.md#long-call-diagonal) - 混合价差
- [Short Call Diagonal](strategies/diagonals.md#short-call-diagonal) - 反向 call 对角
- [Long Put Diagonal](strategies/diagonals.md#long-put-diagonal) - 看跌对角
- [Short Put Diagonal](strategies/diagonals.md#short-put-diagonal) - 看涨对角

[了解更多 →](strategies/diagonals.md)

## 快速参考表

| 策略 | 腿数 | 市场观点 | 最大收益 | 最大损失 | 使用示例 |
|----------|------|-------------|-----------|----------|-------------|
| Long Call | 1 | 看涨 | 无限 | 支付的权利金 | 押注上涨 |
| Short Put | 1 | 看涨 | 收到的权利金 | 重大损失 | 创收 |
| Iron Condor | 4 | 中性 | 净信用 | 行权价差 | 区间震荡市场 |
| Long Straddle | 2 | 高波动率 | 无限 | 支付的权利金 | 财报前 |
| Call Butterfly | 3 | 中性 | 翼宽 | 净借记 | 锁定行权价 |
| Call Calendar | 2 | 中性 | 可变 | 净借记 | 时间衰减交易 |

## 策略选择指南

### 如果您认为市场将...

**大幅上涨**
- Long Calls
- Long Call Spread

**大幅下跌**
- Long Puts
- Long Put Spread

**保持平稳**
- Short Straddle
- Short Strangle
- Iron Condor
- Iron Butterfly

**波动但方向不确定**
- Long Straddle
- Long Strangle

**保持在当前价格附近**
- Calendar Spreads
- Butterflies

### 按风险/回报特征

**有限风险,有限回报**
- 所有价差(垂直、蝶式、iron condor)

**有限风险,无限回报**
- Long calls/puts
- Long straddles/strangles

**重大风险,有限回报**
- Short calls/puts
- Short straddles/strangles

## 通用参数

所有策略都接受这些通用参数:

- `max_entry_dte` - 进场时的最大 DTE
- `exit_dte` - 出场时的 DTE
- `dte_interval` - 结果分组间隔
- `max_otm_pct` - 最大虚值百分比
- `otm_pct_interval` - OTM% 分组间隔
- `min_bid_ask` - 最小买卖价差过滤器
- `raw` - 返回原始交易数据(默认:聚合统计)

查看 [参数指南](parameters.md) 获取完整详细信息。

## 下一步

- 深入了解特定 [策略分类](#策略分类)
- 了解 [策略参数](parameters.md)
- 查看真实回测的 [示例](examples.md)
- 查阅 [API 参考](api-reference.md) 了解函数签名
