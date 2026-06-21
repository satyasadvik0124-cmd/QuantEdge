import pandas as pd

# ==================================
# LOAD DATA
# ==================================

df = pd.read_csv("../data/EURUSD_M15.csv")

fvg_list = []

print("\n===== FVG DETECTOR V1 =====\n")

# ==================================
# DETECT FVG
# ==================================

for i in range(2, len(df)):

    c1 = df.iloc[i - 2]
    c2 = df.iloc[i - 1]
    c3 = df.iloc[i]

    # --------------------------
    # Bullish FVG
    # --------------------------

    if c1["high"] < c3["low"]:

        fvg_list.append({
            "time": c3["time"],
            "type": "BULLISH_FVG",
            "top": c3["low"],
            "bottom": c1["high"]
        })

        print(
            f"BULLISH_FVG | "
            f"{c3['time']} | "
            f"{round(c1['high'],5)} -> "
            f"{round(c3['low'],5)}"
        )

    # --------------------------
    # Bearish FVG
    # --------------------------

    elif c1["low"] > c3["high"]:

        fvg_list.append({
            "time": c3["time"],
            "type": "BEARISH_FVG",
            "top": c1["low"],
            "bottom": c3["high"]
        })

        print(
            f"BEARISH_FVG | "
            f"{c3['time']} | "
            f"{round(c3['high'],5)} -> "
            f"{round(c1['low'],5)}"
        )

# ==================================
# SAVE
# ==================================

fvg_df = pd.DataFrame(fvg_list)

if not fvg_df.empty:
    fvg_df = fvg_df.drop_duplicates()

fvg_df.to_csv(
    "../outputs/fvg_v1.csv",
    index=False
)

# ==================================
# SUMMARY
# ==================================

print("\nFVG Found:", len(fvg_df))
print("Saved: ../outputs/fvg_v1.csv")