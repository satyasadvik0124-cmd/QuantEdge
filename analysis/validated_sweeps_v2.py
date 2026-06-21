import pandas as pd

# ==========================
# LOAD DATA
# ==========================

sweeps = pd.read_csv("../outputs/liquidity_sweeps_v1.csv")
choch = pd.read_csv("../outputs/choch_events.csv")

sweeps["time"] = pd.to_datetime(sweeps["time"])
choch["time"] = pd.to_datetime(choch["time"])

# ==========================
# SETTINGS
# ==========================

LOOKAHEAD_MINUTES = 150  # 10 M15 candles

validated = []

# ==========================
# VALIDATION LOGIC
# ==========================

for _, sweep in sweeps.iterrows():

    sweep_time = sweep["time"]
    sweep_type = sweep["type"]

    if sweep_type == "BSL_SWEEP":
        target_choch = "BULLISH_CHOCH"

    elif sweep_type == "SSL_SWEEP":
        target_choch = "BEARISH_CHOCH"

    else:
        continue

    matching_choch = choch[
        (choch["type"] == target_choch)
        &
        (choch["time"] >= sweep_time)
        &
        (
            choch["time"]
            <= sweep_time + pd.Timedelta(minutes=LOOKAHEAD_MINUTES)
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

# ==========================
# SAVE
# ==========================

validated_df = pd.DataFrame(validated)

validated_df.to_csv(
    "../outputs/validated_sweeps_v2.csv",
    index=False
)

print("\n===== VALIDATED SWEEPS V2 =====")
print("Total:", len(validated_df))

print(validated_df.head())

print(
    "\nSaved to outputs/validated_sweeps_v2.csv"
)