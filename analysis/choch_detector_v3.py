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

df = pd.read_csv(
    f"../data/{PAIR}_{TIMEFRAME}.csv"
)

structure = pd.read_csv(
    "../outputs/market_structure_v4.csv"
)

print("\n===== CHOCH V3 =====\n")

trend = None

protected_HL = None
protected_LH = None

choch_count = 0
choch_events = []

# ==========================
# DETERMINE INITIAL TREND
# ==========================

for i in range(len(structure)):

    label = structure.iloc[i]["label"]

    if label == "HH":
        trend = "bullish"
        break

    elif label == "LL":
        trend = "bearish"
        break

# ==========================
# MAIN LOOP
# ==========================

for i in range(len(structure)):

    row = structure.iloc[i]

    label = row["label"]
    idx = int(row["index"])

    # =====================================
    # BULLISH TREND → LOOK FOR BEARISH CHOCH
    # =====================================

    if trend == "bullish":

        if label == "HL":
            protected_HL = row

        if protected_HL is not None:

            level = protected_HL["price"]

            for j in range(idx + 1, len(df)):

                if df.iloc[j]["close"] < level:

                    print(
                        f"BEARISH CHOCH | "
                        f"{df.iloc[j]['time']} | "
                        f"Below HL {round(level, 5)}"
                    )

                    choch_events.append({
                        "time": df.iloc[j]["time"],
                        "type": "BEARISH_CHOCH",
                        "price": level
                    })

                    choch_count += 1

                    trend = "bearish"

                    protected_HL = None
                    protected_LH = None

                    break

    # =====================================
    # BEARISH TREND → LOOK FOR BULLISH CHOCH
    # =====================================

    elif trend == "bearish":

        if label == "LH":
            protected_LH = row

        if protected_LH is not None:

            level = protected_LH["price"]

            for j in range(idx + 1, len(df)):

                if df.iloc[j]["close"] > level:

                    print(
                        f"BULLISH CHOCH | "
                        f"{df.iloc[j]['time']} | "
                        f"Above LH {round(level, 5)}"
                    )

                    choch_events.append({
                        "time": df.iloc[j]["time"],
                        "type": "BULLISH_CHOCH",
                        "price": level
                    })

                    choch_count += 1

                    trend = "bullish"

                    protected_HL = None
                    protected_LH = None

                    break

# ==========================
# SAVE CHOCH EVENTS
# ==========================

choch_df = pd.DataFrame(
    choch_events,
    columns=[
        "time",
        "type",
        "price"
    ]
)

choch_df.to_csv(
    "../outputs/choch_events.csv",
    index=False
)

# ==========================
# SUMMARY
# ==========================

print("\nStructure Points :", len(structure))
print("Total CHOCH :", choch_count)

print("\nSaved:")
print("../outputs/choch_events.csv")