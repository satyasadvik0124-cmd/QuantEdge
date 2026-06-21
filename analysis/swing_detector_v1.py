import pandas as pd

df = pd.read_csv("../data/EURUSD_M15.csv")

swing_highs = []
swing_lows = []

for i in range(1, len(df) - 1):

    if (
        df["high"][i] > df["high"][i - 1]
        and
        df["high"][i] > df["high"][i + 1]
    ):
        swing_highs.append(i)

    if (
        df["low"][i] < df["low"][i - 1]
        and
        df["low"][i] < df["low"][i + 1]
    ):
        swing_lows.append(i)

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
    print("\nHigh Structure:")

for i in range(1, len(swing_highs)):

    previous_idx = swing_highs[i - 1]
    current_idx = swing_highs[i]

    previous_high = df["high"][previous_idx]
    current_high = df["high"][current_idx]

    if current_high > previous_high:

        print(
            df["time"][current_idx],
            current_high,
            "HH"
        )

    else:

        print(
            df["time"][current_idx],
            current_high,
            "LH"
        )
        print("\nLow Structure:")

for i in range(1, len(swing_lows)):

    previous_idx = swing_lows[i - 1]
    current_idx = swing_lows[i]

    previous_low = df["low"][previous_idx]
    current_low = df["low"][current_idx]

    if current_low > previous_low:

        print(
            df["time"][current_idx],
            current_low,
            "HL"
        )

    else:

        print(
            df["time"][current_idx],
            current_low,
            "LL"
        )