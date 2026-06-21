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

# ==========================
# LOAD DATA
# ==========================

df = pd.read_csv(
    f"../data/{PAIR}_{TIMEFRAME}.csv"
)

structure = pd.read_csv(
    "../outputs/market_structure_v4.csv"
)

# Fast arrays
close_prices = df["close"].values
times = df["time"].values

print("\n===== CHOCH V3 =====\n")

trend = None

protected_HL = None
protected_LH = None

choch_count = 0
bullish_choch_count = 0
bearish_choch_count = 0

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

print(f"Initial Trend: {trend}")

# ==========================
# MAIN LOOP
# ==========================
# ==========================

# MAIN LOOP (FIXED)

# ==========================
# MAIN LOOP
# ==========================

LOOKAHEAD = 500

for i in range(len(structure)):

    row = structure.iloc[i]

    label = row["label"]
    idx = int(row["index"])

    # --------------------------
    # Store protected levels
    # --------------------------

    if label == "HL":
        protected_HL = row

    elif label == "LH":
        protected_LH = row

    # --------------------------
    # Bullish -> Bearish CHOCH
    # --------------------------

    if trend == "bullish":

        if protected_HL is not None:

            level = protected_HL["price"]

            for j in range(
                idx + 1,
                min(idx + LOOKAHEAD, len(close_prices))
            ):

                if close_prices[j] < level:

                    choch_events.append({
                        "time": times[j],
                        "type": "BEARISH_CHOCH",
                        "price": level
                    })

                    choch_count += 1
                    bearish_choch_count += 1

                    trend = "bearish"

                    protected_HL = None
                    protected_LH = None

                    break

    # --------------------------
    # Bearish -> Bullish CHOCH
    # --------------------------

    elif trend == "bearish":

        if protected_LH is not None:

            level = protected_LH["price"]

            for j in range(
                idx + 1,
                min(idx + LOOKAHEAD, len(close_prices))
            ):

                if close_prices[j] > level:

                    choch_events.append({
                        "time": times[j],
                        "type": "BULLISH_CHOCH",
                        "price": level
                    })

                    choch_count += 1
                    bullish_choch_count += 1

                    trend = "bullish"

                    protected_HL = None
                    protected_LH = None

                    break
# --------------------------
# Bearish -> Bullish CHOCH
# --------------------------

    elif trend == "bearish":

       if protected_LH is not None:

        level = protected_LH["price"]

        if close_prices[idx] > level:

            choch_events.append({
                "time": times[idx],
                "type": "BULLISH_CHOCH",
                "price": level
            })

            choch_count += 1
            bullish_choch_count += 1

            trend = "bullish"

            protected_HL = None
            protected_LH = None



# ==========================
# SAVE EVENTS
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
# REPORT
# ==========================

print("\n===== CHOCH REPORT =====\n")

print(
    f"Structure Points : "
    f"{len(structure):,}"
)

print(
    f"Bullish CHOCH    : "
    f"{bullish_choch_count:,}"
)

print(
    f"Bearish CHOCH    : "
    f"{bearish_choch_count:,}"
)

print(
    f"Total CHOCH      : "
    f"{choch_count:,}"
)

if len(structure) > 0:

    print(
        f"CHOCH Ratio      : "
        f"{(choch_count / len(structure)) * 100:.2f}%"
    )

print("\nSaved:")
print("../outputs/choch_events.csv")