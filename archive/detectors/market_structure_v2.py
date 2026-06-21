import pandas as pd

# Load data
df = pd.read_csv("../data/EURUSD_M15.csv")

swings = []

# Swing Detection V2
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

# Sort by time
swings.sort(key=lambda x: x["time"])

# ----------------------------------
# CLEAN DUPLICATE SWINGS
# ----------------------------------

cleaned_swings = []

for swing in swings:

    # First swing
    if not cleaned_swings:
        cleaned_swings.append(swing)
        continue

    last = cleaned_swings[-1]

    # Same type?
    if swing["type"] == last["type"]:

        # Keep stronger SH
        if swing["type"] == "SH":

            if swing["price"] > last["price"]:
                cleaned_swings[-1] = swing

        # Keep stronger SL
        else:

            if swing["price"] < last["price"]:
                cleaned_swings[-1] = swing

    else:
        cleaned_swings.append(swing)

# ----------------------------------
# RESULTS
# ----------------------------------

print("\n===== MARKET STRUCTURE V2 =====\n")

print("Original Swings :", len(swings))
print("Cleaned Swings  :", len(cleaned_swings))

print("\nFirst 20 Cleaned Swings:\n")

for swing in cleaned_swings[:20]:

    print(
        f"{swing['time']} | "
        f"{swing['type']} | "
        f"{swing['price']}"
    )