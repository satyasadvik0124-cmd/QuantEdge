import os

files = [
    "swing_detector_v3.py",
    "market_structure_v4.py",
    "choch_detector_v3.py",
    "liquidity_detector_v2.py",
    "liquidity_sweep_detector_v2.py",
    "validated_sweeps_v2.py",
    "order_block_detector_v1.py",
    "fvg_detector_v2.py",
    "signal_generator_v3.py",
    "backtest_v1.py",
    "equity_curve_v1.py",
    "drawdown_analyzer_v1.py",
    "performance_analyzer_v1.py"
]

print("\n===== QUANTEDGE PIPELINE =====\n")

for file in files:

    print(f"\n{'='*50}")
    print(f"RUNNING: {file}")
    print(f"{'='*50}\n")

    exit_code = os.system(
        f"python {file}"
    )

    if exit_code != 0:

        print(
            f"\n❌ ERROR IN: {file}"
        )

        break

print("\n✅ PIPELINE COMPLETE")