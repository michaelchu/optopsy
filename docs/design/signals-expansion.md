# Design: Expand Signals to Support All pandas-ta-classic Indicators

## Context

Optopsy recently migrated to `pandas-ta-classic` (PR #184) but only uses 6 of its 157 indicators (RSI, SMA, EMA, MACD, Bollinger Bands, ATR). This plan adds support for all practically useful indicators as entry/exit signals for options backtesting.

## Current State

- **14 signal types** in `optopsy/signals.py` (1,039 lines)
- Pattern: factory functions return `SignalFunc = Callable[[DataFrame], Series[bool]]`
- Two core helpers: `_per_symbol_signal()` (threshold), `_crossover_signal()` (crossover)
- UI registry in `optopsy/ui/tools/_schemas.py` with `SIGNAL_REGISTRY`

---

## Step 1: Convert `signals.py` to `signals/` Package

Split the monolithic file into submodules for maintainability:

```
optopsy/signals/
    __init__.py          # Re-exports all public names (backward compat)
    _helpers.py          # _groupby_symbol, _per_symbol_signal, _crossover_signal, SignalFunc
    _combinators.py      # and_signals, or_signals, sustained, Signal, signal, apply_signal, custom_signal
    momentum.py          # RSI, MACD + new momentum indicators
    overlap.py           # SMA, EMA crossovers + new MA crossovers
    volatility.py        # ATR, Bollinger Bands + new volatility indicators
    trend.py             # New: ADX, Aroon, Supertrend, PSAR, etc.
    volume.py            # New: MFI, OBV, CMF, etc.
    iv.py                # IV Rank (existing)
    calendar_signal.py   # day_of_week (existing)
```

`__init__.py` re-exports every public name so `from optopsy.signals import rsi_below` continues to work. Delete old `signals.py` in the same commit.

---

## Step 2: Add New Helper Patterns to `_helpers.py`

Beyond existing `_per_symbol_signal` and `_crossover_signal`, add:

- **`_ohlcv_signal(indicator_fn, compare_fn)`** — like `_per_symbol_signal` but passes full OHLCV group DataFrame instead of just close prices. For indicators needing high/low/volume columns. Falls back to False when required columns are missing.
- **`_band_signal(compute_bands_fn, above)`** — generalized version of the BB signal pattern. Price above upper band or below lower band. For Keltner, Donchian, etc.
- **`_direction_signal(compute_fn, buy)`** — detects direction transitions (e.g., Supertrend flip, PSAR flip). Fires on the bar where direction changes.

---

## Step 3: Implement New Indicators (64 new signal functions)

### Phase 1 — High Priority (24 signals)

Most useful for options trading entry/exit timing.

| Module | Indicator | Functions | Data Needed |
|--------|-----------|-----------|-------------|
| `momentum.py` | Stochastic | `stoch_above`, `stoch_below` | OHLC |
| `momentum.py` | StochRSI | `stochrsi_above`, `stochrsi_below` | close |
| `momentum.py` | Williams %R | `willr_above`, `willr_below` | OHLC |
| `momentum.py` | CCI | `cci_above`, `cci_below` | OHLC |
| `momentum.py` | ROC | `roc_above`, `roc_below` | close |
| `momentum.py` | PPO | `ppo_cross_above`, `ppo_cross_below` | close |
| `volatility.py` | Keltner Channel | `kc_above_upper`, `kc_below_lower` | OHLC |
| `volatility.py` | Donchian | `donchian_above_upper`, `donchian_below_lower` | OHLC |
| `volatility.py` | NATR | `natr_above`, `natr_below` | OHLC |
| `trend.py` | ADX | `adx_above`, `adx_below` | OHLC |
| `trend.py` | Aroon | `aroon_cross_above`, `aroon_cross_below` | OHLC |
| `volume.py` | MFI | `mfi_above`, `mfi_below` | OHLCV |

### Phase 2 — Medium Priority (22 signals)

Useful for more sophisticated setups.

| Module | Indicator | Functions | Data Needed |
|--------|-----------|-----------|-------------|
| `momentum.py` | TSI | `tsi_cross_above`, `tsi_cross_below` | close |
| `momentum.py` | CMO | `cmo_above`, `cmo_below` | close |
| `momentum.py` | UO | `uo_above`, `uo_below` | OHLC |
| `momentum.py` | Squeeze | `squeeze_on`, `squeeze_off` | OHLC |
| `momentum.py` | Awesome Oscillator | `ao_above`, `ao_below` | OHLC |
| `overlap.py` | DEMA crossover | `dema_cross_above`, `dema_cross_below` | close |
| `overlap.py` | TEMA crossover | `tema_cross_above`, `tema_cross_below` | close |
| `overlap.py` | HMA crossover | `hma_cross_above`, `hma_cross_below` | close |
| `overlap.py` | KAMA crossover | `kama_cross_above`, `kama_cross_below` | close |
| `trend.py` | Supertrend | `supertrend_buy`, `supertrend_sell` | OHLC |
| `trend.py` | PSAR | `psar_buy`, `psar_sell` | OHLC |

### Phase 3 — Lower Priority (18 signals)

Niche / advanced indicators.

| Module | Indicator | Functions |
|--------|-----------|-----------|
| `momentum.py` | SMI | `smi_cross_above`, `smi_cross_below` |
| `momentum.py` | KST | `kst_cross_above`, `kst_cross_below` |
| `momentum.py` | Fisher Transform | `fisher_cross_above`, `fisher_cross_below` |
| `overlap.py` | WMA crossover | `wma_cross_above`, `wma_cross_below` |
| `overlap.py` | ZLMA crossover | `zlma_cross_above`, `zlma_cross_below` |
| `overlap.py` | ALMA crossover | `alma_cross_above`, `alma_cross_below` |
| `volatility.py` | Mass Index | `massi_above`, `massi_below` |
| `trend.py` | Choppiness | `chop_above`, `chop_below` |
| `trend.py` | VHF | `vhf_above`, `vhf_below` |
| `volume.py` | OBV | `obv_cross_above_sma`, `obv_cross_below_sma` |
| `volume.py` | CMF | `cmf_above`, `cmf_below` |
| `volume.py` | AD | `ad_cross_above_sma`, `ad_cross_below_sma` |
| `candle` | Doji / Inside | `cdl_doji`, `cdl_inside` |

### Excluded Indicators

Not useful as entry/exit signals:

- **Data transforms:** `hl2`, `hlc3`, `ohlc4`, `ha`, `wcp`, `midpoint`, `midprice`
- **Performance metrics:** `drawdown`, `log_return`, `percent_return`
- **Statistical tools:** `entropy`, `kurtosis`, `stdev`, `zscore`, `mad`, `median`, `quantile`, `skew`, `variance`, `tos_stdevall`
- **Redundant MAs:** `rma`, `smma`, `ssf`, `ssf3`, `pwma`, `fwma`, `hwma`, `sinwma`, `swma`, `t3`, `vidya`
- **Niche:** `aberration`, `accbands`, `atrts`, `hwc`, `pdist`, `decay`, `zigzag`, `rwi`, `cksp`, `thermo`, `ui`
- **Volume variants:** `vp`, `pvol`, `pvr`, `pvt`, `nvi`, `pvi`, `tsv`, `aobv`, `vwma`
- **Cycles:** `ebsw`, `reflex`

---

## Step 4: Update UI Integration

### `optopsy/ui/tools/_schemas.py`

- Add all new signals to `SIGNAL_REGISTRY` with sensible default parameters
- Add `_OHLC_SIGNALS` frozenset for signals needing high/low columns
- Add `_VOLUME_SIGNALS` frozenset for signals needing volume column
- `SIGNAL_NAMES` rebuilds automatically from the registry

### `optopsy/ui/tools/_signals_builder.py`

- Update data requirement detection to check `_OHLC_SIGNALS` / `_VOLUME_SIGNALS`
- Existing `_fetch_stock_data_for_signals` already fetches OHLCV — no changes needed there

### `optopsy/ui/tools/_models.py`

- Update `SignalMixin.entry_signal` field description to list new signal names grouped by category

### `optopsy/__init__.py`

- Add all new public signal functions to imports and `__all__`

---

## Step 5: Tests

Split `tests/test_signals.py` (2,085 lines) into a test subpackage:

```
tests/signals/
    __init__.py
    conftest.py              # Shared fixtures: price_data, ohlcv_data, multi_symbol_data
    test_helpers.py          # _groupby_symbol, _per_symbol_signal
    test_combinators.py      # and_signals, or_signals, sustained, Signal, apply_signal
    test_momentum.py         # All momentum signals
    test_overlap.py          # All overlap/MA signals
    test_volatility.py       # ATR, BB, KC, Donchian, etc.
    test_trend.py            # ADX, Aroon, Supertrend, PSAR
    test_volume.py           # MFI, OBV, CMF, AD
    test_iv.py               # IV Rank
    test_calendar_signal.py  # day_of_week
    test_backward_compat.py  # Verify all old import paths still work
```

Each signal gets at minimum:

1. **Type/shape test** — result is `pd.Series[bool]`, same length as input
2. **Directional test** — known trend produces expected signal
3. **Empty data test** — empty DataFrame returns all-False Series
4. **Multi-symbol test** — each symbol computed independently
5. **Insufficient data test** — not enough bars for warmup returns all-False

New `conftest.py` fixtures for OHLCV data with realistic high/low/volume columns.

---

## Step 6: Documentation

Update `docs/entry-signals.md` with new indicator categories and usage examples.

---

## Verification

```bash
# Full test suite (no regressions)
uv run pytest tests/ -v

# Signal tests specifically
uv run pytest tests/signals/ -v

# Backward compat
uv run pytest tests/signals/test_backward_compat.py -v

# Lint + format
uv run ruff check optopsy/ tests/
uv run ruff format --check optopsy/ tests/

# Type check
uv run ty check optopsy/
```

---

## Files to Modify / Create

| File | Action |
|------|--------|
| `optopsy/signals.py` | Delete (replaced by package) |
| `optopsy/signals/__init__.py` | Create (re-exports) |
| `optopsy/signals/_helpers.py` | Create (shared helpers) |
| `optopsy/signals/_combinators.py` | Create (Signal class, combinators) |
| `optopsy/signals/momentum.py` | Create |
| `optopsy/signals/overlap.py` | Create |
| `optopsy/signals/volatility.py` | Create |
| `optopsy/signals/trend.py` | Create |
| `optopsy/signals/volume.py` | Create |
| `optopsy/signals/iv.py` | Create |
| `optopsy/signals/calendar_signal.py` | Create |
| `optopsy/__init__.py` | Update exports |
| `optopsy/ui/tools/_schemas.py` | Update registry + signal sets |
| `optopsy/ui/tools/_models.py` | Update descriptions |
| `tests/test_signals.py` | Delete (replaced by package) |
| `tests/signals/` | Create (split test modules) |
| `docs/entry-signals.md` | Update |
