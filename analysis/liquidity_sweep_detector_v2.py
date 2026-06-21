import pandas as pd
import os

# ==================================
# CONFIG
# ==================================

LOOKAHEAD_HOURS = 24

# ==================================
# LOAD DATA
# ==================================

sweeps_file = "../outputs/liquidity_sweeps_v1.csv"
choch_file = "../outputs/choch_events.csv"

if not os.path.exists(sweeps_file):
    print(f"Missing: {sweeps_file}")
    exit()

if not os.path.exists(choch_file):
    print(f"Missing: {choch_file}")
    exit()

sweeps_df = pd.read_csv(sweeps_file)
choch_df = pd.read_csv(choch_file)

if sweeps_df.empty:
    print("No liquidity sweeps found.")
    exit()

if choch_df.empty:
    print("No CHOCH events found.")
    exit()

sweeps_df["time"] = pd.to_datetime(sweeps_df["time"])
choch_df["time"] = pd.to_datetime(choch_df["time"])

validated_sweeps = []

# ==================================
# VALIDATION LOGIC
# ==================================

for _, sweep in sweeps_df.iterrows():

    sweep_time = sweep["time"]
    sweep_type = sweep["type"]

    window_end = sweep_time + pd.Timedelta(
        hours=LOOKAHEAD_HOURS
    )

    future_choch = choch_df[
        (choch_df["time"] > sweep_time)
        &
        (choch_df["time"] <= window_end)
    ]

    # ----------------------------------
    # BSL Sweep -> Bearish CHOCH
    # ----------------------------------

    if sweep_type == "BSL_SWEEP":

        bearish_choch = future_choch[
            future_choch["type"]
            == "BEARISH_CHOCH"
        ]

        if not bearish_choch.empty:

            choch = bearish_choch.iloc[0]

            validated_sweeps.append({
                "sweep_time": sweep_time,
                "choch_time": choch["time"],
                "type": "VALID_BEARISH_SWEEP",
                "price": sweep["price"]
            })

    # ----------------------------------
    # SSL Sweep -> Bullish CHOCH
    # ----------------------------------

    elif sweep_type == "SSL_SWEEP":

        bullish_choch = future_choch[
            future_choch["type"]
            == "BULLISH_CHOCH"
        ]

        if not bullish_choch.empty:

            choch = bullish_choch.iloc[0]

            validated_sweeps.append({
                "sweep_time": sweep_time,
                "choch_time": choch["time"],
                "type": "VALID_BULLISH_SWEEP",
                "price": sweep["price"]
            })

# ==================================
# SAVE
# ==================================

validated_df = pd.DataFrame(
    validated_sweeps
)

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