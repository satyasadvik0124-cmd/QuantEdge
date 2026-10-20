import os
import sys

import numpy as np
import pandas as pd

sys.path.append(
    os.path.dirname(
        os.path.dirname(__file__)
    )
)

from config import HISTORICAL_FILE


SIGNALS_FILE = "../outputs/signals_v3.csv"
BACKTEST_FILE = "../outputs/backtest_results_v1.csv"
SCORES_FILE = "../outputs/ml_signal_scores_v1.csv"
REPORT_FILE = "../outputs/ml_model_report_v1.txt"

TRAIN_RATIO = 0.70
LEARNING_RATE = 0.05
EPOCHS = 4000
L2_PENALTY = 0.001
CONFIDENCE_THRESHOLD = 0.55


def sigmoid(values):
    values = np.clip(values, -35, 35)
    return 1 / (1 + np.exp(-values))


def standardize(train_x, test_x, full_x):
    means = train_x.mean(axis=0)
    stds = train_x.std(axis=0)
    stds[stds == 0] = 1

    return (
        (train_x - means) / stds,
        (test_x - means) / stds,
        (full_x - means) / stds,
        means,
        stds
    )


def train_logistic_regression(train_x, train_y):
    weights = np.zeros(train_x.shape[1])
    bias = 0.0

    for _ in range(EPOCHS):
        probabilities = sigmoid(
            np.dot(train_x, weights) + bias
        )

        error = probabilities - train_y

        weight_gradient = (
            np.dot(train_x.T, error)
            / len(train_y)
        ) + (L2_PENALTY * weights)

        bias_gradient = error.mean()

        weights -= LEARNING_RATE * weight_gradient
        bias -= LEARNING_RATE * bias_gradient

    return weights, bias


def classification_metrics(actual, probability):
    predicted = probability >= 0.50

    actual_bool = actual.astype(bool)

    accuracy = (predicted == actual_bool).mean()

    true_positive = (
        predicted & actual_bool
    ).sum()

    false_positive = (
        predicted & ~actual_bool
    ).sum()

    false_negative = (
        ~predicted & actual_bool
    ).sum()

    precision = (
        true_positive
        / (true_positive + false_positive)
        if true_positive + false_positive > 0
        else 0
    )

    recall = (
        true_positive
        / (true_positive + false_negative)
        if true_positive + false_negative > 0
        else 0
    )

    return accuracy, precision, recall


def profit_factor(rr_values):
    gross_profit = rr_values[rr_values > 0].sum()
    gross_loss = abs(
        rr_values[rr_values < 0].sum()
    )

    if gross_loss == 0:
        return float("inf")

    return gross_profit / gross_loss


print("\n===== ML SIGNAL MODEL V1 =====\n")

for file_path in [
    SIGNALS_FILE,
    BACKTEST_FILE,
    HISTORICAL_FILE
]:
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        exit()

signals_df = pd.read_csv(SIGNALS_FILE)
backtest_df = pd.read_csv(BACKTEST_FILE)
price_df = pd.read_csv(HISTORICAL_FILE)

if signals_df.empty or backtest_df.empty:
    print("Signals or backtest results are empty.")
    exit()

signals_df["signal_time"] = pd.to_datetime(
    signals_df["signal_time"]
)

backtest_df["signal_time"] = pd.to_datetime(
    backtest_df["signal_time"]
)

price_df["time"] = pd.to_datetime(
    price_df["time"]
)

price_df = price_df.sort_values("time").copy()

price_df["body_size"] = (
    price_df["close"] - price_df["open"]
).abs()

price_df["candle_range"] = (
    price_df["high"] - price_df["low"]
)

price_df["upper_wick"] = (
    price_df["high"]
    - price_df[["open", "close"]].max(axis=1)
)

price_df["lower_wick"] = (
    price_df[["open", "close"]].min(axis=1)
    - price_df["low"]
)

price_df["return_4"] = price_df["close"].pct_change(4)
price_df["return_16"] = price_df["close"].pct_change(16)

true_range = pd.concat(
    [
        price_df["high"] - price_df["low"],
        (
            price_df["high"]
            - price_df["close"].shift(1)
        ).abs(),
        (
            price_df["low"]
            - price_df["close"].shift(1)
        ).abs()
    ],
    axis=1
).max(axis=1)

price_df["atr_14"] = true_range.rolling(14).mean()

price_features = price_df[
    [
        "time",
        "body_size",
        "candle_range",
        "upper_wick",
        "lower_wick",
        "return_4",
        "return_16",
        "atr_14"
    ]
]

dataset = (
    backtest_df
    .merge(
        signals_df,
        on=[
            "signal_time",
            "direction",
            "entry",
            "sl",
            "tp"
        ],
        how="left",
        suffixes=("_result", "_signal")
    )
    .merge(
        price_features,
        left_on="signal_time",
        right_on="time",
        how="left"
    )
    .sort_values("signal_time")
    .reset_index(drop=True)
)

if "rr_result" in dataset.columns:
    dataset["rr"] = dataset["rr_result"]

dataset = dataset[
    dataset["result"].isin(["WIN", "LOSS"])
].copy()

dataset["target_win"] = (
    dataset["result"] == "WIN"
).astype(int)

dataset["direction_buy"] = (
    dataset["direction"] == "BUY"
).astype(int)

dataset["hour"] = dataset["signal_time"].dt.hour
dataset["day_of_week"] = dataset["signal_time"].dt.dayofweek

dataset["risk_to_atr"] = (
    dataset["risk"]
    / dataset["atr_14"].replace(0, np.nan)
)

feature_columns = [
    "direction_buy",
    "risk",
    "reward",
    "hour",
    "day_of_week",
    "body_size",
    "candle_range",
    "upper_wick",
    "lower_wick",
    "return_4",
    "return_16",
    "atr_14",
    "risk_to_atr"
]

dataset[feature_columns] = (
    dataset[feature_columns]
    .replace([np.inf, -np.inf], np.nan)
    .fillna(0)
)

if len(dataset) < 30:
    print("Not enough closed trades for ML training.")
    exit()

split_index = int(len(dataset) * TRAIN_RATIO)

train_df = dataset.iloc[:split_index].copy()
test_df = dataset.iloc[split_index:].copy()

train_x = train_df[feature_columns].to_numpy(dtype=float)
test_x = test_df[feature_columns].to_numpy(dtype=float)
full_x = dataset[feature_columns].to_numpy(dtype=float)

train_y = train_df["target_win"].to_numpy(dtype=float)
test_y = test_df["target_win"].to_numpy(dtype=float)

train_x, test_x, full_x, _, _ = standardize(
    train_x,
    test_x,
    full_x
)

weights, bias = train_logistic_regression(
    train_x,
    train_y
)

train_probability = sigmoid(
    np.dot(train_x, weights) + bias
)

test_probability = sigmoid(
    np.dot(test_x, weights) + bias
)

full_probability = sigmoid(
    np.dot(full_x, weights) + bias
)

train_accuracy, train_precision, train_recall = classification_metrics(
    train_y,
    train_probability
)

test_accuracy, test_precision, test_recall = classification_metrics(
    test_y,
    test_probability
)

dataset["ml_win_probability"] = np.round(
    full_probability,
    4
)

dataset["ml_take_trade"] = (
    dataset["ml_win_probability"]
    >= CONFIDENCE_THRESHOLD
)

filtered_df = dataset[dataset["ml_take_trade"]]

baseline_rr = dataset["rr"].sum()
filtered_rr = filtered_df["rr"].sum()

baseline_pf = profit_factor(dataset["rr"])
filtered_pf = profit_factor(filtered_df["rr"])

output_columns = [
    "signal_time",
    "direction",
    "entry",
    "sl",
    "tp",
    "result",
    "rr",
    "ml_win_probability",
    "ml_take_trade"
] + feature_columns

dataset[output_columns].to_csv(
    SCORES_FILE,
    index=False
)

report = f"""
=================================
QUANTEDGE ML SIGNAL MODEL V1
=================================

Model Type       : Logistic Regression
Training Method  : Chronological split
Train Ratio      : {TRAIN_RATIO:.0%}
Confidence Gate  : {CONFIDENCE_THRESHOLD:.2f}

---------------------------------

Closed Trades    : {len(dataset)}
Train Trades     : {len(train_df)}
Test Trades      : {len(test_df)}

Train Accuracy   : {train_accuracy:.2%}
Train Precision  : {train_precision:.2%}
Train Recall     : {train_recall:.2%}

Test Accuracy    : {test_accuracy:.2%}
Test Precision   : {test_precision:.2%}
Test Recall      : {test_recall:.2%}

---------------------------------

Baseline Trades  : {len(dataset)}
Baseline Net R   : {baseline_rr:.2f}R
Baseline PF      : {baseline_pf:.2f}

ML Filter Trades : {len(filtered_df)}
ML Filter Net R  : {filtered_rr:.2f}R
ML Filter PF     : {filtered_pf:.2f}

---------------------------------

Saved Scores:
{SCORES_FILE}

Important:
This is a research baseline. Use walk-forward validation
before trusting ML-filtered results.

=================================
"""

print(report)

with open(
    REPORT_FILE,
    "w",
    encoding="utf-8"
) as file:
    file.write(report)

print(f"Saved report: {REPORT_FILE}")
