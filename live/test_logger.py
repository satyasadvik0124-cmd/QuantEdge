from logger import Logger

Logger.new_cycle("BTCUSD", "M15")

Logger.info("Fetching market data...")

Logger.success("Market data downloaded.")

Logger.warning("Spread is slightly high.")

Logger.error("No valid trade signal.")

Logger.signal(
    "BUY",
    118500,
    118250,
    119000
)

Logger.shutdown()