import pandas as pd

# ==================================
# LOAD DATA
# ==================================

sweeps = pd.read_csv(
    "../outputs/validated_sweeps_v1.csv"
)

obs = pd.read_csv(
    "../outputs/order_blocks_v1.csv"
)

fvgs = pd.read_csv(
    "../outputs/fvg_v2.csv"
)

sweeps["choch_time"] = pd.to_datetime(
    sweeps["choch_time"]
)

obs["time"] = pd.to_datetime(
    obs["time"]
)

fvgs["time"] = pd.to_datetime(
    fvgs["time"]
)

signals = []

print("\n===== SIGNALS V3 =====")

print("\nOrder Blocks:")
print(obs)

print("\nFVG Counts:")
print(fvgs["type"].value_counts())

# ==================================
# GENERATE SIGNALS
# ==================================

for _, sweep in sweeps.iterrows():

    sweep_type = sweep["type"]
    choch_time = sweep["choch_time"]

    # ==================================
    # VALID BULLISH SWEEP
    # ==================================

    if sweep_type == "VALID_BULLISH_SWEEP":

        print("\n====================")
        print("CHOCH:", choch_time)

        matching_obs = obs[
            (obs["type"] == "BULLISH_OB")
            &
            (obs["time"] <= choch_time)
        ]

        print(
            "Matching OBs:",
            len(matching_obs)
        )

        if matching_obs.empty:
            continue

        # Latest OB before CHOCH
        ob = matching_obs.sort_values(
            by="time"
        ).iloc[-1]

        print("OB Time:", ob["time"])
        print("OB Type:", ob["type"])

        matching_fvgs = fvgs[
            (fvgs["type"] == "BULLISH_FVG")
            &
            (fvgs["time"] >= ob["time"])
            &
            (
                fvgs["time"]
                <= ob["time"] + pd.Timedelta(hours=24)
            )
        ]

        print(
            "Bullish FVGs Found:",
            len(matching_fvgs)
        )

        if matching_fvgs.empty:
            continue

        entry = ob["high"]
        sl = ob["low"]

        risk = entry - sl

        tp = entry + (risk * 3)

        signals.append({
            "signal_time": ob["time"],
            "direction": "BUY",
            "entry": round(entry, 5),
            "sl": round(sl, 5),
            "tp": round(tp, 5),
            "risk": round(risk, 5),
            "reward": round(risk * 3, 5),
            "rr": 3
        })

    # ==================================
    # VALID BEARISH SWEEP
    # ==================================

    elif sweep_type == "VALID_BEARISH_SWEEP":

        print("\n====================")
        print("CHOCH:", choch_time)

        matching_obs = obs[
            (obs["type"] == "BEARISH_OB")
            &
            (obs["time"] <= choch_time)
        ]

        print(
            "Matching OBs:",
            len(matching_obs)
        )

        if matching_obs.empty:
            continue

        # Latest OB before CHOCH
        ob = matching_obs.sort_values(
            by="time"
        ).iloc[-1]

        print("OB Time:", ob["time"])
        print("OB Type:", ob["type"])

        matching_fvgs = fvgs[
            (fvgs["type"] == "BEARISH_FVG")
            &
            (fvgs["time"] >= ob["time"])
            &
            (
                fvgs["time"]
                <= ob["time"] + pd.Timedelta(hours=24)
            )
        ]

        print(
            "Bearish FVGs Found:",
            len(matching_fvgs)
        )

        if matching_fvgs.empty:
            continue

        entry = ob["low"]
        sl = ob["high"]

        risk = sl - entry

        tp = entry - (risk * 3)

        signals.append({
            "signal_time": ob["time"],
            "direction": "SELL",
            "entry": round(entry, 5),
            "sl": round(sl, 5),
            "tp": round(tp, 5),
            "risk": round(risk, 5),
            "reward": round(risk * 3, 5),
            "rr": 3
        })

# ==================================
# DATAFRAME
# ==================================

signals_df = pd.DataFrame(signals)

if not signals_df.empty:

    signals_df = signals_df.drop_duplicates()

    signals_df = signals_df.sort_values(
        by="signal_time"
    ).reset_index(drop=True)

# ==================================
# SAVE
# ==================================

signals_df.to_csv(
    "../outputs/signals_v3.csv",
    index=False
)

# ==================================
# SUMMARY
# ==================================

print("\n====================")
print(
    "Signals Found:",
    len(signals_df)
)

if not signals_df.empty:
    print(signals_df)

print(
    "\nSaved: ../outputs/signals_v3.csv"
)