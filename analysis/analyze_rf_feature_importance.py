"""
Permutation feature importance for the exploratory Random Forest baseline.

Uses the same legacy dataset and chronological 70/30 split as
train_rf_legacy_experiment.py. Does not modify the strategy or backtest outputs.

WARNING: This is exploratory only. Legacy signal timestamps/labels were flagged
by the timing audit, so importance rankings are not validated trading insights.
"""
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import Pipeline

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "outputs" / "ml" / "gbpusd_m15_technical_features_legacy.csv"
OUTDIR = ROOT / "outputs" / "ml"
OUTDIR.mkdir(parents=True, exist_ok=True)
CSV_OUT = OUTDIR / "rf_legacy_permutation_importance.csv"
TXT_OUT = OUTDIR / "rf_legacy_feature_importance_report.txt"

TARGET = "target_tp_first"
TIME_COL = "signal_time"
EXCLUDE_EXACT = {
    TARGET, "result", "rr", "signal_time", "feature_candle_time",
    "feature_status", "source_file", "entry", "sl", "tp",
    "legacy_result", "aligned_result", "target", "outcome",
}
EXCLUDE_PREFIXES = ("target_", "result_", "outcome_", "label_")

def main():
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATA_PATH}\nRun analysis/prepare_technical_dataset.py first."
        )
    df = pd.read_csv(DATA_PATH)
    if TARGET not in df or TIME_COL not in df:
        raise ValueError(f"Dataset must contain {TARGET!r} and {TIME_COL!r}.")
    df[TIME_COL] = pd.to_datetime(df[TIME_COL], errors="coerce")
    df[TARGET] = pd.to_numeric(df[TARGET], errors="coerce")
    df = df.dropna(subset=[TIME_COL, TARGET])
    df = df[df[TARGET].isin([0, 1])].sort_values(TIME_COL).reset_index(drop=True)

    excluded = set(EXCLUDE_EXACT)
    excluded.update(c for c in df.columns if c.startswith(EXCLUDE_PREFIXES))
    features = [
        c for c in df.columns
        if c not in excluded and pd.api.types.is_numeric_dtype(df[c])
    ]
    if not features:
        raise ValueError("No numeric feature columns remain after exclusions.")

    X = df[features].replace([np.inf, -np.inf], np.nan)
    y = df[TARGET].astype(int)
    split_idx = int(len(df) * 0.70)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
    if y_train.nunique() < 2 or y_test.nunique() < 2:
        raise ValueError("Both chronological train and test partitions need both classes.")

    model = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("model", RandomForestClassifier(
            n_estimators=400, max_depth=4, min_samples_leaf=8,
            class_weight="balanced", random_state=42, n_jobs=-1
        )),
    ])
    model.fit(X_train, y_train)
    classes = list(model.named_steps["model"].classes_)
    p_win = model.predict_proba(X_test)[:, classes.index(1)]
    baseline_auc = roc_auc_score(y_test, p_win)

    result = permutation_importance(
        model, X_test, y_test, scoring="roc_auc",
        n_repeats=30, random_state=42, n_jobs=-1
    )
    importance = pd.DataFrame({
        "feature": features,
        "importance_mean_auc_drop": result.importances_mean,
        "importance_std": result.importances_std,
    }).sort_values("importance_mean_auc_drop", ascending=False)
    importance.to_csv(CSV_OUT, index=False)

    lines = [
        "EXPLORATORY RANDOM FOREST — PERMUTATION FEATURE IMPORTANCE",
        "=" * 64,
        "WARNING: Legacy labels/timestamps have known alignment limitations.",
        "Treat this as an exploratory diagnostic, not validated trading insight.",
        "",
        f"Rows: {len(df)}",
        f"Features tested: {len(features)}",
        f"Chronological split: first {split_idx} rows train, remaining {len(df)-split_idx} rows test",
        f"Test period: {df.iloc[split_idx][TIME_COL]} to {df.iloc[-1][TIME_COL]}",
        f"Test ROC-AUC before permutation: {baseline_auc:.4f}",
        "",
        "Top 10 features by mean ROC-AUC decrease after shuffling:",
    ]
    for rank, (_, row) in enumerate(importance.head(10).iterrows(), start=1):
        lines.append(
            f"{rank:>2}. {row['feature']}: mean AUC drop "
            f"{row['importance_mean_auc_drop']:.5f} +/- {row['importance_std']:.5f}"
        )
    lines += [
        "",
        "How to read this:",
        "- Larger positive values mean shuffling the feature reduced test ROC-AUC more.",
        "- Values near zero suggest little measurable contribution in this test set.",
        "- Negative values can occur due to noise or overfitting.",
        "- Correlated indicators can share or dilute importance.",
        "- Importance does not prove a feature causes better trading outcomes.",
        "",
        f"Full ranked table: {CSV_OUT}",
    ]
    TXT_OUT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))

if __name__ == "__main__":
    main()
