# Optopsy

一个快速、灵活的 Python 期权策略回测库。

## 什么是 Optopsy？

Optopsy 帮助您回答诸如"铁秃鹰策略在 SPX 上的表现如何？"或"哪个 delta 范围为备兑看涨期权产生最佳结果？"等问题，通过从历史期权数据生成全面的绩效统计。

## 主要特性

- **28 种内置策略** - 从简单的看涨/看跌期权到铁秃鹰、蝶式、日历和对角价差
- **希腊字母过滤** - 按 delta 过滤期权以针对特定概率范围
- **滑点建模** - 使用中间价、价差或基于流动性的滑点进行真实填充
- **灵活分组** - 按 DTE、OTM% 和 delta 区间分析结果
- **任何数据源** - 适用于 CSV 或 DataFrame 格式的任何期权数据
- **原生 Pandas** - 返回与现有工作流程集成的 DataFrames

## 快速示例

```python
import optopsy as op

# 加载您的期权数据
data = op.csv_data('SPX_options.csv')

# 回测铁秃鹰策略
results = op.iron_condor(
    data,
    max_entry_dte=45,
    exit_dte=21,
    max_otm_pct=0.25
)

print(results)
```

## 安装

```bash
pip install optopsy
```

**要求：** Python 3.8+、Pandas 2.0+、NumPy 1.26+

## 获取帮助

- 查看[入门指南](getting-started.md)获取详细演练
- 浏览[策略](strategies.md)了解可用的期权策略
- 查看[参数](parameters.md)了解配置选项
- 参阅[示例](examples.md)了解常见用例
- 查看 [API 参考](api-reference.md)获取完整的函数文档

## 贡献

欢迎贡献！有关详细信息，请参阅[贡献指南](contributing.md)。

## 许可证

Optopsy 根据 GPL-3.0 许可证发布。有关更多信息，请参阅 [GitHub 仓库](https://github.com/michaelchu/optopsy)。
