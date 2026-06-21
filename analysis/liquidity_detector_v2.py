import pandas as pd

df = pd.read_csv("../outputs/market_structure_v4.csv")
df["time"] = pd.to_datetime(df["time"])

TOLERANCE = 0.0002      # 2 pips
LOOKAHEAD = 5           # compare next 5 swings

liquidity_levels = []

# =====================
# Equal Highs
# =====================

swing_highs = df[df["type"] == "SH"].reset_index(drop=True)

for i in range(len(swing_highs)):

    h1 = swing_highs.iloc[i]

    for j in range(i + 1, min(i + LOOKAHEAD + 1, len(swing_highs))):

        h2 = swing_highs.iloc[j]

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
# Equal Lows
# =====================

swing_lows = df[df["type"] == "SL"].reset_index(drop=True)

for i in range(len(swing_lows)):

    l1 = swing_lows.iloc[i]

    for j in range(i + 1, min(i + LOOKAHEAD + 1, len(swing_lows))):

        l2 = swing_lows.iloc[j]

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
# Remove duplicates
# =====================

liquidity_df = pd.DataFrame(liquidity_levels)

if not liquidity_df.empty:
    liquidity_df = liquidity_df.drop_duplicates()
liquidity_df.to_csv(
    "../outputs/liquidity_v2.csv",
    index=False
)

print("\nLiquidity Levels Found:", len(liquidity_df))
print("Saved: ../outputs/liquidity_v2.csv")