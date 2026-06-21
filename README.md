# QuantEdge

## Smart Money Concepts Trading Analytics Engine

QuantEdge is a Python-based quantitative trading research project that automates Smart Money Concepts (SMC) analysis using market structure and liquidity-based models.

The system processes OHLC market data and identifies institutional trading concepts such as:

- Swing Highs & Swing Lows
- Market Structure (HH, HL, LH, LL)
- Break of Structure (BOS)
- Change of Character (CHOCH)
- Liquidity Zones
- Liquidity Sweeps
- Order Blocks
- Fair Value Gaps (FVG)
- Trade Signals
- Strategy Backtesting

---

## Architecture

```text
Raw Market Data
       │
       ▼
Swing Detection
       │
       ▼
Market Structure
(HH / HL / LH / LL)
       │
       ▼
BOS Detection
       │
       ▼
CHOCH Detection
       │
       ▼
Liquidity Detection
       │
       ▼
Liquidity Sweeps
       │
       ▼
Order Blocks
       │
       ▼
Fair Value Gaps
       │
       ▼
Signal Generation
       │
       ▼
Backtesting Engine
```

---

## Features

### Market Structure Analysis

Automatically labels:

- Higher High (HH)
- Higher Low (HL)
- Lower High (LH)
- Lower Low (LL)

---

### BOS Detection

Detects:

- Bullish BOS
- Bearish BOS

Used to identify trend continuation.

---

### CHOCH Detection

Detects:

- Bullish CHOCH
- Bearish CHOCH

Used to identify potential trend reversals.

---

### Liquidity Analysis

Detects:

- Equal Highs (EQH)
- Equal Lows (EQL)

Represents institutional liquidity pools.

---

### Liquidity Sweeps

Identifies:

- Buy-Side Liquidity Sweeps
- Sell-Side Liquidity Sweeps

Detects stop-hunt behavior and liquidity grabs.

---

### Order Blocks

Identifies:

- Bullish Order Blocks
- Bearish Order Blocks

Represents institutional accumulation and distribution zones.

---

### Fair Value Gaps

Detects market imbalances using three-candle inefficiency logic.

Types:

- Bullish FVG
- Bearish FVG

---

### Signal Generation

Trade setups generated from confluence of:

- Structure
- Liquidity Sweep
- Order Block
- Fair Value Gap

---

### Backtesting Engine

Evaluates:

- Entry
- Stop Loss
- Take Profit
- Risk-Reward Ratio
- Win/Loss Results

---

## Tech Stack

- Python
- Pandas
- NumPy
- MetaTrader 5
- CSV-Based Data Pipeline

---

## Project Structure

```text
QuantEdge/
│
├── analysis/
│
├── data/
│
├── outputs/
│
├── docs/
│   └── project_progress.md
│
├── README.md
└── requirements.txt
```

---

## Example Workflow

```text
EURUSD_M15.csv
      ↓
Swings
      ↓
Market Structure
      ↓
BOS
      ↓
CHOCH
      ↓
Liquidity
      ↓
Sweeps
      ↓
Order Blocks
      ↓
FVG
      ↓
Signals
      ↓
Backtesting
```

---

## Current Status

### Completed Modules

- Data Collection
- Swing Detection
- Market Structure
- BOS Detection
- CHOCH Detection
- Liquidity Detection
- Liquidity Sweeps
- Order Blocks
- Fair Value Gaps
- Signal Generation
- Backtesting

Project Status:

**Active Development**

---

## Future Enhancements

- Multi-Timeframe Analysis
- Premium/Discount Zones
- Mitigation Block Detection
- Confluence Scoring Engine
- Strategy Optimization
- Walk-Forward Testing
- Interactive Dashboard
- Portfolio-Level Backtesting

---

## Resume Description

Built QuantEdge, a Python-based Smart Money Concepts trading analytics engine that automatically detects market structure (HH/HL/LH/LL), BOS, CHOCH, liquidity zones, sweeps, order blocks, and fair value gaps. Developed a signal generation and backtesting framework to evaluate strategy performance on historical market data using institutional trading concepts.