import pandas as pd
import os

# ==================================
# CONFIG
# ==================================

LOOKAHEAD_MINUTES = 150  # 10 M15 candles

# ==================================
# LOAD DATA
# ==================================

sweeps_file = "../outputs/liquidity_sweeps_v2.csv"
choch_file = "../outputs/choch_events.csv"

if not os.path.exists(sweeps_file):
    print(f"Missing: {sweeps_file}")
    exit()

if not os.path.exists(choch_file):
    print(f"Missing: {choch_file}")
    exit()

sweeps = pd.read_csv(sweeps_file)
choch = pd.read_csv(choch_file)

if sweeps.empty:
    print("No liquidity sweeps found.")
    exit()

if choch.empty:
    print("No CHOCH events found.")
    exit()

sweeps["time"] = pd.to_datetime(
    sweeps["time"]
)

choch["time"] = pd.to_datetime(
    choch["time"]
)

# ==================================
# VALIDATION LOGIC
# ==================================

validated = []

bullish_validated = 0
bearish_validated = 0

for _, sweep in sweeps.iterrows():

    sweep_time = sweep["time"]
    sweep_type = sweep["type"]

    if sweep_type == "BSL_SWEEP":
        target_choch = "BEARISH_CHOCH"

    elif sweep_type == "SSL_SWEEP":
        target_choch = "BULLISH_CHOCH"

    else:
        continue

    matching_choch = choch[
        (choch["type"] == target_choch)
        &
        (choch["time"] >= sweep_time)
        &
        (
            choch["time"]
            <= sweep_time
            + pd.Timedelta(
                minutes=LOOKAHEAD_MINUTES
            )
        )
    ]

    if not matching_choch.empty:

        first_choch = matching_choch.iloc[0]

        validated.append({
            "sweep_time": sweep_time,
            "choch_time": first_choch["time"],
            "type": sweep_type,
            "price": sweep["price"]
        })

        if sweep_type == "BSL_SWEEP":
            bearish_validated += 1

        elif sweep_type == "SSL_SWEEP":
            bullish_validated += 1

# ==================================
# SAVE
# ==================================

validated_df = pd.DataFrame(
    validated
)

if not validated_df.empty:

    validated_df = (
        validated_df
        .drop_duplicates(
            subset=[
                "sweep_time",
                "type"
            ]
        )
    )

validated_df.to_csv(
    "../outputs/validated_sweeps_v2.csv",
    index=False
)

# ==================================
# REPORT
# ==================================

print("\n===== VALIDATED SWEEPS V2 =====\n")

print(
    f"Bullish Validated Sweeps : "
    f"{bullish_validated:,}"
)

print(
    f"Bearish Validated Sweeps : "
    f"{bearish_validated:,}"
)

print(
    f"Total Validated Sweeps   : "
    f"{len(validated_df):,}"
)

print()

if len(sweeps) > 0:

    print(
        f"Validation Rate          : "
        f"{(len(validated_df) / len(sweeps)) * 100:.2f}%"
    )

print(
    "\nSaved:"
)

print(
    "../outputs/validated_sweeps_v2.csv"
)