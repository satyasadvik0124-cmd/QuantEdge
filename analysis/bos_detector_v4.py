import pandas as pd

# ----------------------------------
# LOAD DATA
# ----------------------------------

df = pd.read_csv("../data/EURUSD_M15.csv")

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

bos_count = 0

for i in range(len(structure)):

    swing = structure[i]

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

                print(
                    f"BULLISH BOS | "
                    f"{df['time'][j]} | "
                    f"{round(level,5)}"
                )

                bos_count += 1
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

                print(
                    f"BEARISH BOS | "
                    f"{df['time'][j]} | "
                    f"{round(level,5)}"
                )

                bos_count += 1
                break

print("\nFiltered Structure:", len(structure))
print("Total BOS:", bos_count)