import pandas as pd

df = pd.read_csv("../data/EURUSD_M15.csv")

# --------------------------
# SWING DETECTOR V2
# --------------------------

swing_highs = []
swing_lows = []

for i in range(2, len(df) - 2):

    if (
        df["high"][i] > df["high"][i - 1]
        and df["high"][i] > df["high"][i - 2]
        and df["high"][i] > df["high"][i + 1]
        and df["high"][i] > df["high"][i + 2]
    ):
        swing_highs.append(i)

    if (
        df["low"][i] < df["low"][i - 1]
        and df["low"][i] < df["low"][i - 2]
        and df["low"][i] < df["low"][i + 1]
        and df["low"][i] < df["low"][i + 2]
    ):
        swing_lows.append(i)

# --------------------------
# BULLISH BOS
# --------------------------

print("\n===== BULLISH BOS =====\n")

count = 0

for idx in swing_highs:

    swing_price = df["high"][idx]

    for j in range(idx + 1, len(df)):

        if df["close"][j] > swing_price:

            print(
                f"BOS UP | "
                f"{df['time'][j]} | "
                f"Broke {swing_price}"
            )

            count += 1
            break

print("\nTotal Bullish BOS:", count)