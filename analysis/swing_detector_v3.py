import pandas as pd
import sys
import os

sys.path.append(
    os.path.dirname(
        os.path.dirname(__file__)
    )
)

from config import PAIR, TIMEFRAME

print(f"\nUsing: {PAIR}_{TIMEFRAME}")

from config import PAIR, TIMEFRAME

df = pd.read_csv(
    f"../data/{PAIR}_{TIMEFRAME}.csv"
)
print(df.head())
print()
print(df[["high", "low"]].head())
swing_highs = []
swing_lows = []

for i in range(3, len(df) - 3):

    # Swing High
    if (
        df["high"][i] > df["high"][i-1]
        and df["high"][i] > df["high"][i-2]
        and df["high"][i] > df["high"][i-3]
        and df["high"][i] > df["high"][i+1]
        and df["high"][i] > df["high"][i+2]
        and df["high"][i] > df["high"][i+3]
    ):
        swing_highs.append(i)

    # Swing Low
    if (
        df["low"][i] < df["low"][i-1]
        and df["low"][i] < df["low"][i-2]
        and df["low"][i] < df["low"][i-3]
        and df["low"][i] < df["low"][i+1]
        and df["low"][i] < df["low"][i+2]
        and df["low"][i] < df["low"][i+3]
    ):
        swing_lows.append(i)

print("===== SWING DETECTOR V3 =====")
print()
print("Swing Highs:", len(swing_highs))
print("Swing Lows :", len(swing_lows))

print("\nFirst 10 Swing Highs:\n")

for idx in swing_highs[:10]:
    print(df["time"][idx], df["high"][idx])

print("\nFirst 10 Swing Lows:\n")

for idx in swing_lows[:10]:
    print(df["time"][idx], df["low"][idx])
    