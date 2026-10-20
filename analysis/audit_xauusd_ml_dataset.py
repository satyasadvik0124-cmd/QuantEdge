"""Read-only XAUUSD ML dataset audit. Run from QuantEdge-main:
python .\analysis\audit_xauusd_ml_dataset.py
Creates two NEW files in outputs\ml and never changes source data/models.
Use --overwrite only to replace the two audit reports.
"""
from pathlib import Path
import argparse, json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "outputs"
ML = OUT / "ml"
CANDLES = DATA / "XAUUSD_M15_5Y.csv"
SIGNALS = OUT / "signals_v3.csv"
RESULTS = OUT / "backtest_results_v1.csv"
FEATURES = ML / "xauusd_m15_technical_features.csv"
SCHEMA = ML / "xauusd_rf_model_features.json"
REPORT = ML / "xauusd_dataset_audit_report.txt"
DETAIL = ML / "xauusd_dataset_audit_rows.csv"

def nk(s): return "".join(c.lower() for c in str(s) if c.isalnum())
def col(df, *names):
    m = {nk(c): c for c in df.columns}
    for name in names:
        if nk(name) in m: return m[nk(name)]
    for name in names:
        for k, v in m.items():
            if nk(name) and (nk(name) in k or k in nk(name)): return v
    return None
def load(p):
    if not p.exists(): raise FileNotFoundError(f"Required file missing: {p}")
    return pd.read_csv(p)
def dt(df, c): return pd.to_datetime(df[c], errors="coerce") if c else pd.Series(pd.NaT, index=df.index)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args()
    for p in (REPORT, DETAIL):
        if p.exists() and not args.overwrite:
            raise FileExistsError(f"{p} already exists. Use --overwrite only if you intend to replace audit reports.")
    candles, signals, results, feats = map(load, (CANDLES, SIGNALS, RESULTS, FEATURES))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8")) if SCHEMA.exists() else {}
    cc = {"time":col(candles,"time","datetime","timestamp","date")}
    sc = {"time":col(signals,"signal_time","time","datetime","timestamp"),
          "direction":col(signals,"direction","signal","type"), "entry":col(signals,"entry","entry_price"),
          "sl":col(signals,"sl","stop_loss","stoploss"), "tp":col(signals,"tp","take_profit","takeprofit")}
    rc = {"time":col(results,"signal_time","time","datetime","timestamp"),
          "direction":col(results,"direction","signal","type"), "entry":col(results,"entry","entry_price"),
          "sl":col(results,"sl","stop_loss","stoploss"), "tp":col(results,"tp","take_profit","takeprofit"),
          "result":col(results,"result","outcome","status"), "rr":col(results,"rr","r_multiple")}
    fc = {"time":col(feats,"signal_time","time","datetime","timestamp"),
          "candle_time":col(feats,"feature_candle_time","ml_feature_candle_time","candle_time"),
          "target":col(feats,"target_tp_first","actual_label","target","label"),
          "status":col(feats,"feature_status","ml_feature_status","status")}
    for df, c in ((candles,cc["time"]),(signals,sc["time"]),(results,rc["time"]),(feats,fc["time"])):
        df["_audit_time"] = dt(df,c)
    candle_times = set(candles["_audit_time"].dropna())
    rmap, fmap = {}, {}
    for i, row in results.iterrows():
        if pd.notna(row["_audit_time"]): rmap.setdefault(row["_audit_time"],[]).append(row)
    for i, row in feats.iterrows():
        if pd.notna(row["_audit_time"]): fmap.setdefault(row["_audit_time"],[]).append(row)
    sig_counts = signals["_audit_time"].value_counts()
    rows = []
    for i, s in signals.iterrows():
        t=s["_audit_time"]; rs=rmap.get(t,[]) if pd.notna(t) else []; fs=fmap.get(t,[]) if pd.notna(t) else []
        issues=[]
        if pd.isna(t): issues.append("signal_time_unparseable")
        elif t not in candle_times: issues.append("signal_time_not_exact_candle_timestamp")
        if pd.notna(t) and sig_counts.get(t,0)>1: issues.append("duplicate_signal_timestamp")
        if not rs: issues.append("no_backtest_result_at_signal_time")
        if len(rs)>1: issues.append("multiple_backtest_results_at_signal_time")
        if not fs: issues.append("no_feature_row_at_signal_time")
        if len(fs)>1: issues.append("multiple_feature_rows_at_signal_time")
        r=rs[0] if len(rs)==1 else None
        f=fs[0] if len(fs)==1 else None
        if r is not None:
            for k in ("entry","sl","tp"):
                if sc[k] and rc[k]:
                    a=pd.to_numeric(pd.Series([s[sc[k]]]),errors="coerce").iloc[0]
                    b=pd.to_numeric(pd.Series([r[rc[k]]]),errors="coerce").iloc[0]
                    if pd.notna(a) and pd.notna(b) and abs(float(a)-float(b))>1e-5: issues.append(k+"_mismatch")
            if sc["direction"] and rc["direction"] and str(s[sc["direction"]]).strip().lower()!=str(r[rc["direction"]]).strip().lower():
                issues.append("direction_mismatch")
        ft=""; status=""; target=np.nan; outcome=r[rc["result"]] if r is not None and rc["result"] else ""
        if f is not None:
            if fc["candle_time"]:
                ft=f[fc["candle_time"]]; parsed=pd.to_datetime(ft,errors="coerce")
                if pd.isna(parsed): issues.append("feature_candle_time_unparseable")
                elif pd.notna(t) and parsed>t: issues.append("feature_candle_after_signal_time")
            if fc["status"]:
                status=str(f[fc["status"]])
                if status.strip().upper() not in ("OK","VALID","TRUE","1"): issues.append("feature_status_not_ok")
            if fc["target"]: target=pd.to_numeric(pd.Series([f[fc["target"]]]),errors="coerce").iloc[0]
        if r is not None and rc["result"] and pd.notna(target):
            res=str(r[rc["result"]]).strip().upper()
            expected=1 if res=="WIN" else 0 if res=="LOSS" else None
            if expected is not None and int(target)!=expected: issues.append("feature_target_vs_backtest_result_mismatch")
        rows.append({"signal_row":i,"signal_time":t,"direction":s[sc["direction"]] if sc["direction"] else "",
                     "entry":s[sc["entry"]] if sc["entry"] else np.nan,"sl":s[sc["sl"]] if sc["sl"] else np.nan,
                     "tp":s[sc["tp"]] if sc["tp"] else np.nan,"matched_result_rows":len(rs),
                     "backtest_result":outcome,"feature_rows_at_signal_time":len(fs),"feature_candle_time":ft,
                     "feature_status":status,"feature_target":target,"issues":";".join(issues) if issues else "OK",
                     "issue_count":len(issues)})
    audit=pd.DataFrame(rows)
    audit.to_csv(DETAIL,index=False)
    lines=[]
    def add(x=""): lines.append(str(x))
    add("QUANTEDGE XAUUSD M15 DATASET AUDIT"); add("="*68)
    add(f"Project root: {ROOT}"); add("")
    add("ROW COUNTS")
    for name,df in (("Candles",candles),("Signals",signals),("Backtest results",results),("ML feature rows",feats)): add(f"{name}: {len(df):,}")
    add(f"Candle date range: {candles['_audit_time'].min()} to {candles['_audit_time'].max()}")
    add("")
    add("COLUMN DETECTION")
    for group, mapping in (("Candles",cc),("Signals",sc),("Results",rc),("Features",fc)):
        add(group+":")
        for k,v in mapping.items(): add(f"  {k}: {v or 'NOT FOUND'}")
    add("")
    add("DUPLICATES")
    for name,df in (("Signals",signals),("Results",results),("Features",feats)):
        counts=df["_audit_time"].value_counts()
        add(f"{name} duplicated timestamps: {int((counts>1).sum())}")
    add("")
    add("BACKTEST OUTCOME DISTRIBUTION")
    if rc["result"]:
        for k,v in results[rc["result"]].astype(str).str.upper().value_counts().items(): add(f"{k}: {v}")
    add("")
    add("SIGNAL-LEVEL CHECKS")
    add(f"Clean rows: {(audit['issues']=='OK').sum()} / {len(audit)}")
    add(f"Rows with issues: {(audit['issue_count']>0).sum()} / {len(audit)}")
    issue_counts={}
    for cell in audit["issues"]:
        if cell!="OK":
            for issue in cell.split(";"): issue_counts[issue]=issue_counts.get(issue,0)+1
    if issue_counts:
        for k,v in sorted(issue_counts.items(),key=lambda x:(-x[1],x[0])): add(f"{k}: {v}")
    else: add("No signal-level issues detected by these checks.")
    add("")
    add("FEATURE DATA QUALITY")
    if fc["status"]:
        for k,v in feats[fc["status"]].astype(str).value_counts().items(): add(f"Status {k}: {v}")
    feature_names=schema.get("features",[])
    if feature_names:
        missing=[x for x in feature_names if x not in feats.columns]
        add(f"Schema feature columns present: {len(feature_names)-len(missing)} / {len(feature_names)}")
        if missing: add("Missing schema features: "+", ".join(missing))
        numeric=feats[[x for x in feature_names if x in feats.columns]].apply(pd.to_numeric,errors="coerce")
        add(f"Rows with any missing schema feature: {int(numeric.isna().any(axis=1).sum())}")
        add(f"Missing numeric feature cells: {int(numeric.isna().sum().sum())}")
        add(f"Rows with infinite feature values: {int(np.isinf(numeric.to_numpy(dtype=float)).any(axis=1).sum())}")
    add("")
    add("LIMITATIONS")
    add("- This is a consistency audit, not proof that backtest execution is correct.")
    add("- Exact candle timestamp matches depend on the source timestamp convention.")
    add("- A feature candle before signal time is necessary but does not alone prove no leakage.")
    add("- Existing source files, signals, backtest results, and models were not modified.")
    add("")
    add("Audit detail CSV: "+str(DETAIL))
    add("Audit report: "+str(REPORT))
    REPORT.write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("\n".join(lines))
    print("\nAudit completed. Original project files were not changed.")

if __name__=="__main__": main()
