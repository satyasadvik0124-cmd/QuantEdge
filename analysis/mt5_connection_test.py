
import getpass
import MetaTrader5 as mt5

# MT5 terminal configuration
TERMINAL_PATH = r"C:\Program Files\MetaTrader 5\terminal64.exe"

# Verify your numeric account login ID in MT5
LOGIN = int(input("Enter your MT5 numeric login ID: "))
SERVER = input("Enter your exact MT5 server name: ").strip()
PASSWORD = getpass.getpass("Enter your MT5 password: ")

# Initialize MT5
initialized = mt5.initialize(
    path=TERMINAL_PATH,
    login=LOGIN,
    password=PASSWORD,
    server=SERVER,
    timeout=60000
)

if not initialized:
    print("MT5 initialization failed:", mt5.last_error())
else:
    print("MT5 initialized successfully.")

    terminal = mt5.terminal_info()
    account = mt5.account_info()

    print("Terminal available:", terminal is not None)
    print("Account authenticated:", account is not None)

    if account:
        print("Login verified:", account.login == LOGIN)
        print("Connected server:", account.server)
        print("Account currency:", account.currency)

    mt5.shutdown()
