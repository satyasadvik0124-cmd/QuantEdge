import pandas as pd

# ----------------------------
# Load Data
# ----------------------------
price_df = pd.read_csv("../data/EURUSD_M15.csv")
price_df["time"] = pd.to_datetime(price_df["time"])
liq_df = pd.read_csv("../outputs/liquidity_v2.csv")
liq_df["time"] = pd.to_datetime(liq_df["time"])

sweeps = []

# ----------------------------
# Process Liquidity Levels
# ----------------------------

for _, level in liq_df.iterrows():

    level_time = level["time"]
    level_price = level["price"]
    level_type = level["type"]

    future_candles = price_df[
        price_df["time"] > level_time
    ]

    for _, candle in future_candles.iterrows():

        # ------------------------
        # Buy Side Sweep
        # ------------------------

        if level_type == "EQH":

            if (
                candle["high"] > level_price
                and
                candle["close"] < level_price
            ):

                sweeps.append({
                    "time": candle["time"],
                    "type": "BSL_SWEEP",
                    "price": level_price
                })

                print(
                    f"BSL SWEEP | "
                    f"{candle['time']} | "
                    f"Above EQH {level_price}"
                )

                break

        # ------------------------
        # Sell Side Sweep
        # ------------------------

        elif level_type == "EQL":

            if (
                candle["low"] < level_price
                and
                candle["close"] > level_price
            ):

                sweeps.append({
                    "time": candle["time"],
                    "type": "SSL_SWEEP",
                    "price": level_price
                })

                print(
                    f"SSL SWEEP | "
                    f"{candle['time']} | "
                    f"Below EQL {level_price}"
                )

                break

# ----------------------------
# Save Results
# ----------------------------

sweep_df = pd.DataFrame(sweeps)

sweep_df.to_csv(
    "../outputs/liquidity_sweeps_v1.csv",
    index=False
)
print("\nTotal Sweeps:", len(sweep_df))
print("Saved: ../outputs/liquidity_sweeps_v1.csv")