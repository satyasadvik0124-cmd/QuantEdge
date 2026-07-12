"""
=========================================================
QuantEdge V2
Backtesting Configuration
=========================================================
"""

from config import *

from config_strategy import (
    FOREX_MIN_SWING_DISTANCE,
    XAU_MIN_SWING_DISTANCE,
    FOREX_EQ_TOLERANCE,
    XAU_EQ_TOLERANCE,
    FOREX_MIN_FVG_SIZE,
    XAU_MIN_FVG_SIZE
)

# ==========================================================
# Historical Data
# ==========================================================

PAIR = "GBPUSD"

TIMEFRAME_NAME = "M15"

HISTORICAL_FILE = (
    f"{DATA_FOLDER}/{PAIR}_{TIMEFRAME_NAME}_2Y.csv"
)

# ==========================================================
# Pair Specific Parameters
# ==========================================================

if PAIR == "XAUUSD":

    MIN_SWING_DISTANCE = XAU_MIN_SWING_DISTANCE
    EQ_TOLERANCE = XAU_EQ_TOLERANCE
    MIN_FVG_SIZE = XAU_MIN_FVG_SIZE

else:

    MIN_SWING_DISTANCE = FOREX_MIN_SWING_DISTANCE
    EQ_TOLERANCE = FOREX_EQ_TOLERANCE
    MIN_FVG_SIZE = FOREX_MIN_FVG_SIZE