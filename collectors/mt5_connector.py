"""
=========================================================
QuantEdge V2
MT5 Connector
=========================================================

Responsible for:
- Initializing MT5
- Verifying account login
- Returning account information
- Selecting symbols
- Closing MT5 connection

Author : QuantEdge
"""

import MetaTrader5 as mt5


class MT5Connector:

    def __init__(self):
        self.connected = False

    # =====================================================
    # Connect
    # =====================================================

    def connect(self):

        if self.connected:
            return True

        if not mt5.initialize():
            print("❌ MT5 initialization failed")
            print("Error:", mt5.last_error())
            return False

        account = mt5.account_info()

        if account is None:
            print("❌ No MT5 account logged in.")
            mt5.shutdown()
            return False

        self.connected = True

        print("=" * 60)
        print("QUANTEDGE LIVE")
        print("=" * 60)
        print("✅ MT5 Connected")
        print(f"Login      : {account.login}")
        print(f"Server     : {account.server}")
        print(f"Balance    : {account.balance}")
        print(f"Equity     : {account.equity}")
        print(f"Leverage   : {account.leverage}")
        print("=" * 60)

        return True

    # =====================================================
    # Disconnect
    # =====================================================

    def disconnect(self):

        if self.connected:
            mt5.shutdown()
            self.connected = False
            print("✅ MT5 Connection Closed")

    # =====================================================
    # Connection Status
    # =====================================================

    def is_connected(self):
        return self.connected

    # =====================================================
    # Account Information
    # =====================================================

    def get_account_info(self):
        return mt5.account_info()

    # =====================================================
    # Terminal Information
    # =====================================================

    def get_terminal_info(self):
        return mt5.terminal_info()

    # =====================================================
    # Ensure Symbol Exists
    # =====================================================

    def select_symbol(self, symbol):

        if not mt5.symbol_select(symbol, True):
            raise ValueError(
                f"Unable to select symbol: {symbol}"
            )

        return True


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    connector = MT5Connector()

    if connector.connect():

        print()

        terminal = connector.get_terminal_info()

        print("Terminal:", terminal.name)

        connector.disconnect()