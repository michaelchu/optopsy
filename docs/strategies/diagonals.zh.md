# 对角价差

对角价差结合了垂直价差和日历价差的元素,使用不同的行权价和不同的到期日。这些混合策略提供灵活的盈利区间和方向性偏向。

## Long Call Diagonal

#### 描述
买入一个长期 call,行权价为一个值,卖出一个短期 call,行权价为另一个值。结合时间衰减和方向性移动。

**组成:**
- Short 1 个前月 call
- Long 1 个后月 call
- 每个腿的行权价不同

#### 示例
```python
import optopsy as op

results = op.long_call_diagonal(
    data,
    front_dte_min=20,
    front_dte_max=40,
    back_dte_min=50,
    back_dte_max=90,
    exit_dte=7
)
```

#### 使用场景
- 看涨至中性偏向,带收益
- 比日历更灵活
- 可调整的方向性敞口

---

## Short Call Diagonal

#### 描述
Long call diagonal 的相反。买入近期,卖出长期,行权价不同。

**组成:**
- Long 1 个前月 call
- Short 1 个后月 call
- 每个腿的行权价不同

#### 示例
```python
results = op.short_call_diagonal(data)
```

---

## Long Put Diagonal

#### 描述
结构类似于 call diagonals,但使用 puts。允许看跌至中性定位。

**组成:**
- Short 1 个前月 put
- Long 1 个后月 put
- 每个腿的行权价不同

#### 示例
```python
results = op.long_put_diagonal(data)
```

---

## Short Put Diagonal

#### 描述
Long put diagonal 的相反,到期日相反。

**组成:**
- Long 1 个前月 put
- Short 1 个后月 put
- 每个腿的行权价不同

#### 示例
```python
results = op.short_put_diagonal(data)
```

---

## Diagonal vs Calendar

| 特征 | Calendar Spread | Diagonal Spread |
|---------|----------------|-----------------|
| 行权价 | 相同 | 不同 |
| 方向性 | 中性 | 可以有方向性 |
| 复杂性 | 简单 | 更复杂 |
| 灵活性 | 有限 | 高 |

## 参数

对角价差使用日历价差参数,但评估所有行权价组合:

```python
results = op.long_call_diagonal(
    data,
    front_dte_min=20,
    front_dte_max=40,
    back_dte_min=50,
    back_dte_max=90,
    max_otm_pct=0.30  # 更宽的行权价选择范围
)
```

## 策略技巧

- 从日历开始,随着市场移动调整行权价
- 同时监控时间衰减和方向性移动
- 比日历需要更多管理
- 可以转换为垂直价差或日历
