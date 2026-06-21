import pandas as pd
import sys
import os

# ----------------------------------
# Setup
# ----------------------------------

sys.path.append(
    os.path.dirname(
        os.path.dirname(__file__)
    )
)

from config import PAIR, TIMEFRAME

print(PAIR)
print(TIMEFRAME)
# ----------------------------------
# Load Data
# ----------------------------------

df = pd.read_csv(
    f"../data/{PAIR}_{TIMEFRAME}.csv"
)

print("\nDataset Loaded Successfully")
print("Rows:", len(df))
print("Columns:", df.columns.tolist())
print(df.head())
print(df["close"].head())
# ----------------------------------
# Swing Detection V3
# 3 candles left + 3 candles right
# ----------------------------------

swing_highs = []
swing_lows = []

for i in range(3, len(df) - 3):

    # Swing High
    if (
        df["high"][i] > df["high"][i - 1]
        and df["high"][i] > df["high"][i - 2]
        and df["high"][i] > df["high"][i - 3]
        and df["high"][i] > df["high"][i + 1]
        and df["high"][i] > df["high"][i + 2]
        and df["high"][i] > df["high"][i + 3]
    ):
        swing_highs.append(i)

    # Swing Low
    if (
        df["low"][i] < df["low"][i - 1]
        and df["low"][i] < df["low"][i - 2]
        and df["low"][i] < df["low"][i - 3]
        and df["low"][i] < df["low"][i + 1]
        and df["low"][i] < df["low"][i + 2]
        and df["low"][i] < df["low"][i + 3]
    ):
        swing_lows.append(i)

# ----------------------------------
# Statistics
# ----------------------------------

total_swings = len(swing_highs) + len(swing_lows)

print("\n" + "=" * 40)
print("SWING DETECTOR V3 REPORT")
print("=" * 40)

print(f"Total Candles : {len(df):,}")
print(f"Swing Highs   : {len(swing_highs):,}")
print(f"Swing Lows    : {len(swing_lows):,}")
print(f"Total Swings  : {total_swings:,}")

print(
    f"Swing Density : "
    f"{(total_swings / len(df)) * 100:.2f}%"
)

# ----------------------------------
# Sample Output
# ----------------------------------

print("\nFirst 10 Swing Highs:\n")

for idx in swing_highs[:10]:
    print(
        f"{df['time'][idx]} | "
        f"{df['high'][idx]}"
    )

print("\nFirst 10 Swing Lows:\n")

for idx in swing_lows[:10]:
    print(
        f"{df['time'][idx]} | "
        f"{df['low'][idx]}"
    )

print("\nValidation Complete")