# Options Strategy Optimization — Reference Document

## Overview

Options strategy optimization is a systematic, data-driven process for improving the performance of options trading strategies. The core idea is to start with a base backtested strategy, then intelligently layer entry/exit timing signals from a library of proprietary and technical indicators. Statistical validation (p-values, permutation analysis) is used to ensure that observed improvements represent genuine edge rather than curve-fitting to historical noise.

This document describes the full end-to-end workflow from base strategy creation through optimization, validation, and deployment.

---

## End-to-End Workflow

### Step 1: Define a Base Strategy via Backtesting

Before optimization begins, a base options strategy backtest is created or selected. This establishes the unoptimized baseline performance — the strategy's returns when traded mechanically without any timing signals.

#### Strategy Types

Common strategy types (~25 total) fall into three categories:

- **Bullish:** Long calls, short puts, bull call spreads, bull put spreads, covered calls, etc.
- **Bearish:** Long puts, short calls, bear call spreads, bear put spreads, etc.
- **Neutral:** Iron condors, butterflies, straddles, strangles, calendars, collars, etc.

#### Key Entry Parameters

- **Days to Expiration (DTE):** Target DTE with an acceptable range (e.g., target 40 days, acceptable range 30–50). The backtester selects the closest available option within range. Strategies can be tested across a wide DTE spectrum from 2 to 300+ days.
- **Strike Delta:** Target delta with an acceptable range (e.g., target 0.65, range 0.55–0.75). Tests should span both in-the-money and out-of-the-money strikes.
- **Spread Yield %:** The option trade price relative to the stock price, calculated as `option_entry_price / stock_price`. Categorized as low, moderate, or high relative to comparable backtests with similar DTE and delta. This parameter interacts meaningfully with volatility regime — for example, short put spreads in low-VIX environments tend to perform better with low spread yield targets.
- **Spread Price:** Absolute price filter for the total spread cost.
- **Spread Delta:** Net delta of the multi-leg position, calculated as `leg1_ratio × leg1_delta + leg2_ratio × leg2_delta`.
- **Entry Frequency (Stagger Days):** How often new trades can be initiated (e.g., every 7 days). Setting to 1 (potentially entering every day) reduces path dependency in the results.
- **Expiration Type:** All expirations, weeklies only, or monthlies only.

#### Key Exit Parameters

- **Exit DTE:** Close when remaining days to expiration falls to a threshold. Set to "expire" to hold through expiration.
- **Profit/Loss Targets:** Stop loss and profit target as a percentage of entry price (e.g., -50% stop loss, +200% profit target).
- **Exit Spread Delta:** Close when the position's net delta exceeds specified bounds.
- **Exit Hold Days:** Close after a fixed number of days held.
- **Exit Strike Diff %:** Close based on `trade_price / strike_width` ratio crossing bounds.
- **Exit Leg Triggers:** Close based on individual leg delta or OTM% reaching thresholds.

#### Slippage and Commission Modeling

Realistic backtesting requires accounting for execution costs:

- **Slippage formula (buy):** `Bid + (Ask - Bid) × slippage%`
- **Slippage formula (sell):** `Ask - (Ask - Bid) × slippage%`
- A typical default is 75% bid-ask travel for single-leg trades. Multi-leg trades use lower slippage per leg (e.g., a 4-leg spread might use ~56%) since each additional leg compounds the difficulty of simultaneous execution.
- Daily mark-to-market uses mid-point prices.
- Actual historical bid-ask prices should be used for entry/exit simulation.

#### Return Calculation

- **Arithmetic returns** are preferred over geometric to avoid path dependency and to handle scenarios where more than 100% of a strategy's capital is lost.
- **Notional returns:** Normalized by the underlying's price. Best for comparing disparate strategies on a common basis.
- **Margin returns:** Based on brokerage margin requirements. These vary significantly between portfolio margin and cash (Reg-T) accounts and can be misleading if not interpreted carefully.
- Annualization can use either average or compound daily returns.

#### Backtester Execution Loop

1. Scan for entry from start date using all entry parameters.
2. Find options closest to target DTE and delta within acceptable ranges.
3. Simulate entry using historical bid-ask prices with slippage.
4. Each day, calculate option returns and check all exit conditions.
5. On exit, scan for new entry immediately. Repeat until the backtest end date.
6. If the strategy includes a stock component (overlay or married), incorporate stock daily returns.
7. If multiple weighted symbols are used, calculate weighted returns last.

---

### Step 2: Weighted Scoring of Backtest Permutations

Running multiple parameter variations (different DTEs, deltas, spread yields, exit thresholds) produces many backtests. A scoring system ranks them according to user-defined objectives.

#### How Scoring Works

Each return statistic from each backtest receives a user-defined weight. The weighted composite score determines the ranking.

**Example:** A user values both high annual return and low worst-year drawdown. A strategy returning 8.55% annually with a -18.95% worst year scores *lower* than one returning 6.59% with a -5.56% worst year, because the drawdown penalty outweighs the return benefit under the chosen weights.

#### Key Performance Metrics Available for Weighting

- Annual return (average or compound)
- Maximum drawdown
- Worst year return
- Sortino ratio
- Sharpe ratio
- Win rate
- Best/worst month returns
- Profit factor
- % of time in market
- Average profit per day

The top-scoring base strategy is selected as the candidate for indicator optimization in the next step.

---

### Step 3: Indicator Optimization (Timing Triggers)

This is the core value-add of the optimization process. The goal is to determine whether adding entry/exit timing signals — conditions that must be met before a trade is initiated or exited — can improve the base strategy's risk-adjusted returns.

#### Indicator Library

A comprehensive indicator library might include:

- **Proprietary volatility indicators (~100):** IV rank, IV percentile, term structure slope, skew parameters, implied vs. historical vol spread, earnings implied move, forecast indicators, and their moving averages.
- **Volatility forecasts:** Forecasted 20-day realized volatility, forecasted 20-day IV, forecasted earnings effect. These are derived from historical patterns, sector/index signals, and current IV surface information. Forecast confidence can be measured by R-squared.
- **Standard technical indicators:** SMA (50-day, 200-day), RSI, MACD, Bollinger Bands, etc.
- **Market-level indicators:** VIX price levels, VIX term structure, broad market SMA positioning.
- **Custom ratio indicators:** User-defined ratios between any two indicators.
- **Cross-symbol indicators:** Indicators measured on a different symbol than the one being traded (e.g., using VIX readings or sector ETF volatility as entry triggers for individual stock strategies).

Each indicator also has moving average variants, dramatically expanding the search space.

#### How Timing Triggers Work

Each trigger specifies:
- An indicator to evaluate
- A min and max threshold
- Whether it applies to entry, exit, or both
- Which symbol to measure the indicator on

A trade enters only if **all** entry indicator readings for the day fall within their respective min/max ranges. Similarly, exit triggers fire when readings fall outside bounds.

Multiple entry and exit triggers can be stacked.

#### The Computational Challenge

The combinatorial space is enormous: hundreds of indicators × their moving averages × threshold ranges × entry vs. exit application. Running a full backtest for every combination would be computationally prohibitive.

#### Two-Phase Search: Simulation Then Confirmation

The optimization uses a **coarse-to-fine search strategy:**

1. **Simulation phase (fast, approximate):** Techniques are used to simulate backtest outcomes without running the full backtesting loop for each indicator combination. This rapidly screens the indicator space and identifies promising candidates.

2. **Full backtest confirmation (slow, precise):** Only the most promising indicator combinations from the simulation phase are run through the complete backtester with actual historical bid-ask prices, slippage, and all entry/exit logic. This confirms whether the simulated improvement holds up under realistic conditions.

This two-phase approach is analogous to a broad grid search followed by fine-grained optimization — a common pattern when the objective function is expensive to evaluate.

---

### Step 4: Statistical Validation (Anti-Curve-Fitting)

This is the most critical step. When testing hundreds or thousands of indicator combinations against historical data, some will inevitably appear to improve performance purely by chance. Without statistical validation, the optimizer would systematically produce overfit strategies that look great historically but fail in live trading.

#### The Overfitting Problem

If you test 1,000 random indicator thresholds, roughly 50 will appear "significant" at the 5% level by pure chance. The more indicators tested, the more spurious improvements will be found. This is the multiple comparisons problem.

#### P-Value Calculation

The optimizer calculates p-values for each optimized strategy to quantify the probability that the observed improvement over the base strategy occurred by chance.

- **Low p-value** (e.g., < 0.05): The improvement is unlikely to be random — the indicator likely captures genuine market structure.
- **High p-value** (e.g., > 0.20): The improvement could easily be noise. The indicator should not be trusted.

#### Permutation Analysis

Permutation testing is used to establish the null distribution:

1. Take the base strategy's trade entries.
2. Randomly shuffle which days trades are taken (or which indicator readings are paired with which outcomes).
3. Re-calculate performance metrics under this randomized assignment.
4. Repeat many times to build a distribution of "improvement by chance."
5. Compare the actual optimized strategy's improvement against this null distribution.

If the real improvement exceeds 95% (or 99%) of the permuted improvements, the result is considered statistically significant.

#### The "Find Backtests" Cross-Check

An additional overfitting safeguard: after creating a custom backtest, compare its performance against the distribution of all pre-compiled backtests with similar parameters. If the custom backtest's performance is an outlier relative to nearby parameter configurations, it may be overfit to a specific parameter combination rather than capturing a robust pattern.

#### Practical Significance Thresholds

For curated/production strategies, aim for:
- Low p-values for statistical significance
- Optimal average profit per day (economic significance)
- Consistent performance across different market regimes
- Robustness to small parameter changes

---

### Step 5: Paper Trading Validation

After statistical validation, the optimized strategy should be paper traded before live deployment:

1. **Paper trade with realistic fills:** Simulate execution with real-time pricing and slippage. Note that paper trading fills tend to be slightly more optimistic than live execution.
2. **Track for a meaningful period:** At minimum 12 weeks, ideally capturing different market conditions.
3. **Compare to backtest expectations:** If paper trading results diverge significantly from backtested performance, investigate whether market regime has shifted or the strategy was overfit.
4. **Gradually scale:** Start with small size and increase as confidence builds.

---

### Step 6: Deployment as Live Trade Signals

Once validated, the optimized strategy runs as a continuous scanner:

- The system monitors the strategy's entry indicator conditions in real-time.
- When all conditions are met, it identifies the best available trade opportunity based on probability of profit and risk/reward.
- Results update throughout the trading day as market conditions evolve.
- Greeks, theoretical edge, and probability of profit (POP%) are calculated for each candidate trade.

The strategy's exit conditions are also monitored continuously, with alerts when exit triggers fire.

---

## Key Concepts and Definitions

### Smooth Market Volatility (SMV)

High-quality backtesting requires accurate theoretical values. The SMV process:

1. Calculates implied volatilities from options bid-ask quotes using appropriate interest rates and dividend yields.
2. Aligns call and put IVs using a residual yield derived from put-call parity.
3. Fits a non-arbitrageable smooth curve through strike implied volatilities using bounded flexible spline bands.
4. Eliminates calendar and butterfly arbitrage.
5. Produces theoretical values and accurate Greeks (delta, vega, theta, rho, phi).

For thinly traded securities, historical information is incorporated when current market confidence is low, producing more realistic IVs than raw bid-ask derived values.

### Theoretical Edge

The percentage difference between a smoothed theoretical value and the option's market mid-point: `(theoretical_value - mid_price) / mid_price`. Positive values suggest the option is underpriced; negative values suggest overpricing.

### Volatility Forecasting

Forward-looking volatility predictions combine:

- Current IV surface information
- Historical volatility patterns
- Sector and broad market volatility signals
- Earnings effect decomposition (implied vs. forecasted earnings moves)

Forecast confidence is measured by R-squared (fcstR²). Higher R² = more reliable forecast. Position sizing should reflect forecast confidence.

### Earnings Handling

Strategies can be configured with:

- **Entry date triggers:** Enter N days before/after earnings announcement.
- **Exit date triggers:** Exit N days before/after earnings.
- **Earnings effect indicators:** Compare market-implied earnings move to historically forecasted earnings effect to identify mispriced earnings volatility.

---

## Anti-Overfitting Checklist

When evaluating an optimized strategy, verify:

1. **P-value is low** (< 0.05, ideally < 0.01).
2. **Improvement is economically meaningful**, not just statistically significant. A 0.1% annual return improvement with a p-value of 0.01 is real but worthless.
3. **Performance is consistent** across different time periods within the backtest (no single year driving all the returns).
4. **Nearby parameters produce similar results.** If changing the indicator threshold by 5% destroys the edge, the strategy is likely overfit.
5. **The indicator has a plausible economic rationale.** Can you explain *why* this signal should predict better entry timing?
6. **Paper trading confirms** backtested expectations within a reasonable tolerance.
7. **The strategy trades frequently enough** to be statistically meaningful. A strategy with 10 trades over 15 years cannot be validated regardless of p-value.

---

## Computational Architecture Notes

- The backtesting engine needs to handle parallel execution of thousands of permutations efficiently.
- The simulation-before-full-backtest pattern is essential for keeping optimization tractable. Without it, testing N indicators × M threshold combinations × K strategies requires N×M×K full backtests.
- Historical data requirements: daily options bid-ask quotes, Greeks, underlying prices, earnings dates, and indicator values from 2007+ (or as far back as available).
- Indicator values and their moving averages should be pre-computed and stored for rapid lookup during the simulation phase.
