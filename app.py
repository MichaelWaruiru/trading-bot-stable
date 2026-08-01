import logging
import MetaTrader5 as mt5
from threading import Thread
from flask import Flask, render_template
from flask_socketio import SocketIO
from config.settings import DEFAULT_SYMBOL, DEFAULT_RISK_PERCENTAGE
from trading.engine import TradingEngine
from trading.meta5 import initialize_mt5, select_symbol, get_symbol_info
from trading.risk import validate_trading_config

app = Flask(__name__)

socketio = SocketIO(
    app,
    cors_allowed_origins="*"
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s"
)

# MetaTrader 5 initialization
if not initialize_mt5():
    raise RuntimeError(
        "Could not initialize MetaTrader 5."
    )

if not select_symbol(DEFAULT_SYMBOL):
    raise RuntimeError(f"Could not select {DEFAULT_SYMBOL}.")

symbol_info = get_symbol_info(DEFAULT_SYMBOL)

if symbol_info is None:
    raise RuntimeError(
        f"Could not get information for "
        f"{DEFAULT_SYMBOL}."
    )

logging.info("%s found - Bid: %s, Ask: %s", DEFAULT_SYMBOL, symbol_info.bid, symbol_info.ask)

# Trading engine
engine = TradingEngine(socketio)

# Web routes
@app.route("/")
def index():
    return render_template("index.html")

# Start bot
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
                "message": "Invalid trading parameters."
            }
        )

        return

    # Validate configuration
    errors = validate_trading_config(config)

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
    if not select_symbol(config["symbol"]):
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
    engine.start(config)

    socketio.emit(
        "bot_status",
        {
            "running": True
        }
    )

# Stop bot
@socketio.on("stop_bot")
def stop_bot():
    engine.stop()

    socketio.emit(
        "bot_status",
        {
            "running": False
        }
    )

# Application startup
engine = TradingEngine(socketio)

# Start trading engine worker
engine_thread = Thread(
    target=engine.run,
    daemon=True
)

engine_thread.start()