# 垂直价差

垂直价差结合买入和卖出相同类型的期权(都是 calls 或都是 puts),行权价不同但到期日相同。这些策略提供有限风险和有限回报。

## Long Call Spread (Bull Call Spread) {#long-call-spread}

#### 描述
一种看涨策略,买入较低行权价的 call 并卖出较高行权价的 call,降低成本但限制上行空间。

**组成:**
- Long 1 个 call,行权价为较低的 X
- Short 1 个 call,行权价为较高的 Y

#### 示例
```python
import optopsy as op
results = op.long_call_spread(data, max_entry_dte=45, exit_dte=21)
```

---

## Short Call Spread (Bear Call Spread) {#short-call-spread}

#### 描述
一种看跌的信用策略,当标的资产保持在空头行权价以下时获利。

**组成:**
- Short 1 个 call,行权价为较低的 X
- Long 1 个 call,行权价为较高的 Y(保护)

#### 示例
```python
results = op.short_call_spread(data, max_entry_dte=45, exit_dte=21, max_otm_pct=0.20)
```

---

## Long Put Spread (Bear Put Spread) {#long-put-spread}

#### 描述
一种看跌策略,从向下移动中获利,风险有限。

**组成:**
- Short 1 个 put,行权价为较低的 X
- Long 1 个 put,行权价为较高的 Y

#### 示例
```python
results = op.long_put_spread(data, max_entry_dte=45, exit_dte=21)
```

---

## Short Put Spread (Bull Put Spread) {#short-put-spread}

#### 描述
一种看涨的信用策略,当标的资产保持在空头行权价以上时获利。

**组成:**
- Long 1 个 put,行权价为较低的 X(保护)
- Short 1 个 put,行权价为较高的 Y

#### 示例
```python
results = op.short_put_spread(data, max_entry_dte=45, exit_dte=21, max_otm_pct=0.25)
```

---

## 比较表

| 价差 | 方向 | 类型 | 最大盈利 | 最大损失 |
|--------|-----------|------|-----------|----------|
| Long Call | 看涨 | 借记 | 宽度 - 借记 | 支付的借记 |
| Short Call | 看跌 | 信用 | 信用 | 宽度 - 信用 |
| Long Put | 看跌 | 借记 | 宽度 - 借记 | 支付的借记 |
| Short Put | 看涨 | 信用 | 信用 | 宽度 - 信用 |
