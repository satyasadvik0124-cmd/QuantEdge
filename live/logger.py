"""
=========================================================
QuantEdge V2
Logger
=========================================================

Central logging utility for the live engine.

Author : QuantEdge
"""

from datetime import datetime


class Logger:

    @staticmethod
    def separator():
        print("=" * 70)

    @staticmethod
    def info(message):
        print(f"[INFO] {message}")

    @staticmethod
    def success(message):
        print(f"[SUCCESS] {message}")

    @staticmethod
    def warning(message):
        print(f"[WARNING] {message}")

    @staticmethod
    def error(message):
        print(f"[ERROR] {message}")

    @staticmethod
    def timestamp():
        print(f"Time : {datetime.now()}")

    @staticmethod
    def new_cycle(symbol, timeframe):

        Logger.separator()

        print("QUANTEDGE LIVE")

        Logger.separator()

        print(f"Symbol     : {symbol}")
        print(f"Timeframe  : {timeframe}")
        print(f"Time       : {datetime.now()}")

        Logger.separator()

    @staticmethod
    def signal(direction, entry, sl, tp):

        Logger.separator()

        print("SIGNAL GENERATED")

        Logger.separator()

        print(f"Direction  : {direction}")
        print(f"Entry      : {entry}")
        print(f"Stop Loss  : {sl}")
        print(f"Take Profit: {tp}")

        Logger.separator()

    @staticmethod
    def shutdown():

        Logger.separator()

        print("QuantEdge Live Engine Stopped")

        Logger.separator()