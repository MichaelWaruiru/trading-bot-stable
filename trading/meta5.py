# from datetime import datetime, timedelta
# import matplotlib.pyplot as plt
# import pandas as pd
# from pandas.plotting import register_matplotlib_converters
# import pandas_ta as ta
# import MetaTrader5 as mt5

# register_matplotlib_converters()

# # Connect to MetaTrader 5
# if not mt5.initialize():
#     print("MetaTrader5 initialization failed!")
#     print("MT5 error:", mt5.last_error())
#     mt5.shutdown()
#     quit()

# print("MetaTrader5 initialized successfully")

# # Check terminal information
# terminal_info = mt5.terminal_info()

# if terminal_info is None:
#     print("Could not retrieve MT5 terminal information!")
#     print("MT5 error:", mt5.last_error())
#     mt5.shutdown()
#     quit()

# print("\n MT5 TERMINAL INFO ")
# print(terminal_info)

# # Check account information
# account_info = mt5.account_info()

# if account_info is None:
#     print("Could not retrieve MT5 account information!")
#     print("MT5 error:", mt5.last_error())
#     mt5.shutdown()
#     quit()

# print("\n MT5 ACCOUNT INFO ")
# print(f"Account Login: {account_info.login}")
# print(f"Balance:       {account_info.balance}")
# print(f"Equity:        {account_info.equity}")
# print(f"Currency:      {account_info.currency}")
# print(f"Server:        {account_info.server}")

# # Enable all symbols in the Market Watch
# symbols = [
#     "EURAUD",
#     "AUDUSD",
#     "EURUSD",
#     "EURGBP",
#     "EURCAD"
# ]

# print("\nSYMBOL SELECTION")

# for symbol in symbols:

#     if not mt5.symbol_select(symbol, True):
#         print(
#             f"FAILED to select {symbol} | "
#             f"MT5 error: {mt5.last_error()}"
#         )
#     else:
#         print(f"Symbol selected successfully: {symbol}")

# # Check EURUSD symbol info
# symbol = "EURUSD"

# print("\nEURUSD SYMBOL CHECK")

# symbol_info = mt5.symbol_info(symbol)

# if symbol_info is None:
#     print(f"Could not retrieve symbol information for {symbol}!")
#     print("MT5 error:", mt5.last_error())
#     mt5.shutdown()
#     quit()

# print(f"Symbol found: {symbol}")
# print(f"Symbol name: {symbol_info.name}")
# print(f"Bid:         {symbol_info.bid}")
# print(f"Ask:         {symbol_info.ask}")
# print(f"Point:       {symbol_info.point}")
# print(f"Digits:      {symbol_info.digits}")
# print(f"Trade mode:  {symbol_info.trade_mode}")

# # 6. Check current EURUSD tick
# print("\nEURUSD CURRENT TICK")

# tick = mt5.symbol_info_tick(symbol)

# if tick is None:
#     print(f"No current tick available for {symbol}!")
#     print("MT5 error:", mt5.last_error())
# else:
#     print(f"EURUSD Bid:  {tick.bid}")
#     print(f"EURUSD Ask:  {tick.ask}")
#     print(f"Tick Time:   {tick.time}")

# # Define date range
# start = datetime.now() - timedelta(days=1)
# end = datetime.now()

# # Request historical data for EURUSD
# print("\n HISTORICAL DATA ")

# eurusd_rates = mt5.copy_rates_range(
#     "EURUSD",
#     mt5.TIMEFRAME_M1,
#     start,
#     end
# )

# # Check if historical data is returned successfully
# if eurusd_rates is None:
#     print("EURUSD rates error:", mt5.last_error())
#     mt5.shutdown()
#     quit()

# if len(eurusd_rates) == 0:
#     print("No historical EURUSD data was returned.")
#     mt5.shutdown()
#     quit()

# print(
#     f"Successfully retrieved "
#     f"{len(eurusd_rates)} EURUSD M1 candles."
# )

# # Convert data to dataframe
# eurusd_df = pd.DataFrame(eurusd_rates)

# eurusd_df["time"] = pd.to_datetime(
#     eurusd_df["time"],
#     unit="s"
# )


# # Indicators using pandas-ta
# eurusd_df["rsi"] = eurusd_df.ta.rsi(
#     length=14
# )

# eurusd_df["ema_50"] = eurusd_df.ta.ema(
#     length=50
# )

# eurusd_df["sma_200"] = eurusd_df.ta.sma(
#     length=200
# )


# # 1Display first few rows
# print("\n EURUSD DATA ")

# print(eurusd_df.head())


# # Plot data with indicators
# plt.figure(figsize=(12, 6))

# plt.plot(
#     eurusd_df["time"],
#     eurusd_df["close"],
#     label="Close Price",
#     color="blue"
# )

# plt.plot(
#     eurusd_df["time"],
#     eurusd_df["ema_50"],
#     label="EMA 50",
#     color="orange"
# )

# plt.plot(
#     eurusd_df["time"],
#     eurusd_df["sma_200"],
#     label="SMA 200",
#     color="green"
# )

# plt.title("EURUSD with EMA and SMA")

# plt.legend()

# plt.show()

# # Shutdown MetaTrader5 connection
# mt5.shutdown()

# print("\nMetaTrader5 connection closed.")

import logging

import MetaTrader5 as mt5


def initialize_mt5():
    """Initialize the MetaTrader 5 connection."""

    if not mt5.initialize():
        logging.error(
            "MetaTrader5 initialization failed: %s",
            mt5.last_error()
        )
        return False

    logging.info(
        "MetaTrader5 initialized successfully"
    )

    return True


def select_symbol(symbol):
    """Make sure a symbol is available in Market Watch."""

    if not mt5.symbol_select(symbol, True):
        logging.error(
            "Failed to select symbol %s: %s",
            symbol,
            mt5.last_error()
        )
        return False

    logging.info(
        "Symbol %s selected successfully",
        symbol
    )

    return True


def get_symbol_info(symbol):
    """Return MT5 symbol information."""

    symbol_info = mt5.symbol_info(symbol)

    if symbol_info is None:
        logging.error(
            "Failed to get symbol info for %s: %s",
            symbol,
            mt5.last_error()
        )
        return None

    return symbol_info


def get_current_tick(symbol):
    """Return the latest market tick."""

    tick = mt5.symbol_info_tick(symbol)

    if tick is None:
        logging.error(
            "Failed to fetch tick for %s: %s",
            symbol,
            mt5.last_error()
        )
        return None

    return tick


def shutdown_mt5():
    """Close the MetaTrader 5 connection."""

    mt5.shutdown()

    logging.info(
        "MetaTrader5 connection closed"
    )