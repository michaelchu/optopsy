# 日历价差

日历价差(也称为时间价差或水平价差)使用相同行权价但不同到期日的期权。它们从时间衰减差异和隐含波动率变化中获利。

## Long Call Calendar

#### 描述
卖出近期 call 并买入长期 call,行权价相同。从时间衰减和后月波动率扩张中获利。

**组成:**
- Short 1 个前月 call(接近到期)
- Long 1 个后月 call(更长到期)
- 两者行权价相同

#### 示例
```python
import optopsy as op

results = op.long_call_calendar(
    data,
    front_dte_min=20,
    front_dte_max=40,
    back_dte_min=50,
    back_dte_max=90,
    exit_dte=7  # 在前月到期前 7 天退出
)
```

#### 使用场景
- 在行权价附近的中性市场
- 预期波动率增加
- 时间衰减交易

---

## Short Call Calendar

#### 描述
买入近期 call,卖出长期 call。从远离行权价的大幅移动中获利。

**组成:**
- Long 1 个前月 call
- Short 1 个后月 call
- 两者行权价相同

#### 示例
```python
results = op.short_call_calendar(
    data,
    front_dte_min=20,
    front_dte_max=40,
    back_dte_min=50,
    back_dte_max=90
)
```

---

## Long Put Calendar

#### 描述
类似于 long call calendar,但使用 puts。从行权价处的中性价格行为中获利。

**组成:**
- Short 1 个前月 put
- Long 1 个后月 put
- 两者行权价相同

#### 示例
```python
results = op.long_put_calendar(data)
```

---

## Short Put Calendar

#### 描述
Long put calendar 的相反。从远离行权价的移动中获利。

**组成:**
- Long 1 个前月 put
- Short 1 个后月 put
- 两者行权价相同

#### 示例
```python
results = op.short_put_calendar(data)
```

---

## 关键参数

日历价差使用不同的默认参数:

```python
calendar_default_kwargs = {
    "front_dte_min": 20,      # 前月腿的最小 DTE
    "front_dte_max": 40,      # 前月腿的最大 DTE
    "back_dte_min": 50,       # 后月腿的最小 DTE
    "back_dte_max": 90,       # 后月腿的最大 DTE
    "exit_dte": 7,            # 在前月到期前 7 天退出
    "dte_interval": 7,
    "otm_pct_interval": 0.05,
    "max_otm_pct": 0.5,
}
```

## 最佳实践

- 在前月腿到期前退出以避免分配
- 目标行权价接近当前价格
- 监控到期日之间的波动率倾斜
- 考虑后月的 IV 变化
