import pandas as pd

# Load data
df = pd.read_csv("../data/EURUSD_M15.csv")

swing_highs = []
swing_lows = []

# 5-candle swing detection
for i in range(2, len(df) - 2):

    # Swing High
    if (
        df["high"][i] > df["high"][i - 1]
        and df["high"][i] > df["high"][i - 2]
        and df["high"][i] > df["high"][i + 1]
        and df["high"][i] > df["high"][i + 2]
    ):
        swing_highs.append(i)

    # Swing Low
    if (
        df["low"][i] < df["low"][i - 1]
        and df["low"][i] < df["low"][i - 2]
        and df["low"][i] < df["low"][i + 1]
        and df["low"][i] < df["low"][i + 2]
    ):
        swing_lows.append(i)

print("=== Swing Detector V2 ===")
print("Swing Highs:", len(swing_highs))
print("Swing Lows:", len(swing_lows))

print("\nFirst 5 Swing Highs:")

for idx in swing_highs[:5]:
    print(
        df["time"][idx],
        df["high"][idx]
    )

print("\nFirst 5 Swing Lows:")

for idx in swing_lows[:5]:
    print(
        df["time"][idx],
        df["low"][idx]
    )