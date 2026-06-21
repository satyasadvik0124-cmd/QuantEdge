import pandas as pd
import sys
import os

sys.path.append(
    os.path.dirname(
        os.path.dirname(__file__)
    )
)

from config import PAIR

# =====================
# LOAD DATA
# =====================

df = pd.read_csv(
    "../outputs/market_structure_v4.csv"
)

df["time"] = pd.to_datetime(
    df["time"]
)

# =====================
# SETTINGS
# =====================

if PAIR == "XAUUSD":
    TOLERANCE = 2.0
else:
    TOLERANCE = 0.0002

LOOKAHEAD = 5

liquidity_levels = []

eqh_count = 0
eql_count = 0

# =====================
# EQUAL HIGHS
# =====================

swing_highs = (
    df[df["type"] == "SH"]
    .reset_index(drop=True)
)

for i in range(len(swing_highs)):

    h1 = swing_highs.iloc[i]

    for j in range(
        i + 1,
        min(
            i + LOOKAHEAD + 1,
            len(swing_highs)
        )
    ):

        h2 = swing_highs.iloc[j]

        if abs(
            h1["price"] - h2["price"]
        ) <= TOLERANCE:

            liquidity_levels.append({
                "time": h2["time"],
                "type": "EQH",
                "price": round(
                    (h1["price"] + h2["price"]) / 2,
                    5
                )
            })

            eqh_count += 1

# =====================
# EQUAL LOWS
# =====================

swing_lows = (
    df[df["type"] == "SL"]
    .reset_index(drop=True)
)

for i in range(len(swing_lows)):

    l1 = swing_lows.iloc[i]

    for j in range(
        i + 1,
        min(
            i + LOOKAHEAD + 1,
            len(swing_lows)
        )
    ):

        l2 = swing_lows.iloc[j]

        if abs(
            l1["price"] - l2["price"]
        ) <= TOLERANCE:

            liquidity_levels.append({
                "time": l2["time"],
                "type": "EQL",
                "price": round(
                    (l1["price"] + l2["price"]) / 2,
                    5
                )
            })

            eql_count += 1

# =====================
# REMOVE DUPLICATES
# =====================

liquidity_df = pd.DataFrame(
    liquidity_levels
)

if not liquidity_df.empty:

    liquidity_df = (
        liquidity_df
        .drop_duplicates()
        .sort_values(by="time")
        .reset_index(drop=True)
    )

# =====================
# SAVE
# =====================

liquidity_df.to_csv(
    "../outputs/liquidity_v2.csv",
    index=False
)

# =====================
# REPORT
# =====================

print("\n===== LIQUIDITY REPORT =====\n")

print(f"Pair                   : {PAIR}")
print(f"Tolerance              : {TOLERANCE}")

print(f"\nEQH Count              : {eqh_count:,}")
print(f"EQL Count              : {eql_count:,}")

print(
    f"Raw Liquidity Levels   : "
    f"{eqh_count + eql_count:,}"
)

print(
    f"Unique Liquidity Levels: "
    f"{len(liquidity_df):,}"
)

print(
    "\nSaved: "
    "../outputs/liquidity_v2.csv"
)