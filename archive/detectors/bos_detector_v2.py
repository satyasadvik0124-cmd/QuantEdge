import pandas as pd

df = pd.read_csv("../data/EURUSD_M15.csv")

# ----------------------------------
# STEP 1: DETECT SWINGS (V2)
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
# STEP 2: SORT
# ----------------------------------

swings.sort(key=lambda x: x["time"])

# ----------------------------------
# STEP 3: CLEAN DUPLICATES
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
# STEP 4: LABEL HH HL LH LL
# ----------------------------------

last_high = None
last_low = None

structure = []

for swing in cleaned:

    label = ""

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
# STEP 5: DETECT BOS
# ----------------------------------

print("\n===== BOS V2 =====\n")

bos_count = 0

for swing in structure:

    # Bullish BOS
    if swing["label"] == "HH":

        level = swing["price"]

        for i in range(swing["index"] + 1, len(df)):

            if df["close"][i] > level:

                print(
                    f"BULLISH BOS | "
                    f"{df['time'][i]} | "
                    f"Broke HH {level}"
                )

                bos_count += 1
                break

    # Bearish BOS
    elif swing["label"] == "LL":

        level = swing["price"]

        for i in range(swing["index"] + 1, len(df)):

            if df["close"][i] < level:

                print(
                    f"BEARISH BOS | "
                    f"{df['time'][i]} | "
                    f"Broke LL {level}"
                )

                bos_count += 1
                break

print("\nTotal BOS:", bos_count)