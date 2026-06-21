import pandas as pd
import sys
import os

sys.path.append(
    os.path.dirname(
        os.path.dirname(__file__)
    )
)

from config import PAIR, TIMEFRAME

print(f"\nUsing: {PAIR}_{TIMEFRAME}")
# ==================================
# LOAD DATA
# ==================================
df = pd.read_csv(
    f"../data/{PAIR}_{TIMEFRAME}.csv"
)

df["time"] = pd.to_datetime(df["time"])

# ==================================
# SETTINGS
# ==================================

MIN_FVG_SIZE = 0.0005   # 5 pips

# ==================================
# STORAGE
# ==================================

fvg_list = []

print("\n===== FVG DETECTOR V2 =====\n")

# ==================================
# DETECT FVG
# ==================================

for i in range(2, len(df)):

    c1 = df.iloc[i - 2]
    c2 = df.iloc[i - 1]
    c3 = df.iloc[i]

    # ----------------------------------
    # BULLISH FVG
    # ----------------------------------

    bullish_gap = c3["low"] - c1["high"]

    if bullish_gap >= MIN_FVG_SIZE:

        fvg_list.append({
            "time": c3["time"],
            "type": "BULLISH_FVG",
            "top": round(c3["low"], 5),
            "bottom": round(c1["high"], 5),
            "gap_size": round(bullish_gap, 5)
        })

        print(
            f"BULLISH_FVG | "
            f"{c3['time']} | "
            f"{round(c1['high'],5)} -> "
            f"{round(c3['low'],5)} | "
            f"Gap={round(bullish_gap,5)}"
        )

    # ----------------------------------
    # BEARISH FVG
    # ----------------------------------

    bearish_gap = c1["low"] - c3["high"]

    if bearish_gap >= MIN_FVG_SIZE:

        fvg_list.append({
            "time": c3["time"],
            "type": "BEARISH_FVG",
            "top": round(c1["low"], 5),
            "bottom": round(c3["high"], 5),
            "gap_size": round(bearish_gap, 5)
        })

        print(
            f"BEARISH_FVG | "
            f"{c3['time']} | "
            f"{round(c3['high'],5)} -> "
            f"{round(c1['low'],5)} | "
            f"Gap={round(bearish_gap,5)}"
        )

# ==================================
# CREATE DATAFRAME
# ==================================

fvg_df = pd.DataFrame(fvg_list)

if not fvg_df.empty:

    fvg_df = fvg_df.drop_duplicates()

    # Largest gaps first
    fvg_df = fvg_df.sort_values(
    by="time"
)

# ==================================
# SAVE
# ==================================

fvg_df.to_csv(
    "../outputs/fvg_v2.csv",
    index=False
)

# ==================================
# SUMMARY
# ==================================

print("\nFVG Found:", len(fvg_df))

if not fvg_df.empty:

    print(
        "Largest Gap:",
        round(fvg_df["gap_size"].max(), 5)
    )

print("Saved: ../outputs/fvg_v2.csv")