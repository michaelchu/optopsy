# 备兑策略

备兑策略将股票头寸与期权结合,用于创收或下行保护。

!!! note "合成实现"
    Optopsy 使用深度实值 calls 作为合成股票头寸来模拟备兑策略,因为该库仅处理期权数据。

## Covered Call

#### 描述
通过对 long 股票头寸(或通过深度实值 call 的合成 long)卖出 calls 来创收。

**组成:**
- Long 标的资产(通过 long 深度实值 call 模拟)
- Short 1 个 call,行权价较高

#### 示例
```python
import optopsy as op
results = op.covered_call(data, max_entry_dte=45, exit_dte=21)
```

#### 使用场景
- 在持股上创收
- 愿意以更高价格卖出股票
- 中性至略微看涨的观点

---

## Protective Put (Married Put) {#protective-put}

#### 描述
通过对 long 股票头寸购买 puts 来购买下行保护。

**组成:**
- Long 标的资产(通过 long 深度实值 call 模拟)
- Long 1 个 put,行权价较低以提供保护

#### 示例
```python
results = op.protective_put(data, max_entry_dte=90, exit_dte=60)
```

#### 使用场景
- 对冲 long 股票头寸
- 在不确定期间的保护
- 投资组合保险
