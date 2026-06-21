import pandas as pd

# ==================================
# LOAD DATA
# ==================================

sweeps = pd.read_csv(
    "../outputs/validated_sweeps_v2.csv"
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

print("\n===== SIGNAL GENERATOR V3 =====\n")

# ==================================
# GENERATE SIGNALS
# ==================================

for _, sweep in sweeps.iterrows():

    sweep_type = sweep["type"]
    choch_time = sweep["choch_time"]

    # ==================================
    # SSL_SWEEP -> BUY SIGNAL
    # ==================================

    if sweep_type == "SSL_SWEEP":

        matching_obs = obs[
            (obs["type"] == "BULLISH_OB")
            &
            (obs["time"] <= choch_time)
        ]

        if matching_obs.empty:
            continue

        matching_obs = matching_obs.copy()

        matching_obs["distance"] = (
            choch_time - matching_obs["time"]
        )

        matching_obs = matching_obs[
            matching_obs["distance"]
            <= pd.Timedelta(days=7)
        ]

        if matching_obs.empty:
            continue

        ob = matching_obs.sort_values(
            by="distance"
        ).iloc[0]

        matching_fvgs = fvgs[
            (fvgs["type"] == "BULLISH_FVG")
            &
            (fvgs["time"] >= ob["time"])
            &
            (
                fvgs["time"]
                <= ob["time"] + pd.Timedelta(days=7)
            )
        ]

        if matching_fvgs.empty:
            continue

        entry = ob["high"]
        sl = ob["low"]

        risk = entry - sl

        if risk <= 0:
            continue

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
    # BSL_SWEEP -> SELL SIGNAL
    # ==================================

    elif sweep_type == "BSL_SWEEP":

        matching_obs = obs[
            (obs["type"] == "BEARISH_OB")
            &
            (obs["time"] <= choch_time)
        ]

        if matching_obs.empty:
            continue

        matching_obs = matching_obs.copy()

        matching_obs["distance"] = (
            choch_time - matching_obs["time"]
        )

        matching_obs = matching_obs[
            matching_obs["distance"]
            <= pd.Timedelta(days=7)
        ]

        if matching_obs.empty:
            continue

        ob = matching_obs.sort_values(
            by="distance"
        ).iloc[0]

        matching_fvgs = fvgs[
            (fvgs["type"] == "BEARISH_FVG")
            &
            (fvgs["time"] >= ob["time"])
            &
            (
                fvgs["time"]
                <= ob["time"] + pd.Timedelta(days=7)
            )
        ]

        if matching_fvgs.empty:
            continue

        entry = ob["low"]
        sl = ob["high"]

        risk = sl - entry

        if risk <= 0:
            continue

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

    signals_df = (
        signals_df
        .drop_duplicates()
        .sort_values(by="signal_time")
        .reset_index(drop=True)
    )

# ==================================
# SAVE
# ==================================

signals_df.to_csv(
    "../outputs/signals_v3.csv",
    index=False
)

# ==================================
# REPORT
# ==================================

bullish_signals = 0
bearish_signals = 0

if not signals_df.empty:

    bullish_signals = len(
        signals_df[
            signals_df["direction"] == "BUY"
        ]
    )

    bearish_signals = len(
        signals_df[
            signals_df["direction"] == "SELL"
        ]
    )

print("\n===== SIGNAL REPORT =====\n")

print(
    f"Bullish Signals : "
    f"{bullish_signals:,}"
)

print(
    f"Bearish Signals : "
    f"{bearish_signals:,}"
)

print(
    f"Total Signals   : "
    f"{len(signals_df):,}"
)

if len(sweeps) > 0:

    print(
        f"Signal Rate     : "
        f"{(len(signals_df) / len(sweeps)) * 100:.2f}%"
    )

print("\nSaved:")
print("../outputs/signals_v3.csv")