import pandas as pd

# Load data
df = pd.read_csv("../data/EURUSD_M15.csv")

swings = []

# -----------------------------
# SWING DETECTOR V2
# -----------------------------
for i in range(2, len(df) - 2):

    # Swing High
    if (
        df["high"][i] > df["high"][i - 1]
        and df["high"][i] > df["high"][i - 2]
        and df["high"][i] > df["high"][i + 1]
        and df["high"][i] > df["high"][i + 2]
    ):
        swings.append({
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
            "time": df["time"][i],
            "price": df["low"][i],
            "type": "SL"
        })

# Sort swings
swings.sort(key=lambda x: x["time"])

# -----------------------------
# CLEAN SWINGS (V2)
# -----------------------------
cleaned_swings = []

for swing in swings:

    if not cleaned_swings:
        cleaned_swings.append(swing)
        continue

    last = cleaned_swings[-1]

    if swing["type"] == last["type"]:

        if swing["type"] == "SH":

            if swing["price"] > last["price"]:
                cleaned_swings[-1] = swing

        else:  # SL

            if swing["price"] < last["price"]:
                cleaned_swings[-1] = swing

    else:
        cleaned_swings.append(swing)

# -----------------------------
# MARKET STRUCTURE V3
# -----------------------------

last_high = None
last_low = None

print("\n===== MARKET STRUCTURE V3 =====\n")

for swing in cleaned_swings:

    # Swing High
    if swing["type"] == "SH":

        if last_high is None:

            label = "SH"

        elif swing["price"] > last_high:

            label = "HH"

        else:

            label = "LH"

        last_high = swing["price"]

    # Swing Low
    else:

        if last_low is None:

            label = "SL"

        elif swing["price"] > last_low:

            label = "HL"

        else:

            label = "LL"

        last_low = swing["price"]

    print(
        f"{swing['time']} | "
        f"{label} | "
        f"{swing['price']}"
    )