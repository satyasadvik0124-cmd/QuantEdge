import MetaTrader5 as mt5
import pandas as pd

print("Starting QuantEdge...")

if not mt5.initialize():
    print("Failed to connect to MT5")
    quit()

symbols = ["EURUSD", "GBPUSD", "XAUUSD"]

timeframes = {
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "H1": mt5.TIMEFRAME_H1
}

for symbol in symbols:

    for tf_name, tf_value in timeframes.items():

        print(f"Fetching {symbol} {tf_name}...")

        rates = mt5.copy_rates_from_pos(
            symbol,
            tf_value,
            0,
            1000
        )

        if rates is None:
            print(f"Failed: {symbol} {tf_name}")
            continue

        df = pd.DataFrame(rates)

        df["time"] = pd.to_datetime(
            df["time"],
            unit="s"
        )

        filename = f"data/{symbol}_{tf_name}.csv"

        df.to_csv(
            filename,
            index=False
        )

        print(f"Saved {filename}")

mt5.shutdown()

print("QuantEdge Data Collection Complete")