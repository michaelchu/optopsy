# Iron Condors & Iron Butterflies

四腿策略,结合信用价差以创建有限风险、有限回报的头寸。这些是中性至区间震荡市场的热门收益策略。

## Iron Condor

#### 描述
Iron condor 结合 bull put spread 和 bear call spread,创建一个宽盈利区间。这是最受欢迎的信用策略之一。

**组成:**
- Long 1 个 put,行权价为 A(保护)
- Short 1 个 put,行权价为 B(收益)
- Short 1 个 call,行权价为 C(收益)
- Long 1 个 call,行权价为 D(保护)

其中: A < B < C < D

#### 市场观点
- **中性** - 预期标的资产保持在空头行权价之间
- 如果价格在到期时保持在区间内则获利
- 适合低波动率、区间震荡市场

#### 盈亏
- **最大盈利**: 收到的净信用
- **最大损失**: 价差宽度 - 净信用
- **盈亏平衡点**: Short put 行权价 - 净信用, Short call 行权价 + 净信用

#### 示例

```python
import optopsy as op

data = op.csv_data('SPX_options.csv')

# 回测 iron condors
results = op.iron_condor(
    data,
    max_entry_dte=45,
    exit_dte=21,
    max_otm_pct=0.30,  # 宽翼以提高概率
    min_bid_ask=0.10
)

print(results)
```

#### 使用场景
- 在区间震荡市场中创收
- 高 IV 事件后(财报后 IV 挤压)
- 当您预期低波动率时
- 每月收益策略(45 DTE 进场,21 DTE 出场)

### 管理指南
- **止盈**: 在最大盈利的 50% 时平仓
- **止损**: 在收到信用的 200% 或 21 DTE 时平仓
- **滚动**: 如果受到挑战,滚动未测试的一侧
- **盈利区间**: 通常 60-70% 的盈利概率

---

## Reverse Iron Condor

#### 描述
Iron condor 的相反 - 该策略从任一方向的大幅价格波动中获利,同时定义风险。

**组成:**
- Short 1 个 put,行权价为 A
- Long 1 个 put,行权价为 B
- Long 1 个 call,行权价为 C
- Short 1 个 call,行权价为 D

其中: A < B < C < D

#### 市场观点
- **预期高波动率** - 预期任一方向的突破
- 如果价格大幅超出内侧行权价则获利
- Long straddles 的有限风险替代方案

#### 盈亏
- **最大盈利**: 价差宽度 - 净借记
- **最大损失**: 支付的净借记
- **盈亏平衡点**: Long put 行权价 + 借记, Long call 行权价 - 借记

#### 示例

```python
results = op.reverse_iron_condor(
    data,
    max_entry_dte=30,
    exit_dte=0,
    max_otm_pct=0.25  # 为突破移动设置
)
```

#### 使用场景
- 在预期大幅波动的重大事件之前
- 有限风险的波动率交易
- 当您预期突破但想要有限损失时

---

## Iron Butterfly

#### 描述
Iron butterfly 类似于 iron condor,但空头行权价在相同价格(ATM),创建更紧的盈利区间和更高的潜在盈利。

**组成:**
- Long 1 个 put,行权价为 A(翼)
- Short 1 个 put,行权价为 B(身体)
- Short 1 个 call,行权价为 B(身体) - **与 short put 相同**
- Long 1 个 call,行权价为 C(翼)

其中: A < B < C

#### 市场观点
- **非常中性** - 预期价格保持在当前水平或非常接近
- 如果价格在到期时恰好在中间行权价则最大盈利
- 比 iron condor 回报更高但盈利区间更窄

#### 盈亏
- **最大盈利**: 收到的净信用(大于 iron condor)
- **最大损失**: 翼宽度 - 净信用
- **盈亏平衡点**: Short 行权价 ± 净信用

#### 示例

```python
results = op.iron_butterfly(
    data,
    max_entry_dte=45,
    exit_dte=21,
    max_otm_pct=0.05,  # ATM 身体以获得最大信用
    min_bid_ask=0.15
)
```

#### 使用场景
- 预期价格锁定在特定水平
- 在具有高持仓量的主要行权价周围
- 当您想要比 iron condors 更高的信用时
- 比 iron condors 概率更低但回报更高

### Pin 风险
- 股票价格往往锁定在具有高持仓量的行权价
- Iron butterflies 从这种锁定效应中受益
- 仔细监控到期周的价格行为

---

## Reverse Iron Butterfly

#### 描述
Iron butterfly 的相反 - 从远离中心行权价的大幅波动中获利。

**组成:**
- Short 1 个 put,行权价为 A(翼)
- Long 1 个 put,行权价为 B(身体)
- Long 1 个 call,行权价为 B(身体) - **与 long put 相同**
- Short 1 个 call,行权价为 C(翼)

其中: A < B < C

#### 市场观点
- **高波动率** - 预期从当前价格大幅移动
- Long straddles 的有限风险替代方案
- 成本更低且最大损失有限

#### 盈亏
- **最大盈利**: 翼宽度 - 净借记
- **最大损失**: 支付的净借记
- **盈亏平衡点**: Long 行权价 ± 净借记

#### 示例

```python
results = op.reverse_iron_butterfly(
    data,
    max_entry_dte=30,
    exit_dte=7,
    max_otm_pct=0.10
)
```

#### 使用场景
- 在重大事件之前(财报、FDA 决定)
- 当您预期爆炸性波动时
- Long straddles/strangles 的有限风险替代方案

---

## 策略比较

| 策略 | 盈利区间 | 最大盈利 | 最大损失 | 最佳用于 |
|----------|-------------|-----------|----------|----------|
| Iron Condor | 宽区间 | 中等信用 | 有限 | 区间震荡收益 |
| Reverse IC | 区间外 | 有限 | 净借记 | 突破交易 |
| Iron Butterfly | 窄(在 ATM) | 更高信用 | 有限 | 锁定行权价 |
| Reverse Iron Butterfly | 远离 ATM | 有限 | 净借记 | 波动率爆发 |

## Iron Condor vs Iron Butterfly

**Iron Condor:**
- ✅ 更宽的盈利区间(60-70% 概率)
- ✅ 如果价格移动更宽容
- ❌ 收到的信用较低
- **使用时机**: 对区间有中等信心

**Iron Butterfly:**
- ✅ 更高的信用(2-3 倍)
- ❌ 更窄的盈利区间(40-50% 概率)
- ❌ 对价格移动不太宽容
- **使用时机**: 对锁定有高度信心

## 高级示例: Delta 中性 Iron Condors

```python
# 目标 delta 中性定位
results = op.iron_condor(
    data,
    max_entry_dte=45,
    exit_dte=21,
    # 空头行权价的目标特定 delta
    delta_min=0.15,  # ~15-20 delta 空头行权价
    delta_max=0.20,
    delta_interval=0.05,
    min_bid_ask=0.10,
    slippage='liquidity'
)
```

## 风险管理最佳实践

### 进场检查清单
- [ ] 45 DTE 或更少(最佳 theta 衰减)
- [ ] 信用 > 价差宽度的 1/3
- [ ] 盈利概率 > 60%
- [ ] 流动行权价(紧密的买卖价差)
- [ ] 确定的头寸规模(每笔交易 < 账户的 5%)

### 管理规则
1. **止盈**: 在最大盈利的 50% 时平仓(21 DTE)
2. **止损**: 在信用的 200-300% 或盈亏平衡时平仓
3. **滚动**: 如果早期受到挑战,向下/向上滚动未测试的一侧
4. **到期**: 避免持有至到期(pin 风险)

### 头寸规模
- 每笔交易风险不超过 2-5%
- Iron condors: 宽度决定每个合约的风险
- 示例: $5 宽价差收取 $2 信用 = 每个 IC 最大风险 $300

## Greeks 分析

### Iron Condor Greeks
- **Theta**: 正(时间衰减帮助您)
- **Vega**: 负(希望波动率降低)
- **Delta**: 接近零(中性头寸)
- **Gamma**: 负(如果价格移动,头寸对您不利)

**最佳条件:**
- 高 IV → 在 IV 升高时卖出
- 波动率降低 → IV 挤压有利于头寸
- 时间流逝 → Theta 衰减增加盈利

## 要避免的常见错误

1. **持有时间过长**: 在 50% 盈利时退出,不要贪心
2. **错误的 IV 环境**: 不要在 IV 低时卖出
3. **太窄**: 确保空头行权价之间有足够的缓冲
4. **忽略调整**: 如果价格威胁行权价,制定计划
5. **过度规模**: 尊重每个头寸的最大损失

## 下一步

- 了解 [蝶式价差](butterflies.md) 以获得三腿替代方案
- 探索 [日历价差](calendars.md) 以获得基于时间的策略
- 查看包含风险管理的更多 [示例](../examples.md)
- 查阅 [参数](../parameters.md) 进行优化
