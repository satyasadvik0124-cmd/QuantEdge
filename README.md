# QuantEdge 

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

QuantEdge was tested on **2 years of M15 historical data** across multiple markets.

## EURUSD

| Metric          | Value   |
| --------------- | ------- |
| Trades          | 236     |
| Wins            | 89      |
| Losses          | 147     |
| Win Rate        | 37.71%  |
| Profit Factor   | 1.82    |
| Net R           | 120R    |
| Expectancy      | 0.51R   |
| Initial Capital | $10,000 |
| Final Capital   | $22,000 |
| Return          | 120%    |
| Max Win Streak  | 4       |
| Max Loss Streak | 9       |

---

## GBPUSD

| Metric          | Value   |
| --------------- | ------- |
| Trades          | 295     |
| Wins            | 113     |
| Losses          | 182     |
| Win Rate        | 38.31%  |
| Profit Factor   | 1.86    |
| Net R           | 157R    |
| Expectancy      | 0.53R   |
| Initial Capital | $10,000 |
| Final Capital   | $25,700 |
| Return          | 157%    |
| Max Win Streak  | 5       |
| Max Loss Streak | 9       |

---

## XAUUSD

| Metric          | Value   |
| --------------- | ------- |
| Trades          | 347     |
| Wins            | 122     |
| Losses          | 225     |
| Win Rate        | 35.16%  |
| Profit Factor   | 1.63    |
| Net R           | 141R    |
| Expectancy      | 0.41R   |
| Initial Capital | $10,000 |
| Final Capital   | $24,100 |
| Return          | 141%    |
| Max Win Streak  | 6       |
| Max Loss Streak | 8       |

---

## USDCAD

| Metric          | Value   |
| --------------- | ------- |
| Trades          | 218     |
| Wins            | 81      |
| Losses          | 137     |
| Win Rate        | 37.16%  |
| Profit Factor   | 1.77    |
| Net R           | 106R    |
| Expectancy      | 0.49R   |
| Initial Capital | $10,000 |
| Final Capital   | $20,600 |
| Return          | 106%    |
| Max Win Streak  | 4       |
| Max Loss Streak | 12      |

---

## EURAUD

| Metric          | Value   |
| --------------- | ------- |
| Trades          | 314     |
| Wins            | 103     |
| Losses          | 211     |
| Win Rate        | 32.80%  |
| Profit Factor   | 1.46    |
| Net R           | 98R     |
| Expectancy      | 0.31R   |
| Initial Capital | $10,000 |
| Final Capital   | $19,800 |
| Return          | 98%     |
| Max Win Streak  | 6       |
| Max Loss Streak | 13      |

---

# Research Summary

| Asset  | Trades | Win Rate | Profit Factor | Net R |
| ------ | -----: | -------: | ------------: | ----: |
| EURUSD |    236 |   37.71% |          1.82 |  120R |
| GBPUSD |    295 |   38.31% |          1.86 |  157R |
| XAUUSD |    347 |   35.16% |          1.63 |  141R |
| USDCAD |    218 |   37.16% |          1.77 |  106R |
| EURAUD |    314 |   32.80% |          1.46 |   98R |

**Total Trades Tested:** **1,410**

The strategy demonstrated positive expectancy and profitability across multiple asset classes, including major Forex pairs, Gold, and cross-currency pairs. QuantEdge maintained a positive Profit Factor (>1.4) and positive expectancy across all validated markets, demonstrating that the Smart Money Concepts framework generalizes beyond a single instrument.

> **Note:** Preliminary testing was also conducted on JPY pairs (USDJPY and GBPJPY). Due to the limited number of generated trades, those results are excluded from the validation summary until additional testing is completed.


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



Quantitative Trading Research | Algorithmic Trading