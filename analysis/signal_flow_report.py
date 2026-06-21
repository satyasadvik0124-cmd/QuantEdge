import pandas as pd
import os

files = {
    "Validated Sweeps": "../outputs/validated_sweeps_v2.csv",
    "Order Blocks": "../outputs/order_blocks_v1.csv",
    "FVGs": "../outputs/fvg_v2.csv",
    "Signals": "../outputs/signals_v3.csv",
    "Backtest Trades": "../outputs/backtest_results_v1.csv"
}

print("\n===== QUANTEDGE FLOW REPORT =====\n")

for name, path in files.items():

    if not os.path.exists(path):
        print(f"{name:<20}: File Missing")
        continue

    try:
        df = pd.read_csv(path)
        print(f"{name:<20}: {len(df)}")

    except Exception as e:
        print(f"{name:<20}: ERROR -> {e}")