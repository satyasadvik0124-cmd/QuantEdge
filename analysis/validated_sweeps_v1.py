import pandas as pd

# ==================================
# CONFIG
# ==================================

LOOKAHEAD_HOURS = 5

# ==================================
# LOAD DATA
# ==================================

sweeps_df = pd.read_csv(
    "../outputs/liquidity_sweeps_v1.csv"
)
choch_df = pd.read_csv(
    "../outputs/choch_events.csv"
)

sweeps_df["time"] = pd.to_datetime(sweeps_df["time"])
choch_df["time"] = pd.to_datetime(choch_df["time"])

validated_sweeps = []

# ==================================
# VALIDATION
# ==================================

for _, sweep in sweeps_df.iterrows():

    sweep_time = sweep["time"]
    sweep_type = sweep["type"]

    window_end = sweep_time + pd.Timedelta(hours=LOOKAHEAD_HOURS)

    future_choch = choch_df[
        (choch_df["time"] > sweep_time) &
        (choch_df["time"] <= window_end)
    ]

    # ----------------------------------
    # BSL Sweep -> Bearish CHOCH
    # ----------------------------------

    if sweep_type == "BSL_SWEEP":

        bearish_choch = future_choch[
            future_choch["type"] == "BEARISH_CHOCH"
        ]

        if not bearish_choch.empty:

            first_choch = bearish_choch.iloc[0]

            validated_sweeps.append({
                "sweep_time": sweep_time,
                "choch_time": first_choch["time"],
                "type": "VALID_BEARISH_SWEEP",
                "price": sweep["price"]
            })

            print(
                f"VALID_BEARISH_SWEEP | "
                f"Sweep: {sweep_time} | "
                f"CHOCH: {first_choch['time']}"
            )

    # ----------------------------------
    # SSL Sweep -> Bullish CHOCH
    # ----------------------------------

    elif sweep_type == "SSL_SWEEP":

        bullish_choch = future_choch[
            future_choch["type"] == "BULLISH_CHOCH"
        ]

        if not bullish_choch.empty:

            first_choch = bullish_choch.iloc[0]

            validated_sweeps.append({
                "sweep_time": sweep_time,
                "choch_time": first_choch["time"],
                "type": "VALID_BULLISH_SWEEP",
                "price": sweep["price"]
            })

            print(
                f"VALID_BULLISH_SWEEP | "
                f"Sweep: {sweep_time} | "
                f"CHOCH: {first_choch['time']}"
            )

# ==================================
# SAVE RESULTS
# ==================================

validated_df = pd.DataFrame(validated_sweeps)

# Remove duplicate validated sweeps
if not validated_df.empty:

    validated_df = validated_df.drop_duplicates(
        subset=["sweep_time", "type"]
    )

validated_df.to_csv(
    "../outputs/validated_sweeps_v1.csv",
    index=False
)
# ==================================
# SUMMARY
# ==================================

print("\nTotal Validated Sweeps:", len(validated_df))
print("Saved: ../outputs/validated_sweeps_v1.csv")