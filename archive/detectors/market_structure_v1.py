import pandas as pd

# Load M15 data
df = pd.read_csv("../data/EURUSD_M15.csv")

swings = []

# Swing Detection V2 (5-candle swing)
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

print("\n===== MARKET STRUCTURE V1 =====\n")

print("Total Swings Found:", len(swings))

print("\nFirst 20 Swings:\n")

for swing in swings[:20]:
    print(
        f"{swing['time']} | "
        f"{swing['type']} | "
        f"{swing['price']}"
    )