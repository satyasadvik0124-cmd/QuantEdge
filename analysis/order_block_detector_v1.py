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
    "../outputs/validated_sweeps_v2.csv"
)

if sweeps_df.empty:
    print("No validated sweeps found.")
    exit()

sweeps_df["choch_time"] = pd.to_datetime(
    sweeps_df["choch_time"]
)

order_blocks = []

print("\n===== ORDER BLOCK DETECTOR V1 =====\n")

# ==================================
# FIND ORDER BLOCKS
# ==================================

for _, sweep in sweeps_df.iterrows():

    choch_time = sweep["choch_time"]
    sweep_type = sweep["type"]

    choch_rows = price_df[
        price_df["time"] == choch_time
    ]

    if choch_rows.empty:
        continue

    choch_idx = choch_rows.index[0]

    # Debug (first few only)
    if len(order_blocks) < 5:
        print(
            f"CHOCH={choch_time} | "
            f"TYPE={sweep_type} | "
            f"IDX={choch_idx}"
        )

    # ==================================
    # SSL_SWEEP -> BULLISH OB
    # Find last bearish candle
    # ==================================

    if sweep_type == "SSL_SWEEP":

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

                break

    # ==================================
    # BSL_SWEEP -> BEARISH OB
    # Find last bullish candle
    # ==================================

    elif sweep_type == "BSL_SWEEP":

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

                break

# ==================================
# DATAFRAME
# ==================================

ob_df = pd.DataFrame(order_blocks)

if not ob_df.empty:

    ob_df = ob_df.drop_duplicates()

    ob_df = (
        ob_df
        .sort_values(by="time")
        .reset_index(drop=True)
    )

# ==================================
# SAVE
# ==================================

ob_df.to_csv(
    "../outputs/order_blocks_v1.csv",
    index=False
)

# ==================================
# REPORT
# ==================================

bullish_ob = 0
bearish_ob = 0

if not ob_df.empty:

    bullish_ob = len(
        ob_df[
            ob_df["type"] == "BULLISH_OB"
        ]
    )

    bearish_ob = len(
        ob_df[
            ob_df["type"] == "BEARISH_OB"
        ]
    )

print("\n===== ORDER BLOCK REPORT =====\n")

print(
    f"Bullish Order Blocks : "
    f"{bullish_ob:,}"
)

print(
    f"Bearish Order Blocks : "
    f"{bearish_ob:,}"
)

print(
    f"Total Order Blocks   : "
    f"{len(ob_df):,}"
)

if len(sweeps_df) > 0:

    print(
        f"OB Conversion Rate   : "
        f"{(len(ob_df) / len(sweeps_df)) * 100:.2f}%"
    )

print("\nSaved:")
print("../outputs/order_blocks_v1.csv")