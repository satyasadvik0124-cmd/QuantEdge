"""
Read-only XAUUSD backtest execution audit.

Run from QuantEdge-main:
  python .\analysis\audit_xauusd_backtest_execution.py

Reads existing candles, signals and backtest results. Creates NEW files only:
  outputs/ml/xauusd_backtest_execution_audit.txt
  outputs/ml/xauusd_backtest_execution_audit.csv

Does not change signals, strategy code, results, datasets, or models.
Refuses to overwrite these audit outputs unless --overwrite is supplied.

This is a diagnostic audit, not an automatic replacement backtest. It highlights:
- entry level not touched after signal time before an exit level is touched
- SL and TP both touched within the same candle (intrabar order unknown from M15 OHLC)
- no SL/TP hit within available candles
- first exit level found by a simple OHLC scan differs from recorded result
- timestamp and trade-price integrity issues

The scan starts with candles strictly after the signal timestamp, consistent with the
known legacy backtest convention. It assumes the trade is active at the entry price
immediately after the signal, solely to reconstruct the legacy exit scan. Entry-touch
flags are reported separately and are not used to silently change the recorded result.
"""
from pathlib import Path
import argparse
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "outputs"
ML = OUT / "ml"
CANDLES_FILE = DATA / "XAUUSD_M15_5Y.csv"
SIGNALS_FILE = OUT / "signals_v3.csv"
RESULTS_FILE = OUT / "backtest_results_v1.csv"
REPORT_FILE = ML / "xauusd_backtest_execution_audit.txt"
DETAIL_FILE = ML / "xauusd_backtest_execution_audit.csv"

def norm(x):
    return "".join(c.lower() for c in str(x) if c.isalnum())

def find_col(df, *names):
    m = {norm(c): c for c in df.columns}
    for name in names:
        if norm(name) in m:
            return m[norm(name)]
    for name in names:
        for key, val in m.items():
            if norm(name) and (norm(name) in key or key in norm(name)):
                return val
    return None

def numeric(value):
    try:
        x = float(value)
        return x if np.isfinite(x) else np.nan
    except (TypeError, ValueError):
        return np.nan

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    for p in (REPORT_FILE, DETAIL_FILE):
        if p.exists() and not args.overwrite:
            raise FileExistsError(
                f"{p} already exists. Use --overwrite only if you intend to replace these audit outputs."
            )

    for p in (CANDLES_FILE, SIGNALS_FILE, RESULTS_FILE):
        if not p.exists():
            raise FileNotFoundError(f"Required file not found: {p}")

    candles = pd.read_csv(CANDLES_FILE)
    signals = pd.read_csv(SIGNALS_FILE)
    results = pd.read_csv(RESULTS_FILE)

    ct = find_col(candles, "time", "datetime", "timestamp", "date")
    co, ch, cl, cc = (find_col(candles, x) for x in ("open", "high", "low", "close"))
    st = find_col(signals, "signal_time", "time", "datetime", "timestamp")
    sd = find_col(signals, "direction", "signal", "type")
    se, ss, sp = (find_col(signals, x) for x in ("entry", "sl", "tp"))
    rt = find_col(results, "signal_time", "time", "datetime", "timestamp")
    rd = find_col(results, "direction", "signal", "type")
    re, rsl, rtp = (find_col(results, x) for x in ("entry", "sl", "tp"))
    rr = find_col(results, "result", "outcome", "status")
    rrm = find_col(results, "rr", "r_multiple", "r")

    required = [("candle time", ct), ("open", co), ("high", ch), ("low", cl),
                ("signal time", st), ("entry", se), ("SL", ss), ("TP", sp),
                ("result time", rt), ("recorded result", rr)]
    missing = [name for name, value in required if not value]
    if missing:
        raise ValueError("Could not identify required columns: " + ", ".join(missing))

    candles["_t"] = pd.to_datetime(candles[ct], errors="coerce")
    signals["_t"] = pd.to_datetime(signals[st], errors="coerce")
    results["_t"] = pd.to_datetime(results[rt], errors="coerce")
    for c in (co, ch, cl, cc):
        if c:
            candles[c] = pd.to_numeric(candles[c], errors="coerce")
    candles = candles.dropna(subset=["_t", ch, cl]).sort_values("_t").reset_index(drop=True)
    candle_times = candles["_t"].to_numpy(dtype="datetime64[ns]")
    candle_time_set = set(candles["_t"])

    result_by_time = {}
    for _, r in results.iterrows():
        t = r["_t"]
        if pd.notna(t):
            result_by_time.setdefault(t, []).append(r)

    out = []
    for idx, s in signals.iterrows():
        t = s["_t"]
        entry, sl, tp = numeric(s[se]), numeric(s[ss]), numeric(s[sp])
        matched = result_by_time.get(t, []) if pd.notna(t) else []
        rec = matched[0] if len(matched) == 1 else None
        recorded = str(rec[rr]).strip().upper() if rec is not None else "NO_MATCH"
        direction = str(s[sd]).strip().upper() if sd else ""
        issues = []

        if pd.isna(t):
            issues.append("signal_time_unparseable")
            future = candles.iloc[0:0]
        else:
            future = candles[candles["_t"] > t]
            if t not in candle_time_set:
                issues.append("signal_time_not_exact_candle")
        if len(matched) != 1:
            issues.append("result_match_count_not_one")
        if not np.isfinite([entry, sl, tp]).all():
            issues.append("invalid_entry_sl_tp")
        elif sl == entry or tp == entry or sl == tp:
            issues.append("degenerate_entry_sl_tp")

        # Scan future candles for the first SL/TP touch. On same-bar touches, mark ambiguity.
        first_exit = "NO_EXIT_IN_DATA"
        first_exit_time = pd.NaT
        both_hit_same_bar = False
        sl_first_count = 0
        tp_first_count = 0
        entry_touched_before_exit = False
        entry_touch_time = pd.NaT
        first_exit_idx = None

        valid_prices = np.isfinite([entry, sl, tp]).all()
        if valid_prices and len(future):
            for cidx, c in future.iterrows():
                hi, lo = numeric(c[ch]), numeric(c[cl])
                if not np.isfinite([hi, lo]).all():
                    continue
                if direction in ("BUY", "LONG"):
                    sl_hit = lo <= sl
                    tp_hit = hi >= tp
                    entry_hit = lo <= entry <= hi
                elif direction in ("SELL", "SHORT"):
                    sl_hit = hi >= sl
                    tp_hit = lo <= tp
                    entry_hit = lo <= entry <= hi
                else:
                    sl_hit = False
                    tp_hit = False
                    entry_hit = lo <= entry <= hi
                if sl_hit or tp_hit:
                    first_exit_time = c["_t"]
                    first_exit_idx = cidx
                    both_hit_same_bar = bool(sl_hit and tp_hit)
                    if both_hit_same_bar:
                        first_exit = "AMBIGUOUS_SL_AND_TP_SAME_BAR"
                    elif sl_hit:
                        first_exit = "LOSS"
                    else:
                        first_exit = "WIN"
                    break
                if entry_hit and not entry_touched_before_exit:
                    entry_touched_before_exit = True
                    entry_touch_time = c["_t"]

        if valid_prices and first_exit != "NO_EXIT_IN_DATA" and not entry_touched_before_exit:
            issues.append("entry_not_touched_before_first_exit_under_touch_check")
        if both_hit_same_bar:
            issues.append("sl_and_tp_both_touched_same_m15_bar")
        if first_exit == "NO_EXIT_IN_DATA":
            issues.append("no_sl_or_tp_hit_in_remaining_data")
        if first_exit in ("WIN", "LOSS") and recorded in ("WIN", "LOSS") and first_exit != recorded:
            issues.append("simple_ohlc_exit_scan_disagrees_with_recorded_result")
        if first_exit == "AMBIGUOUS_SL_AND_TP_SAME_BAR":
            issues.append("recorded_result_depends_on_intrabar_assumption")

        # Verify signal/result prices if columns exist.
        if rec is not None:
            for label, sig_col, res_col in (("entry", se, re), ("sl", ss, rsl), ("tp", sp, rtp)):
                if sig_col and res_col:
                    a, b = numeric(s[sig_col]), numeric(rec[res_col])
                    if np.isfinite([a, b]).all() and abs(a-b) > 1e-5:
                        issues.append(f"{label}_signal_result_mismatch")

        out.append({
            "signal_row": idx,
            "signal_time": t,
            "direction": direction,
            "entry": entry, "sl": sl, "tp": tp,
            "recorded_result": recorded,
            "recorded_rr": rec[rrm] if rec is not None and rrm else "",
            "future_candles_scanned": len(future),
            "entry_touched_before_first_exit": entry_touched_before_exit,
            "entry_touch_time": entry_touch_time,
            "ohlc_first_exit_diagnostic": first_exit,
            "diagnostic_first_exit_time": first_exit_time,
            "both_sl_tp_hit_same_bar": both_hit_same_bar,
            "issues": ";".join(issues) if issues else "OK",
            "issue_count": len(issues)
        })

    audit = pd.DataFrame(out)
    audit.to_csv(DETAIL_FILE, index=False)

    lines = []
    def add(x=""): lines.append(str(x))
    add("QUANTEDGE XAUUSD M15 BACKTEST EXECUTION AUDIT")
    add("=" * 72)
    add(f"Candles scanned: {len(candles):,}")
    add(f"Signals: {len(signals):,}")
    add(f"Backtest results: {len(results):,}")
    add(f"Candle range: {candles['_t'].min()} to {candles['_t'].max()}")
    add("")
    add("RECORDED RESULT DISTRIBUTION")
    for k, v in results[rr].astype(str).str.upper().value_counts().items():
        add(f"{k}: {v}")
    add("")
    add("DIAGNOSTIC COUNTS")
    add(f"Signals with no detected issue: {(audit['issues']=='OK').sum()} / {len(audit)}")
    add(f"Signals with one or more flags: {(audit['issue_count']>0).sum()} / {len(audit)}")
    add(f"Entry not touched before first detected exit: {int((~audit['entry_touched_before_first_exit'] & audit['ohlc_first_exit_diagnostic'].isin(['WIN','LOSS','AMBIGUOUS_SL_AND_TP_SAME_BAR'])).sum())}")
    add(f"SL and TP both touched in same M15 candle: {int(audit['both_sl_tp_hit_same_bar'].sum())}")
    add(f"No SL/TP hit in remaining candle history: {int((audit['ohlc_first_exit_diagnostic']=='NO_EXIT_IN_DATA').sum())}")
    add(f"Simple OHLC exit scan disagrees with recorded WIN/LOSS: {int(audit['issues'].str.contains('simple_ohlc_exit_scan_disagrees', regex=False).sum())}")
    add("")
    add("FLAG COUNTS")
    counts = {}
    for cell in audit["issues"]:
        if cell != "OK":
            for issue in cell.split(";"):
                counts[issue] = counts.get(issue, 0) + 1
    if counts:
        for k, v in sorted(counts.items(), key=lambda x: (-x[1], x[0])):
            add(f"{k}: {v}")
    else:
        add("No flags from these diagnostic checks.")
    add("")
    add("HOW TO INTERPRET")
    add("- This is a diagnostic OHLC scan, not an automatic replacement backtest.")
    add("- M15 OHLC cannot reveal the order of SL and TP touches within the same candle.")
    add("- Entry-touch flags are diagnostic; this script does not remove trades or change results.")
    add("- The scan begins strictly after the recorded signal timestamp.")
    add("- Inspect flagged rows before changing the strategy or training labels.")
    add("")
    add(f"Detail CSV: {DETAIL_FILE}")
    add(f"Report: {REPORT_FILE}")
    REPORT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print("\nOriginal project files were not modified.")

if __name__ == "__main__":
    main()
