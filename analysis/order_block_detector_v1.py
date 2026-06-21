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

price_df = pd.read_csv(
    f"../data/{PAIR}_{TIMEFRAME}.csv"
)

price_df["time"] = pd.to_datetime(
    price_df["time"]
)

sweeps_df = pd.read_csv(
    "../outputs/validated_sweeps_v1.csv"
)

print("\nSweep Types:")
print(sweeps_df["type"].value_counts())

sweeps_df["choch_time"] = pd.to_datetime(
    sweeps_df["choch_time"]
)

order_blocks = []

print("\n===== ORDER BLOCKS V2 =====\n")

# ==================================
# FIND ORDER BLOCKS
# ==================================

for _, sweep in sweeps_df.iterrows():

    choch_time = sweep["choch_time"]
    sweep_type = sweep["type"]

    # Find CHOCH candle

    choch_rows = price_df[
        price_df["time"] == choch_time
    ]

    if choch_rows.empty:
        continue

    choch_idx = choch_rows.index[0]

    # ==================================
    # VALID_BULLISH_SWEEP
    # -> Find last bearish candle
    # -> BULLISH OB
    # ==================================

    if sweep_type == "VALID_BULLISH_SWEEP":

        for i in range(
            choch_idx - 1,
            max(0, choch_idx - 20),
            -1
        ):

            candle = price_df.iloc[i]

            if candle["close"] < candle["open"]:

                order_blocks.append({
                    "time": candle["time"],
                    "type": "BULLISH_OB",
                    "high": candle["high"],
                    "low": candle["low"]
                })

                print(
                    f"BULLISH_OB | "
                    f"{candle['time']} | "
                    f"{round(candle['low'], 5)} - "
                    f"{round(candle['high'], 5)}"
                )

                break

    # ==================================
    # VALID_BEARISH_SWEEP
    # -> Find last bullish candle
    # -> BEARISH OB
    # ==================================

    elif sweep_type == "VALID_BEARISH_SWEEP":

        for i in range(
            choch_idx - 1,
            max(0, choch_idx - 20),
            -1
        ):

            candle = price_df.iloc[i]

            if candle["close"] > candle["open"]:

                order_blocks.append({
                    "time": candle["time"],
                    "type": "BEARISH_OB",
                    "high": candle["high"],
                    "low": candle["low"]
                })

                print(
                    f"BEARISH_OB | "
                    f"{candle['time']} | "
                    f"{round(candle['low'], 5)} - "
                    f"{round(candle['high'], 5)}"
                )

                break

# ==================================
# DATAFRAME
# ==================================

ob_df = pd.DataFrame(order_blocks)

if not ob_df.empty:

    ob_df = ob_df.drop_duplicates()

    ob_df = ob_df.sort_values(
        by="time"
    ).reset_index(drop=True)

# ==================================
# SAVE
# ==================================

ob_df.to_csv(
    "../outputs/order_blocks_v1.csv",
    index=False
)

# ==================================
# SUMMARY
# ==================================

print("\n===== SUMMARY =====")

print(
    "Order Blocks Found:",
    len(ob_df)
)

if not ob_df.empty:

    print("\nType Counts:")

    print(
        ob_df["type"].value_counts()
    )

print(
    "\nSaved: ../outputs/order_blocks_v1.csv"
)