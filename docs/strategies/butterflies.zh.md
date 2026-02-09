# 蝶式价差

蝶式价差是三腿策略,旨在当标的资产保持在特定价格附近时获利。它们提供有限风险和有限回报,市场观点中性。

## Long Call Butterfly

#### 描述
当标的资产在到期时保持在中间行权价时获利。

**组成:**
- Long 1 个 call,行权价为较低(翼)
- Short 2 个 calls,行权价为中间(身体)
- Long 1 个 call,行权价为较高(翼)

#### 示例
```python
import optopsy as op
results = op.long_call_butterfly(data, max_entry_dte=45, exit_dte=21)
```

---

## Short Call Butterfly

#### 描述
当标的资产在任一方向偏离中间行权价时获利。

**组成:**
- Short 1 个 call,行权价为较低
- Long 2 个 calls,行权价为中间
- Short 1 个 call,行权价为较高

#### 示例
```python
results = op.short_call_butterfly(data, max_entry_dte=30, exit_dte=7)
```

---

## Long Put Butterfly

#### 描述
类似于 long call butterfly,但使用 puts。在中间行权价获利。

**组成:**
- Long 1 个 put,行权价为较低(翼)
- Short 2 个 puts,行权价为中间(身体)
- Long 1 个 put,行权价为较高(翼)

#### 示例
```python
results = op.long_put_butterfly(data, max_entry_dte=45, exit_dte=21)
```

---

## Short Put Butterfly

#### 描述
当标的资产大幅偏离中间行权价时获利。

**组成:**
- Short 1 个 put,行权价为较低
- Long 2 个 puts,行权价为中间
- Short 1 个 put,行权价为较高

#### 示例
```python
results = op.short_put_butterfly(data, max_entry_dte=30, exit_dte=7)
```

---

## 关键特征

- **等宽翼**: 翼与身体等距
- **低成本**: 通常以小额借记甚至信用进场
- **有限风险**: 最大损失限于支付的借记
- **高精度**: 在中间行权价周围的窄范围内获利
