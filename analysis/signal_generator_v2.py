import pandas as pd

# ==================================
# SETTINGS
# ==================================

RR = 3

MIN_STOP = 0.0003    # 5 pips
MIN_FVG_GAP = 0.0007   # 7 pips

# ==================================
# LOAD FILES
# ==================================

sweeps_df = pd.read_csv(
    "../outputs/validated_sweeps_v1.csv"
)

ob_df = pd.read_csv(
    "../outputs/order_blocks_v1.csv"
)

fvg_df = pd.read_csv(
    "../outputs/fvg_v2.csv"
)

# ==================================
# DATETIME
# ==================================

sweeps_df["choch_time"] = pd.to_datetime(
    sweeps_df["choch_time"]
)

ob_df["time"] = pd.to_datetime(
    ob_df["time"]
)

fvg_df["time"] = pd.to_datetime(
    fvg_df["time"]
)

signals = []

print("\n===== SIGNAL GENERATOR V2 =====\n")

# ==================================
# MAIN LOOP
# ==================================

for _, sweep in sweeps_df.iterrows():

    choch_time = sweep["choch_time"]
    sweep_type = sweep["type"]

    # ==================================
    # BULLISH SETUP
    # ==================================

    if sweep_type == "VALID_BULLISH_SWEEP":

        bullish_obs = ob_df[
            (ob_df["type"] == "BULLISH_OB") &
            (ob_df["time"] <= choch_time)
        ]

        bullish_fvg = fvg_df[
            (fvg_df["type"] == "BULLISH_FVG") &
            (fvg_df["time"] <= choch_time) &
            (fvg_df["gap_size"] >= MIN_FVG_GAP)
        ]

        if bullish_obs.empty:
            continue

        if bullish_fvg.empty:
            continue

        ob = bullish_obs.iloc[-1]

        entry = (ob["high"] + ob["low"]) / 2

        sl = ob["low"]

        risk = entry - sl

        # ----------------------------------
        # Minimum Stop Filter
        # ----------------------------------

        if risk < MIN_STOP:
            continue

        reward = risk * RR

        tp = entry + reward

        signals.append({
            "signal_time": choch_time,
            "direction": "BUY",

            "entry": round(entry, 5),
            "sl": round(sl, 5),
            "tp": round(tp, 5),

            "risk": round(risk, 5),
            "reward": round(reward, 5),

            "rr": RR
        })

        print(
            f"BUY | {choch_time} | "
            f"Entry={round(entry,5)} | "
            f"SL={round(sl,5)} | "
            f"TP={round(tp,5)}"
        )

    # ==================================
    # BEARISH SETUP
    # ==================================

    elif sweep_type == "VALID_BEARISH_SWEEP":

        bearish_obs = ob_df[
            (ob_df["type"] == "BEARISH_OB") &
            (ob_df["time"] <= choch_time)
        ]

        bearish_fvg = fvg_df[
            (fvg_df["type"] == "BEARISH_FVG") &
            (fvg_df["time"] <= choch_time) &
            (fvg_df["gap_size"] >= MIN_FVG_GAP)
        ]

        if bearish_obs.empty:
            continue

        if bearish_fvg.empty:
            continue

        ob = bearish_obs.iloc[-1]

        entry = (ob["high"] + ob["low"]) / 2

        sl = ob["high"]

        risk = sl - entry

        # ----------------------------------
        # Minimum Stop Filter
        # ----------------------------------

        if risk < MIN_STOP:
            continue

        reward = risk * RR

        tp = entry - reward

        signals.append({
            "signal_time": choch_time,
            "direction": "SELL",

            "entry": round(entry, 5),
            "sl": round(sl, 5),
            "tp": round(tp, 5),

            "risk": round(risk, 5),
            "reward": round(reward, 5),

            "rr": RR
        })

        print(
            f"SELL | {choch_time} | "
            f"Entry={round(entry,5)} | "
            f"SL={round(sl,5)} | "
            f"TP={round(tp,5)}"
        )

# ==================================
# SAVE
# ==================================

signals_df = pd.DataFrame(signals)

if not signals_df.empty:
    signals_df = signals_df.drop_duplicates()

signals_df.to_csv(
    "../outputs/signals_v2.csv",
    index=False
)

# ==================================
# SUMMARY
# ==================================

print("\nSignals Generated:", len(signals_df))

if not signals_df.empty:

    print(
        "Average Risk:",
        round(signals_df["risk"].mean(), 5)
    )

print("Saved: ../outputs/signals_v2.csv")