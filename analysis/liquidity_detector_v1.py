import pandas as pd

# Load market structure data
df = pd.read_csv("market_structure_v4.csv")

# Convert time column
df["time"] = pd.to_datetime(df["time"])

# EURUSD tolerance (2 pips)
TOLERANCE = 0.0002

liquidity_levels = []

# =====================
# Equal Highs (EQH)
# =====================

swing_highs = df[df["type"] == "SH"].reset_index(drop=True)

for i in range(len(swing_highs) - 1):

    h1 = swing_highs.iloc[i]
    h2 = swing_highs.iloc[i + 1]

    if abs(h1["price"] - h2["price"]) <= TOLERANCE:

        liquidity_levels.append({
            "time": h2["time"],
            "type": "EQH",
            "price": round((h1["price"] + h2["price"]) / 2, 5)
        })

        print(
            f"EQH | {h2['time']} | "
            f"{round((h1['price'] + h2['price']) / 2, 5)}"
        )

# =====================
# Equal Lows (EQL)
# =====================

swing_lows = df[df["type"] == "SL"].reset_index(drop=True)

for i in range(len(swing_lows) - 1):

    l1 = swing_lows.iloc[i]
    l2 = swing_lows.iloc[i + 1]

    if abs(l1["price"] - l2["price"]) <= TOLERANCE:

        liquidity_levels.append({
            "time": l2["time"],
            "type": "EQL",
            "price": round((l1["price"] + l2["price"]) / 2, 5)
        })

        print(
            f"EQL | {l2['time']} | "
            f"{round((l1['price'] + l2['price']) / 2, 5)}"
        )

# =====================
# Save Results
# =====================

liquidity_df = pd.DataFrame(liquidity_levels)

liquidity_df.to_csv(
    "liquidity_v1.csv",
    index=False
)

print("\nLiquidity Levels Found:", len(liquidity_df))