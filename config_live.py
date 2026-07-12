"""
=========================================================
QuantEdge V2
Live Trading Configuration
=========================================================
"""

import MetaTrader5 as mt5

from config import *

# ==========================================================
# Live Trading
# ==========================================================

PAIR = "BTCUSD"

TIMEFRAME = mt5.TIMEFRAME_M15

TIMEFRAME_NAME = "M15"

# ==========================================================
# MT5
# ==========================================================

BARS = 500

# Use only closed candles
INCLUDE_CURRENT = False