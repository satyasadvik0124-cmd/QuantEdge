# QuantEdge 🚀

A Python-based quantitative Smart Money Concepts (SMC) research engine that transforms raw OHLC market data into market structure, liquidity zones, institutional footprints, trade signals, and performance analytics.

QuantEdge automates the complete trading research workflow, from swing detection and market structure analysis to signal generation and historical backtesting.

---

# Features

✅ Swing High / Swing Low Detection

✅ Market Structure Classification (HH, HL, LH, LL)

✅ Break of Structure (BOS) Detection

✅ Change of Character (CHOCH) Detection

✅ Equal High (EQH) & Equal Low (EQL) Liquidity Detection

✅ Liquidity Sweep Detection

✅ Validated Liquidity Sweeps

✅ Order Block Detection

✅ Fair Value Gap (FVG) Detection

✅ Trade Signal Generation

✅ Historical Backtesting Engine

✅ Equity Curve Generation

✅ Drawdown Analysis

✅ Performance Analytics

---

# Architecture

```text
Raw OHLC Data
       │
       ▼
Swing Detector V3
       │
       ▼
Market Structure V4
       │
       ├── BOS Detection
       │
       └── CHOCH Detection
                │
                ▼
Liquidity Detection
                │
                ▼
Liquidity Sweep Detection
                │
                ▼
Validated Sweeps
                │
                ▼
Order Block Detection
                │
                ▼
Fair Value Gap Detection
                │
                ▼
Signal Generator
                │
                ▼
Backtesting Engine
                │
                ▼
Equity Curve
                │
                ▼
Drawdown Analysis
                │
                ▼
Performance Analytics
```

---

# Tech Stack

- Python
- Pandas
- NumPy
- CSV Data Pipelines
- Quantitative Research
- Smart Money Concepts (SMC)
- Algorithmic Trading Research

---

# Modules

## Swing Detector V3

Detects significant swing highs and swing lows using a 3-candle left and 3-candle right confirmation model.

---

## Market Structure V4

Classifies swings into:

- Higher High (HH)
- Higher Low (HL)
- Lower High (LH)
- Lower Low (LL)

---

## BOS Detector

Identifies valid Break of Structure events.

---

## CHOCH Detector V3

Tracks trend transitions through protected highs and lows.

Detects:

- Bullish CHOCH
- Bearish CHOCH

---

## Liquidity Detector V2

Detects:

- Equal Highs (EQH)
- Equal Lows (EQL)

representing potential liquidity pools.

---

## Liquidity Sweep Detector V2

Detects stop-hunt events where price sweeps liquidity and closes back inside range.

---

## Validated Sweeps V2

Filters sweeps using market structure confirmation and CHOCH validation.

---

## Order Block Detector V1

Detects institutional order blocks after validated liquidity sweeps.

---

## Fair Value Gap Detector V2

Detects bullish and bearish fair value gaps.

---

## Signal Generator V3

Generates BUY and SELL signals using:

- Liquidity Sweep
- CHOCH
- Order Block
- Fair Value Gap

confluence.

---

## Backtesting Engine V1

Evaluates historical signal performance using:

- Fixed Risk Model
- 1:3 Risk Reward Ratio
- TP / SL Simulation

---

## Equity Curve Generator

Tracks account growth over time.

---

## Drawdown Analyzer

Calculates maximum drawdown and risk exposure.

---

## Performance Analyzer

Generates:

- Win Rate
- Profit Factor
- Expectancy
- Net R
- Winning Streak
- Losing Streak
- Return %

---

# Multi-Asset Validation Results

QuantEdge was tested on 2 years of M15 data across multiple markets.

## EURUSD

| Metric | Value |
|----------|----------|
| Trades | 234 |
| Wins | 88 |
| Losses | 146 |
| Win Rate | 37.61% |
| Profit Factor | 1.81 |
| Net R | 118R |
| Expectancy | 0.50R |
| Initial Capital | $10,000 |
| Final Capital | $21,800 |
| Return | 118% |
| Max Drawdown | $1,700 |
| Max Win Streak | 5 |
| Max Loss Streak | 9 |

---

## GBPUSD

| Metric | Value |
|----------|----------|
| Trades | 289 |
| Wins | 110 |
| Losses | 179 |
| Win Rate | 38.06% |
| Profit Factor | 1.84 |
| Net R | 151R |
| Expectancy | 0.52R |
| Initial Capital | $10,000 |
| Final Capital | $25,100 |
| Return | 151% |
| Max Drawdown | $1,500 |
| Max Win Streak | 5 |
| Max Loss Streak | 9 |

---

## XAUUSD

| Metric | Value |
|----------|----------|
| Trades | 352 |
| Wins | 126 |
| Losses | 226 |
| Win Rate | 35.80% |
| Profit Factor | 1.67 |
| Net R | 152R |
| Expectancy | 0.43R |
| Initial Capital | $10,000 |
| Final Capital | $25,200 |
| Return | 152% |
| Max Drawdown | N/A |
| Max Win Streak | 4 |
| Max Loss Streak | 9 |

---

# Research Summary

| Asset | Trades | Win Rate | Profit Factor | Net R |
|---------|---------:|---------:|---------:|---------:|
| EURUSD | 234 | 37.61% | 1.81 | 118R |
| GBPUSD | 289 | 38.06% | 1.84 | 151R |
| XAUUSD | 352 | 35.80% | 1.67 | 152R |

Total Trades Tested: **875**

The strategy demonstrated positive expectancy and profitability across all tested markets, indicating robustness beyond a single asset class.

---

# Future Roadmap

- [ ] Multi-Timeframe Analysis
- [ ] Session Filters (London / New York)
- [ ] Economic News Filters
- [ ] Order Block Strength Scoring
- [ ] Fair Value Gap Ranking
- [ ] Portfolio Backtesting
- [ ] Walk-Forward Testing
- [ ] Monte Carlo Analysis
- [ ] Interactive Dashboard
- [ ] Live Signal Engine

---

# Author

**Satya Sadvik**

B.Tech Information Technology

Quantitative Trading Research | Python Development | Algorithmic Trading