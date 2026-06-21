# QuantEdge - Project Progress Tracker

## Project Overview

QuantEdge is a Python-based Smart Money Concepts (SMC) market structure analysis and backtesting engine.

The project analyzes OHLC market data and identifies institutional trading concepts such as:

- Swing Highs & Swing Lows
- Market Structure
- Break of Structure (BOS)
- Change of Character (CHOCH)
- Liquidity Zones
- Liquidity Sweeps
- Order Blocks
- Fair Value Gaps
- Trade Signals
- Strategy Backtesting

---

# System Architecture

```text
Raw OHLC Data
      │
      ▼
Swing Detector V3
      │
      ▼
Market Structure V4
(HH HL LH LL)
      │
      ▼
BOS Detector
      │
      ▼
CHOCH Detector V3
      │
      ▼
Liquidity Detector V2
(EQH / EQL)
      │
      ▼
Liquidity Sweep Detector
      │
      ▼
Validated Sweeps
      │
      ▼
Order Block Detector V1
      │
      ▼
Fair Value Gap Detector V2
      │
      ▼
Signal Generator V2
      │
      ▼
Backtester V1
```

---

# Module Status

| Module | Version | Status |
|----------|----------|----------|
| Data Collection | V1 | ✅ Complete |
| Swing Detector | V3 | ✅ Complete |
| Market Structure | V4 | ✅ Complete |
| BOS Detector | V1 | ✅ Complete |
| CHOCH Detector | V3 | ✅ Complete |
| Liquidity Detector | V2 | ✅ Complete |
| Liquidity Sweep Detector | V1 | ✅ Complete |
| Sweep Validation | V1 | ✅ Complete |
| Order Block Detector | V1 | ✅ Complete |
| Fair Value Gap Detector | V2 | ✅ Complete |
| Signal Generator | V2 | ✅ Complete |
| Backtester | V1 | ✅ Complete |

---

# Module Details

## 1. Data Collection

### Purpose
Collect OHLC market data for analysis.

### Output
- EURUSD_M15.csv

---

## 2. Swing Detector V3

### Purpose
Identify valid swing highs and swing lows.

### Logic
- 3 candles to the left
- 3 candles to the right

### Output
- swings.csv

---

## 3. Market Structure V4

### Purpose
Classify swings into market structure labels.

### Labels
- HH (Higher High)
- HL (Higher Low)
- LH (Lower High)
- LL (Lower Low)

### Output
- market_structure_v4.csv

---

## 4. BOS Detector

### Purpose
Detect Break of Structure events.

### Types
- Bullish BOS
- Bearish BOS

### Output
- bos_events.csv

---

## 5. CHOCH Detector V3

### Purpose
Detect Change of Character events.

### Types
- Bullish CHOCH
- Bearish CHOCH

### Output
- choch_events.csv

---

## 6. Liquidity Detector V2

### Purpose
Detect liquidity pools.

### Types
- Equal Highs (EQH)
- Equal Lows (EQL)

### Output
- liquidity_events.csv

---

## 7. Liquidity Sweep Detector

### Purpose
Detect liquidity grabs.

### Types
- BSL Sweep
- SSL Sweep

### Output
- liquidity_sweeps.csv

---

## 8. Sweep Validation

### Purpose
Filter low-quality sweep events.

### Output
- validated_sweeps.csv

---

## 9. Order Block Detector V1

### Purpose
Detect institutional order blocks.

### Types
- Bullish OB
- Bearish OB

### Output
- order_blocks.csv

---

## 10. Fair Value Gap Detector V2

### Purpose
Detect market imbalances.

### Types
- Bullish FVG
- Bearish FVG

### Output
- fvg_events.csv

---

## 11. Signal Generator V2

### Purpose
Generate trading signals using confluence.

### Conditions
- Market Structure
- Sweep
- Order Block
- Fair Value Gap

### Output
- signals.csv

---

## 12. Backtester V1

### Purpose
Evaluate generated signals on historical data.

### Metrics
- Entry
- Stop Loss
- Take Profit
- Result
- RR

### Output
- backtest_results.csv

---

# Technologies Used

- Python
- Pandas
- NumPy
- MetaTrader 5
- CSV Data Pipeline

---

# Current Progress

Completed Modules: 12/12

Current Stage:
Advanced Market Structure Analytics Engine

---

# Resume Description

Built QuantEdge, a Python-based Smart Money Concepts trading analytics engine that automatically detects market structure (HH/HL/LH/LL), Break of Structure (BOS), Change of Character (CHOCH), liquidity zones, liquidity sweeps, order blocks, and fair value gaps. Developed a signal generation and backtesting framework to evaluate strategy performance on historical market data using institutional trading concepts.