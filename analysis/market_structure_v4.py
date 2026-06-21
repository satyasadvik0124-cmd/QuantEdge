import pandas as pd

# ----------------------------------
# LOAD DATA
# ----------------------------------

df = pd.read_csv("../data/EURUSD_M15.csv")

# ----------------------------------
# SETTINGS
# ----------------------------------

MIN_DISTANCE = 0.0010      # 10 pips

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
# CLEAN SAME TYPE SWINGS
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

    distance = abs(swing["price"] - last["price"])

    if distance >= MIN_DISTANCE:
        filtered.append(swing)

# ----------------------------------
# LABEL STRUCTURE
# ----------------------------------
# ----------------------------------
# LABEL STRUCTURE
# ----------------------------------

last_high = None
last_low = None

structure = []

print("\n===== MARKET STRUCTURE V4 =====\n")

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

    print(
        f"{swing['time']} | "
        f"{label} | "
        f"{round(swing['price'],5)}"
    )

print("\nOriginal Swings :", len(swings))
print("Cleaned Swings  :", len(cleaned))
print("Filtered Swings :", len(filtered))
structure_df = pd.DataFrame(structure)

structure_df.to_csv(
    "../outputs/market_structure_v4.csv",
    index=False
)

print("\nSaved ../outputs/market_structure_v4.csv")