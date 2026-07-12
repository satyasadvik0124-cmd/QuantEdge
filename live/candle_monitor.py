"""
=========================================================
QuantEdge V2
Candle Monitor
=========================================================

Detects newly closed candles.

Author : QuantEdge
"""

import time


class CandleMonitor:

    def __init__(self):

        self.last_candle = None

    def is_new_candle(self, candle_time):
        """
        Returns True only when a new CLOSED candle appears.
        """

        if self.last_candle is None:

            self.last_candle = candle_time
            return False

        if candle_time > self.last_candle:

            self.last_candle = candle_time
            return True

        return False

    def wait(self, seconds=1):
        """
        Small delay to reduce CPU usage.
        """
        time.sleep(seconds)

    def reset(self):

        self.last_candle = None