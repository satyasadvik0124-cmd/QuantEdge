from pathlib import Path
import shutil
import subprocess
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / "outputs" / "multi_pair_5y"
DATA = ROOT / "data"
ANALYSIS = ROOT / "analysis"
PAIRS = {
    "GBPUSD": DATA / "GBPUSD_M15_5Y.csv",
    "XAUUSD": DATA / "XAUUSD_M15_5Y.csv",
}
PIPELINE = [
    "market_structure_v4.py",
    "choch_detector_v3.py",
    "liquidity_detector_v2.py",
    "liquidity_sweep_detector_v2.py",
    "validated_sweeps_v2.py",
    "order_block_detector_v1.py",
    "fvg_detector_v2.py",
    "signal_generator_v3.py",
    "backtest_v1.py",
]

def load_data(path):
    df = pd.read_csv(path)
    needed = {"time", "open", "high", "low", "close"}
    if not needed.issubset(df.columns):
        raise ValueError(f"{path} missing columns: {sorted(needed-set(df.columns))}")
    df["time"] = pd.to_datetime(df["time"], errors="raise")
    return df.sort_values("time").drop_duplicates("time").reset_index(drop=True)

def execute_run(pair, period, candles):
    runroot = DEST / pair / period
    adir, odir, ddir = runroot / "analysis", runroot / "outputs", runroot / "data"
    for folder in (adir, odir, ddir):
        folder.mkdir(parents=True, exist_ok=True)
    candle_path = ddir / f"{pair}_M15.csv"
    candles.to_csv(candle_path, index=False)

    for name in PIPELINE:
        src = ANALYSIS / name
        if not src.exists():
            raise FileNotFoundError(f"Required script missing: {src}")
        shutil.copy2(src, adir / name)

    (runroot / "config.py").write_text(
        "from pathlib import Path\n"
        f"PAIR = {pair!r}\n"
        "TIMEFRAME_NAME = 'M15'\n"
        f"HISTORICAL_FILE = Path({str(candle_path.resolve())!r})\n"
        "RISK_PERCENT = 1.0\nRISK_REWARD = 4.0\nBARS = 500\nINCLUDE_CURRENT = False\n",
        encoding="utf-8",
    )
    logs = runroot / "logs"
    logs.mkdir(exist_ok=True)
    for name in PIPELINE:
        print(f"[{pair}/{period}] {name}")
        proc = subprocess.run(
            [sys.executable, name], cwd=adir, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, errors="replace"
        )
        (logs / f"{Path(name).stem}.log").write_text(proc.stdout, encoding="utf-8")
        if proc.returncode:
            raise RuntimeError(
                f"{pair}/{period}: {name} failed. See {logs / (Path(name).stem + '.log')}.\n"
                + "\n".join(proc.stdout.splitlines()[-30:])
            )

    sp = odir / "signals_v3.csv"
    rp = odir / "backtest_results_v1.csv"
    signals = pd.read_csv(sp) if sp.exists() and sp.stat().st_size else pd.DataFrame()
    results = pd.read_csv(rp) if rp.exists() and rp.stat().st_size else pd.DataFrame()
    wins = losses = opened = 0
    net_r = pf = mdd = wr = 0.0
    if not results.empty and "result" in results:
        labels = results["result"].astype(str).str.upper()
        wins = int((labels == "WIN").sum())
        losses = int((labels == "LOSS").sum())
        opened = int((labels == "OPEN").sum())
        resolved = wins + losses
        wr = wins / resolved * 100 if resolved else 0.0
        rr = pd.to_numeric(results["rr"], errors="coerce") if "rr" in results else pd.Series(dtype=float)
        trade_rs = []
        for i, label in enumerate(labels):
            if label == "WIN":
                trade_rs.append(float(rr.iloc[i]) if i < len(rr) and pd.notna(rr.iloc[i]) else 4.0)
            elif label == "LOSS":
                trade_rs.append(-1.0)
            else:
                trade_rs.append(0.0)
        net_r = sum(trade_rs)
        gp = sum(x for x in trade_rs if x > 0)
        gl = -sum(x for x in trade_rs if x < 0)
        pf = gp / gl if gl else (float("inf") if gp else 0.0)
        equity = pd.Series(trade_rs).cumsum()
        mdd = float((equity.cummax() - equity).max()) if len(equity) else 0.0
    return {
        "pair": pair, "period": period, "candles": len(candles),
        "start": str(candles["time"].min()), "end": str(candles["time"].max()),
        "signals": len(signals), "backtest_rows": len(results),
        "wins": wins, "losses": losses, "open": opened,
        "win_rate_pct": round(wr, 2), "net_R": round(net_r, 2),
        "profit_factor": round(pf, 4) if pf != float("inf") else "Infinity",
        "max_drawdown_R": round(mdd, 2), "run_directory": str(runroot),
    }

def main():
    for p in PAIRS.values():
        if not p.exists():
            raise FileNotFoundError(f"Dataset not found: {p}")
    datasets = {pair: load_data(path) for pair, path in PAIRS.items()}
    start = max(df["time"].min() for df in datasets.values())
    end = min(df["time"].max() for df in datasets.values())
    print("Dataset coverage:")
    for pair, df in datasets.items():
        print(f"  {pair}: {len(df):,} candles | {df['time'].min()} -> {df['time'].max()}")
    print(f"Common overlap: {start} -> {end}")
    print("Strategy files are copied to isolated folders; originals are not edited.")
    print("Original 1:4 signal RR and strategy thresholds are preserved.")
    print("Important: any existing signal-timing/look-ahead issue in the original logic remains.")
    summaries = []
    for pair, df in datasets.items():
        summaries.append(execute_run(pair, "full_available", df.copy()))
        common = df[(df["time"] >= start) & (df["time"] <= end)].copy()
        summaries.append(execute_run(pair, "common_overlap", common))
    report = pd.DataFrame(summaries)
    DEST.mkdir(parents=True, exist_ok=True)
    report.to_csv(DEST / "comparison_report.csv", index=False)
    report.to_json(DEST / "comparison_report.json", orient="records", indent=2)
    cols = ["pair", "period", "candles", "start", "end", "signals",
            "backtest_rows", "wins", "losses", "open", "win_rate_pct",
            "net_R", "profit_factor", "max_drawdown_R"]
    print("\nCOMPARISON REPORT")
    print(report[cols].to_string(index=False))
    print(f"\nReports and all isolated run files saved under: {DEST}")

if __name__ == "__main__":
    main()
