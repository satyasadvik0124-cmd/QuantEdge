import MetaTrader5 as mt5

MT5_PATH = r"C:\Program Files\MetaTrader 5\terminal64.exe"

print("=" * 60)
print("MT5 CONNECTION CHECK")
print("=" * 60)

if mt5.initialize(path=MT5_PATH):

    print("\n✅ MT5 INITIALIZED")

    terminal = mt5.terminal_info()

    if terminal:
        print("\nTerminal information:")
        print("Name       :", terminal.name)
        print("Connected  :", terminal.connected)
        print("Trade Mode :", terminal.trade_allowed)

    account = mt5.account_info()

    if account:
        print("\nAccount information:")
        print("Login      :", account.login)
        print("Server     :", account.server)
        print("Balance    :", account.balance)

    else:
        print("\n❌ Account information unavailable")
        print("Error:", mt5.last_error())

    symbol = mt5.symbol_info_tick("XAUUSD")

    if symbol:
        print("\nXAUUSD:")
        print("Bid        :", symbol.bid)
        print("Ask        :", symbol.ask)
        print("Time       :", symbol.time)

    else:
        print("\n❌ XAUUSD tick unavailable")
        print("Error:", mt5.last_error())

    mt5.shutdown()

else:

    print("\n❌ MT5 INITIALIZATION FAILED")
    print("Error:", mt5.last_error())