# import os
# import time
# import logging
# import pandas as pd
# import pandas_ta as ta
# import MetaTrader5 as mt5
# from threading import Thread
# from datetime import datetime, timedelta
# from flask import Flask, render_template
# from flask_socketio import SocketIO
# from dotenv import load_dotenv
# from config.settings import DEFAULT_SYMBOL, DEFAULT_RISK_PERCENTAGE

# # Load environment variables
# load_dotenv()

# # Parameters
# # SYMBOL = os.getenv("SYMBOL", "EURUSD")
# # RISK_PERCENTAGE = float(os.getenv("RISK_PERCENTAGE", 1.0))

# # Initialize Flask and SocketIO
# app = Flask(__name__)
# socketio = SocketIO(app, cors_allowed_origins="*")

# # Logging setup
# logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

# # MetaTrader5 initialization
# if not mt5.initialize():
#   logging.error(f"MetaTrader5 initialization failed: {mt5.last_error()}")
#   quit()
  
# logging.info("MetaTrader5 initialized successfully")

# # Select configured symbol
# if not mt5.symbol_select(DEFAULT_SYMBOL, True):
#   logging.error(f"Failed to select symbol {DEFAULT_SYMBOL}: {mt5.last_error()}")
#   mt5.shutdown()
#   quit()
  
# logging.info(f"Symbol {DEFAULT_SYMBOL} selected successfully")

# # Check symbol info
# symbol_info = mt5.symbol_info(DEFAULT_SYMBOL)
# if symbol_info is None:
#   logging.error(f"Failed to get symbol info for {DEFAULT_SYMBOL}: {mt5.last_error()}")
#   mt5.shutdown()
#   quit()
  
# logging.info(f"{DEFAULT_SYMBOL} found - "
#              f"Bid: {symbol_info.bid}, "
#              f"Ask: {symbol_info.ask}"
#             )

# # Check current tick
# tick = mt5.symbol_info_tick(DEFAULT_SYMBOL)

# if tick is None:
#   logging.error(f"No current tick available for {DEFAULT_SYMBOL}: {mt5.last_error()}")
# else:
#   logging.info(f"{DEFAULT_SYMBOL} current tick - "
#                f"Bid: {tick.bid}, "
#                f"Ask: {tick.ask}, "
#                f"Time: {datetime.fromtimestamp(tick.time)}"
#               )

# # Bot state
# bot_state = {
#   "is_running": False,
#   "current_price": 0.0,
#   "position": None,
#   "profit_loss": 0,
#   "alerts": []
# }

# def fetch_current_price(symbol):
#   """Fetch live tick from MetaTrader5."""
#   tick = mt5.symbol_info_tick(symbol)
#   if tick is None:
#       logging.error(
#         f"Failed to fetch tick for {symbol}: "
#         f"{mt5.last_error()}"
#       )
#       return None

#   logging.info(
#     f"{symbol} - Bid: {tick.bid}, Ask: {tick.ask}"
#   )

#   return tick.ask

# def fetch_historical_data(symbol, timeframe, count=100):
#   """Fetch historical candles using copy_rates_from_pos."""
#   rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
#   if rates is None or len(rates) == 0:
#       return None
#   df = pd.DataFrame(rates)
#   df['time'] = pd.to_datetime(df['time'], unit='s')
#   return df

# def calculate_lot_size(account_balance, risk_percentage, stop_loss_pips=20):
#   """
#   Proper Forex Lot Size Calculation:
#   Risk Amount ($) = Account Balance * (Risk % / 100)
#   For EURUSD: Standard Lot = $10 per pip.
#   """
#   risk_amount = account_balance * (risk_percentage / 100.0)
#   pip_value_per_standard_lot = 10.0  # EURUSD standard lot pip value in USD
  
#   lot_size = risk_amount / (stop_loss_pips * pip_value_per_standard_lot)
  
#   # Clamp lot size between 0.01 min lot and 1.00 max lot for safety
#   lot_size = max(0.01, round(lot_size, 2))
#   return lot_size

# def place_order(symbol, volume, order_type):
#   """Place market order in MetaTrader5."""
#   price = fetch_current_price(symbol)
#   if not price:
#     return False
      
#   request = {
#     "action": mt5.TRADE_ACTION_DEAL,
#     "symbol": symbol,
#     "volume": volume,
#     "type": order_type,
#     "price": price,
#     "deviation": 20,
#     "magic": 123456,
#     "comment": "Python Bot Order",
#     "type_time": mt5.ORDER_TIME_GTC,
#     "type_filling": mt5.ORDER_FILLING_IOC,
#   }
#   result = mt5.order_send(request)
#   if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
#     comment = result.comment if result else "Unknown error"
#     logging.error(f"Order execution failed: {comment}")
#     return False
#   return True

# def send_alert(message):
#   """Send alert string to frontend."""
#   bot_state["alerts"].append(message)
#   socketio.emit("alert", {"message": message})

# def trading_engine():
#   """Main trading loop."""
#   while True:
#     # Always fetch live price tick regardless of running state so UI updates
#     price = fetch_current_price(DEFAULT_SYMBOL)
#     if price:
#       bot_state["current_price"] = price

#     if bot_state["is_running"] and price:
#       # 1. Fetch last 100 candles on M1
#       data = fetch_historical_data(DEFAULT_SYMBOL, mt5.TIMEFRAME_M1, count=100)
#       if data is not None:
#         # 2. Calculate RSI
#         data['rsi'] = data.ta.rsi(length=14)
#         current_rsi = data['rsi'].iloc[-1]

#         # 3. Simple Strategy Logic
#         position = None
#         if current_rsi < 30 and bot_state["position"] != "long":
#           position = "long"
#         elif current_rsi > 70 and bot_state["position"] != "short":
#           position = "short"

#         # 4. Order Execution
#         if position:
#           account_info = mt5.account_info()
#           if account_info:
#             lot_size = calculate_lot_size(account_info.balance, DEFAULT_RISK_PERCENTAGE)
#             order_type = mt5.ORDER_TYPE_BUY if position == "long" else mt5.ORDER_TYPE_SELL

#             if place_order(DEFAULT_SYMBOL, lot_size, order_type):
#               bot_state["position"] = position
#               send_alert(f"Order Executed: {position.upper()} {lot_size} lots on {DEFAULT_SYMBOL} (RSI: {round(current_rsi, 2)})")

#     # 5. Broadcast live price update to JavaScript UI
#     socketio.emit("price_update", {
#         "price": round(bot_state["current_price"], 5),
#         "position": bot_state["position"]
#     })

#     time.sleep(1)  # Refresh tick frequency

# @app.route("/")
# def index():
#   return render_template("index.html")

# @socketio.on("toggle_bot")
# def toggle_bot(data):
#   bot_state["is_running"] = data["status"]
#   status_msg = "Bot started." if bot_state["is_running"] else "Bot stopped."
#   send_alert(status_msg)
#   logging.info(f"Bot running status: {bot_state['is_running']}")

# if __name__ == "__main__":
#   # Start background loop
#   daemon_thread = Thread(target=trading_engine, daemon=True)
#   daemon_thread.start()

#   # Run app
#   socketio.run(app, debug=True, port=5000)

import logging
import MetaTrader5 as mt5
from threading import Thread

from flask import Flask, render_template
from flask_socketio import SocketIO

from config.settings import (
    DEFAULT_SYMBOL,
    DEFAULT_RISK_PERCENTAGE
)

from trading.engine import TradingEngine

from trading.meta5 import (
    initialize_mt5,
    select_symbol,
    get_symbol_info
)

from trading.risk import (
    validate_trading_config
)


app = Flask(__name__)

socketio = SocketIO(
    app,
    cors_allowed_origins="*"
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s"
)


# --------------------------------------------------
# MetaTrader 5 initialization
# --------------------------------------------------

if not initialize_mt5():

    raise RuntimeError(
        "Could not initialize MetaTrader 5."
    )


if not select_symbol(
    DEFAULT_SYMBOL
):

    raise RuntimeError(
        f"Could not select {DEFAULT_SYMBOL}."
    )


symbol_info = get_symbol_info(
    DEFAULT_SYMBOL
)


if symbol_info is None:

    raise RuntimeError(
        f"Could not get information for "
        f"{DEFAULT_SYMBOL}."
    )


logging.info(
    "%s found - Bid: %s, Ask: %s",
    DEFAULT_SYMBOL,
    symbol_info.bid,
    symbol_info.ask
)


# --------------------------------------------------
# Trading engine
# --------------------------------------------------

engine = TradingEngine(
    socketio
)


# --------------------------------------------------
# Web routes
# --------------------------------------------------

@app.route("/")
def index():

    return render_template(
        "index.html"
    )


# --------------------------------------------------
# Start bot
# --------------------------------------------------

@socketio.on("start_bot")
def start_bot(data):

    try:

        config = {
            "symbol":
                data.get(
                    "symbol",
                    DEFAULT_SYMBOL
                ),
                
            "timeframe": mt5.TIMEFRAME_M1,

            "risk_percentage":
                float(
                    data.get(
                        "risk_percentage",
                        DEFAULT_RISK_PERCENTAGE
                    )
                ),

            "stop_loss_pips":
                int(
                    data.get(
                        "stop_loss_pips",
                        20
                    )
                ),

            "take_profit_pips":
                int(
                    data.get(
                        "take_profit_pips",
                        40
                    )
                ),

            "max_open_positions":
                int(
                    data.get(
                        "max_open_positions",
                        1
                    )
                ),

            "max_daily_loss_percentage":
                float(
                    data.get(
                        "max_daily_loss_percentage",
                        3
                    )
                ),

            "max_spread_pips":
                float(
                    data.get(
                        "max_spread_pips",
                        2
                    )
                )
        }


    except (TypeError, ValueError):

        socketio.emit(
            "alert",
            {
                "message":
                    "Invalid trading parameters."
            }
        )

        return


    # Validate configuration

    errors = validate_trading_config(
        config
    )


    if errors:

        socketio.emit(
            "alert",
            {
                "message":
                    " | ".join(errors)
            }
        )

        return


    # Make sure symbol exists

    if not select_symbol(
        config["symbol"]
    ):

        socketio.emit(
            "alert",
            {
                "message":
                    f"Symbol "
                    f"{config['symbol']} "
                    f"is not available."
            }
        )

        return


    # Start engine

    engine.start(
        config
    )


    socketio.emit(
        "bot_status",
        {
            "running": True
        }
    )


# --------------------------------------------------
# Stop bot
# --------------------------------------------------

@socketio.on("stop_bot")
def stop_bot():

    engine.stop()


    socketio.emit(
        "bot_status",
        {
            "running": False
        }
    )


# --------------------------------------------------
# Application startup
# --------------------------------------------------

if __name__ == "__main__":

    engine_thread = Thread(
        target=engine.run,
        daemon=True
    )

    engine_thread.start()


    socketio.run(
        app,
        debug=True,
        port=5000
    )