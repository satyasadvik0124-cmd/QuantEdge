import pandas as pd

# ==================================
# LOAD DATA
# ==================================

df = pd.read_csv("../data/EURUSD_M15.csv")

MIN_DISTANCE = 0.0010

# ==================================
# SWING DETECTOR V3
# ==================================

swings = []

for i in range(3, len(df) - 3):

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

swings.sort(key=lambda x: x["index"])

# ==================================
# CLEAN SWINGS
# ==================================

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

# ==================================
# DISTANCE FILTER
# ==================================

filtered = []

for swing in cleaned:

    if not filtered:
        filtered.append(swing)
        continue

    last = filtered[-1]

    if abs(swing["price"] - last["price"]) >= MIN_DISTANCE:
        filtered.append(swing)

# ==================================
# STRUCTURE LABELS
# ==================================

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

# ==================================
# CHOCH DETECTOR
# ==================================

print("\n===== CHOCH V1 =====\n")

trend = None

last_HL = None
last_LH = None

choch_count = 0

for swing in structure:

    label = swing["label"]

    # ------------------------
    # Trend Detection
    # ------------------------

    if label == "HH":
        trend = "bullish"

    elif label == "LL":
        trend = "bearish"

    # ------------------------
    # Store Protected Levels
    # ------------------------

    if label == "HL":
        last_HL = swing

    elif label == "LH":
        last_LH = swing

    # ------------------------
    # Bearish CHOCH
    # ------------------------

    if trend == "bullish" and last_HL:

        level = last_HL["price"]

        for j in range(
            swing["index"] + 1,
            len(df)
        ):

            if df["close"][j] < level:

                print(
                    f"BEARISH CHOCH | "
                    f"{df['time'][j]} | "
                    f"Below HL {round(level,5)}"
                )

                choch_count += 1

                last_HL = None
                break

    # ------------------------
    # Bullish CHOCH
    # ------------------------

    if trend == "bearish" and last_LH:

        level = last_LH["price"]

        for j in range(
            swing["index"] + 1,
            len(df)
        ):

            if df["close"][j] > level:

                print(
                    f"BULLISH CHOCH | "
                    f"{df['time'][j]} | "
                    f"Above LH {round(level,5)}"
                )

                choch_count += 1

                last_LH = None
                break

# ==================================
# SUMMARY
# ==================================

print("\nTotal CHOCH:", choch_count)