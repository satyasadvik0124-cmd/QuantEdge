import pandas as pd

# ----------------------------------
# LOAD DATA
# ----------------------------------
import sys
import os

sys.path.append(
    os.path.dirname(
        os.path.dirname(__file__)
    )
)

from config import PAIR, TIMEFRAME
df = pd.read_csv(
    f"../data/{PAIR}_{TIMEFRAME}.csv"
)

if PAIR == "XAUUSD":
    MIN_DISTANCE = 5.0
else:
    MIN_DISTANCE = 0.0010

# ----------------------------------
# SWING DETECTOR V3
# ----------------------------------

swings = []

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
        swings.append({
            "index": i,
            "time": df["time"][i],
            "price": df["high"][i],
            "type": "SH"
        })

    # Swing Low
    if (
        df["low"][i] < df["low"][i-1]
        and df["low"][i] < df["low"][i-2]
        and df["low"][i] < df["low"][i-3]
        and df["low"][i] < df["low"][i+1]
        and df["low"][i] < df["low"][i+2]
        and df["low"][i] < df["low"][i+3]
    ):
        swings.append({
            "index": i,
            "time": df["time"][i],
            "price": df["low"][i],
            "type": "SL"
        })

# ----------------------------------
# SORT
# ----------------------------------

swings.sort(key=lambda x: x["index"])

# ----------------------------------
# CLEAN SAME-TYPE SWINGS
# ----------------------------------

cleaned = []

for swing in swings:

    if not cleaned:
        cleaned.append(swing)
        continue

    last = cleaned[-1]

    if swing["type"] == last["type"]:

        if swing["type"] == "SH":

            if swing["price"] > last["price"]:
                cleaned[-1] = swing

        else:

            if swing["price"] < last["price"]:
                cleaned[-1] = swing

    else:
        cleaned.append(swing)

# ----------------------------------
# DISTANCE FILTER
# ----------------------------------

filtered = []

for swing in cleaned:

    if not filtered:
        filtered.append(swing)
        continue

    last = filtered[-1]

    distance = abs(
        swing["price"] - last["price"]
    )

    if distance >= MIN_DISTANCE:
        filtered.append(swing)

# ----------------------------------
# LABEL STRUCTURE
# ----------------------------------

last_high = None
last_low = None

structure = []

for swing in filtered:

    if swing["type"] == "SH":

        if last_high is None:
            label = "SH"

        elif swing["price"] > last_high:
            label = "HH"

        else:
            label = "LH"

        last_high = swing["price"]

    else:

        if last_low is None:
            label = "SL"

        elif swing["price"] > last_low:
            label = "HL"

        else:
            label = "LL"

        last_low = swing["price"]

    swing["label"] = label
    structure.append(swing)

# ----------------------------------
# BOS V4
# ----------------------------------

print("\n===== BOS V4 =====\n")

bos_events = []

bullish_bos_count = 0
bearish_bos_count = 0

for swing in structure:

    # -----------------------
    # Bullish BOS
    # -----------------------

    if swing["label"] == "HH":

        level = swing["price"]

        for j in range(
            swing["index"] + 1,
            len(df)
        ):

            if df["close"][j] > level:

                bos_events.append({
                    "time": df["time"][j],
                    "type": "Bullish BOS",
                    "level": level
                })

                bullish_bos_count += 1
                break

    # -----------------------
    # Bearish BOS
    # -----------------------

    elif swing["label"] == "LL":

        level = swing["price"]

        for j in range(
            swing["index"] + 1,
            len(df)
        ):

            if df["close"][j] < level:

                bos_events.append({
                    "time": df["time"][j],
                    "type": "Bearish BOS",
                    "level": level
                })

                bearish_bos_count += 1
                break

# ----------------------------------
# SAVE BOS EVENTS
# ----------------------------------

bos_df = pd.DataFrame(bos_events)

bos_df.to_csv(
    "../outputs/bos_events_v4.csv",
    index=False
)

# ----------------------------------
# REPORT
# ----------------------------------

print("\n===== BOS REPORT =====\n")

print(f"Filtered Structure : {len(structure):,}")

print(f"Bullish BOS        : {bullish_bos_count:,}")
print(f"Bearish BOS        : {bearish_bos_count:,}")

print(
    f"Total BOS          : "
    f"{bullish_bos_count + bearish_bos_count:,}"
)

print(
    f"BOS Ratio          : "
    f"{((bullish_bos_count + bearish_bos_count) / len(structure)) * 100:.2f}%"
)

print(
    "\nSaved: "
    "../outputs/bos_events_v4.csv"
)