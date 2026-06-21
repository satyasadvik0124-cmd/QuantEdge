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

# ==================================
# SORT
# ==================================

swings.sort(key=lambda x: x["index"])

# ==================================
# CLEAN SAME TYPE SWINGS
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
# CHOCH V2
# ==================================

print("\n===== CHOCH V2 =====\n")

trend = None

protected_HL = None
protected_LH = None

choch_count = 0

for i in range(len(structure)):

    swing = structure[i]

    label = swing["label"]

    # --------------------------
    # Trend Detection
    # --------------------------

    if label == "HH":
        trend = "bullish"

    elif label == "LL":
        trend = "bearish"

    # --------------------------
    # Save protected levels
    # --------------------------

    if trend == "bullish" and label == "HL":
        protected_HL = swing

    if trend == "bearish" and label == "LH":
        protected_LH = swing

    # --------------------------
    # Bearish CHOCH
    # --------------------------

    if trend == "bullish" and protected_HL:

        level = protected_HL["price"]

        found = False

        for j in range(
            swing["index"] + 1,
            len(df)
        ):

            if df["close"][j] < level:

                print(
                    f"BEARISH CHOCH | "
                    f"{df['time'][j]} | "
                    f"Broke HL {round(level,5)}"
                )

                choch_count += 1

                trend = "bearish"
                protected_HL = None

                found = True
                break

        if found:
            continue

    # --------------------------
    # Bullish CHOCH
    # --------------------------

    if trend == "bearish" and protected_LH:

        level = protected_LH["price"]

        found = False

        for j in range(
            swing["index"] + 1,
            len(df)
        ):

            if df["close"][j] > level:

                print(
                    f"BULLISH CHOCH | "
                    f"{df['time'][j]} | "
                    f"Broke LH {round(level,5)}"
                )

                choch_count += 1

                trend = "bullish"
                protected_LH = None

                found = True
                break

        if found:
            continue

# ==================================
# SUMMARY
# ==================================

print("\nStructure Points:", len(structure))
print("Total CHOCH:", choch_count)