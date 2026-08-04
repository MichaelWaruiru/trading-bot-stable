import logging
import time
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime
from trading.meta5 import get_current_tick, get_symbol_info
from trading.strategy import calculate_rsi, generate_rsi_signal
from trading.risk import can_open_position, check_spread, calculate_position_size, get_open_positions, get_daily_starting_equity, check_daily_drawdown
from trading.execution import execute_market_order

class TradingEngine:
    def __init__(self, socketio):
        self.socketio = socketio
        self.running = False
        self.config = None
        self.daily_starting_equity = None
        self.daily_loss_blocked = False
        self.last_drawdown_alert = None
        self.risk_date = None
        self.loop_interval = 1
        self.last_processed_candle = None
        self.state = {
            "current_price": 0.0,
            "position": None,
            "open_positions": 0,
            "last_signal": None,
            "last_trade": None,
            "daily_drawdown": 0.0,
            "daily_loss_blocked": False,
            "alerts": []
        }

    def start(self, config):
        self.config = config
        self.running = True
        self.daily_loss_blocked = False
        self.last_drawdown_alert = None
        self.risk_date = datetime.now().date()
        self.daily_starting_equity = (get_daily_starting_equity())
        self.last_processed_candle = None

        if self.daily_starting_equity is None:
            logging.error(
                (
                    "Could not determine "
                    "daily starting equity."
                )
            )

        logging.info(
            (
                "Trading engine started "
                "with configuration: %s"
            ),
            config
        )

        self._send_alert(
            (
                f"Trading engine started "
                f"for {config['symbol']}."
            )
        )

    def stop(self):
        self.running = False

        logging.info("Trading engine stopped.")

        self._send_alert("Trading engine stopped.")

    def run(self):
        """
        Run the trading engine worker loop
        """
        logging.info("Tading engine worker started")
        while True:
            try:
                # No configuration yet
                if self.config is None:
                    time.sleep(self.loop_interval)
                    continue
                  
                self._reset_daily_risk_if_needed()

                symbol = self.config["symbol"]

                # Get symbol information
                symbol_info = (get_symbol_info(symbol))

                if symbol_info is None:
                    logging.error( ( "Unable to retrieve " "symbol information " "for %s. MT5 error: %s" ), symbol, mt5.last_error() )
                    
                    time.sleep(self.loop_interval)
                    continue

                # Get latest tick
                tick = (get_current_tick(symbol))

                if tick is None:
                    logging.error( ( "Unable to retrieve " "current tick for %s. " "MT5 error: %s" ), symbol, mt5.last_error() )
                    
                    time.sleep(self.loop_interval)
                    continue

                self.state["current_price"] = tick.ask

                # Synchronize actual MT5 positions
                self._sync_positions(symbol)

                # Check daily drawdown
                self._check_daily_risk()
                
                # Calculate current spread
                spread = (tick.ask - tick.bid)
                
                spread_pips = (spread / (symbol_info.point * 10 if symbol_info.digits in (3, 5) else symbol_info.point))
                
                # Log current market state
                logging.info( ( "MARKET | %s | " "Bid: %.*f | " "Ask: %.*f | " "Spread: %.2f pips | " "Position: %s | " "Open: %s | " "Engine: %s" ), symbol, symbol_info.digits, tick.bid, symbol_info.digits, tick.ask, spread_pips, self.state["position"], self.state["open_positions"], ( "RUNNING" if self.running else "STOPPED" ) )

                # Broadcast current state
                self._broadcast_state(symbol_info, tick)

                # Engine stopped
                if not self.running:
                    time.sleep(self.loop_interval)
                    continue

                # Daily loss circuit breaker
                if self.daily_loss_blocked:
                    time.sleep(self.loop_interval)
                    continue

                # Maximum position check
                can_trade, reason = (can_open_position(self.config))

                if not can_trade:
                    time.sleep(self.loop_interval)
                    continue

                # Spread check
                (spread_ok, spread_message, spread) = check_spread(self.config, symbol_info, tick)

                if not spread_ok:
                    time.sleep(self.loop_interval)
                    continue

                # Fetch historical data
                data = (self._fetch_historical_data(symbol, self.config["timeframe"], count=100))

                if data is None:
                    time.sleep(self.loop_interval)
                    continue

                # Calculate RSI
                data = calculate_rsi(data)
                
                # Exclude the current forming candle
                closed_data = data.iloc[:-1]
                
                if len(closed_data) < 2:
                    time.sleep(self.loop_interval)
                    continue
                
                # Identify the latest completed candle to avoid processing the same candle multiple times
                latest_closed_candle = closed_data["time"].iloc[-1]
                
                if self.last_processed_candle == latest_closed_candle:
                    time.sleep(self.loop_interval)
                    continue
                
                self.last_processed_candle = latest_closed_candle

                # Generate transition signal
                signal = (generate_rsi_signal(data))

                self.state["last_signal"] = signal

                if signal is None:
                    time.sleep(1)
                    continue

                logging.info(
                    (
                        "New RSI signal: %s"
                    ),
                    signal
                )

                # Convert signal to order type
                if signal == "long":
                    order_type = (
                        mt5.ORDER_TYPE_BUY
                    )
                elif signal == "short":
                    order_type = (
                        mt5.ORDER_TYPE_SELL
                    )
                else:
                    time.sleep(self.loop_interval)
                    continue

                # Account information
                account_info = (mt5.account_info())

                if account_info is None:
                    self._send_alert(
                        (
                            "Could not retrieve "
                            "MT5 account information."
                        )
                    )
                    time.sleep(1)
                    continue

                # Calculate position size
                volume = (calculate_position_size(account_info.balance, self.config["risk_percentage"], self.config["stop_loss_pips"], symbol_info))

                if volume is None:
                    self._send_alert(
                        (
                            "Could not calculate "
                            "a valid position size."
                        )
                    )
                    time.sleep(self.loop_interval)
                    continue

                # Execute order
                (success, message, result) = execute_market_order(self.config, symbol_info, tick, order_type, volume)

                self._send_alert(message)

                if success:
                    self.state["last_trade"] = {
                        "signal": signal,
                        "volume": volume,
                        "price": (tick.ask if signal == "long" else tick.bid)
                    }
                time.sleep(self.loop_interval)

            except Exception:
                logging.exception("Trading engine error")
                time.sleep(self.loop_interval)

    def _sync_positions(self, symbol):
        """
        Synchronize local state with actual
        MetaTrader 5 positions.
        """
        positions = (get_open_positions(symbol))

        self.state["open_positions"] = len(positions)

        if not positions:
            self.state["position"] = None

            return
        # Determie position directi
        has_long = any(
            position.type
            == mt5.POSITION_TYPE_BUY

            for position
            in positions
        )

        has_short = any(
            position.type
            == mt5.POSITION_TYPE_SELL

            for position
            in positions
        )

        if has_long and has_short:
            self.state["position"] = "mixed"

        elif has_long:
            self.state["position"] = "long"

        elif has_short:
            self.state["position"] = "short"

        else:
            self.state["position"] = None

    def _check_daily_risk(self):
        """
        Check account equity against the
        daily drawdown limit.
        """
        if self.daily_starting_equity is None:
            return

        account_info = (mt5.account_info())
        if account_info is None:
            return

        (allowed, message, drawdown) = check_daily_drawdown(self.config, self.daily_starting_equity, account_info.equity)

        self.state["daily_drawdown"] = drawdown

        if not allowed:
            self.daily_loss_blocked = True

            self.state["daily_loss_blocked"] = True

            # Only alert once for a specific drawdown value.
            if (self.last_drawdown_alert != round(drawdown, 2)):
                self._send_alert(message)

                self.last_drawdown_alert = (round(drawdown, 2))

        else:
            self.daily_loss_blocked = False

            self.state["daily_loss_blocked"] = False

    def _fetch_historical_data(self, symbol, timeframe, count=100):
        rates = (
            mt5.copy_rates_from_pos(
                symbol,
                timeframe,
                0,
                count
            )
        )

        if rates is None:
            logging.error(
                (
                    "Failed to retrieve "
                    "historical data: %s"
                ),

                mt5.last_error()
            )

            return None

        if len(rates) == 0:
            return None

        data = pd.DataFrame(rates)

        data["time"] = pd.to_datetime(data["time"], unit="s")

        return data

    def _broadcast_state(self, symbol_info, tick):
        spread = (tick.ask - tick.bid)

        self.socketio.emit(

            "price_update",
            {
                "symbol": self.config["symbol"],
                "bid": round(tick.bid, symbol_info.digits),
                "ask": round(tick.ask, symbol_info.digits),
                "price": round(self.state["current_price"], symbol_info.digits),
                "spread": round(spread, symbol_info.digits),
                "position": self.state["position"],
                "open_positions": self.state["open_positions"],
                "running": self.running,
                "last_signal": self.state["last_signal"],
                "daily_drawdown": round(self.state["daily_drawdown"], 2),
                "daily_loss_blocked": self.state["daily_loss_blocked"]
            }
        )

    def _send_alert(self, message):
        logging.info(message)

        self.state["alerts"].append(message)

        self.socketio.emit(

            "alert",
            {
                "message": message
            }
        )
        
    def _reset_daily_risk_if_needed(self):
        """
        Reset daily risk tracking when the
        calendar day changes.
        """
        today = (datetime.now().date())

        if self.risk_date == today:
            return

        self.risk_date = today
        self.daily_starting_equity = (get_daily_starting_equity())
        self.daily_loss_blocked = False
        self.last_drawdown_alert = None
        self.state["daily_loss_blocked"] = False
        self.state["daily_drawdown"] = 0.0


        logging.info(
            (
                "Daily risk reset. "
                "Starting equity: %.2f"
            ),
            self.daily_starting_equity
            or 0
        )