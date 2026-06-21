import pandas as pd

# ==================================
# LOAD DATA
# ==================================

price_df = pd.read_csv("../data/EURUSD_M15.csv")
price_df["time"] = pd.to_datetime(price_df["time"])

sweeps_df = pd.read_csv(
    "../outputs/validated_sweeps_v1.csv"
)
print("\nSweep Types:")
print(sweeps_df["type"].value_counts())

sweeps_df["choch_time"] = pd.to_datetime(
    sweeps_df["choch_time"]
)

order_blocks = []

print("\n===== ORDER BLOCKS V1 =====\n")

# ==================================
# FIND ORDER BLOCKS
# ==================================

for _, sweep in sweeps_df.iterrows():

    choch_time = sweep["choch_time"]
    sweep_type = sweep["type"]

    # Get CHOCH candle index
    choch_rows = price_df[
        price_df["time"] == choch_time
    ]

    if choch_rows.empty:
        continue

    choch_idx = choch_rows.index[0]

    # ------------------------------
    # VALID BULLISH SWEEP
    # Find last bearish candle
    # ------------------------------

    if sweep_type == "VALID_BULLISH_SWEEP":

        for i in range(choch_idx - 1, max(0, choch_idx - 20), -1):

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
                    f"{round(candle['low'],5)} - "
                    f"{round(candle['high'],5)}"
                )

                break

    # ------------------------------
    # VALID BEARISH SWEEP
    # Find last bullish candle
    # ------------------------------

    elif sweep_type == "VALID_BEARISH_SWEEP":

        for i in range(choch_idx - 1, max(0, choch_idx - 20), -1):

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
                    f"{round(candle['low'],5)} - "
                    f"{round(candle['high'],5)}"
                )

                break

# ==================================
# SAVE
# ==================================

ob_df = pd.DataFrame(order_blocks)

if not ob_df.empty:
    ob_df = ob_df.drop_duplicates()

ob_df.to_csv(
    "../outputs/order_blocks_v1.csv",
    index=False
)

# ==================================
# SUMMARY
# ==================================

print("\nOrder Blocks Found:", len(ob_df))
print("Saved: ../outputs/order_blocks_v1.csv")
