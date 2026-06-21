import pandas as pd

# ----------------------------------
# LOAD DATA
# ----------------------------------

df = pd.read_csv("../data/EURUSD_M15.csv")

# ----------------------------------
# SWING DETECTOR V2
# ----------------------------------

swings = []

for i in range(2, len(df) - 2):

    # Swing High
    if (
        df["high"][i] > df["high"][i - 1]
        and df["high"][i] > df["high"][i - 2]
        and df["high"][i] > df["high"][i + 1]
        and df["high"][i] > df["high"][i + 2]
    ):
        swings.append({
            "index": i,
            "time": df["time"][i],
            "price": df["high"][i],
            "type": "SH"
        })

    # Swing Low
    if (
        df["low"][i] < df["low"][i - 1]
        and df["low"][i] < df["low"][i - 2]
        and df["low"][i] < df["low"][i + 1]
        and df["low"][i] < df["low"][i + 2]
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

swings.sort(key=lambda x: x["time"])

# ----------------------------------
# CLEAN DUPLICATES
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
# LABEL STRUCTURE
# ----------------------------------

last_high = None
last_low = None

structure = []

for swing in cleaned:

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
# BOS V3
# ----------------------------------

print("\n===== BOS V3 =====\n")

bos_count = 0

latest_hh = None
latest_ll = None

for swing in structure:

    # Store only latest HH
    if swing["label"] == "HH":
        latest_hh = swing

    # Store only latest LL
    elif swing["label"] == "LL":
        latest_ll = swing

    # Check bullish BOS
    if latest_hh is not None:

        level = latest_hh["price"]

        for i in range(
            latest_hh["index"] + 1,
            min(latest_hh["index"] + 50, len(df))
        ):

            if df["close"][i] > level:

                print(
                    f"BULLISH BOS | "
                    f"{df['time'][i]} | "
                    f"HH {level}"
                )

                bos_count += 1
                latest_hh = None
                break

    # Check bearish BOS
    if latest_ll is not None:

        level = latest_ll["price"]

        for i in range(
            latest_ll["index"] + 1,
            min(latest_ll["index"] + 50, len(df))
        ):

            if df["close"][i] < level:

                print(
                    f"BEARISH BOS | "
                    f"{df['time'][i]} | "
                    f"LL {level}"
                )

                bos_count += 1
                latest_ll = None
                break

print("\nTotal BOS:", bos_count)