import logging
import MetaTrader5 as mt5

def initialize_mt5():
    """Initialize the MetaTrader 5 connection."""

    if not mt5.initialize():
        logging.error(
            "MetaTrader5 initialization failed: %s", mt5.last_error())
        return False

    logging.info("MetaTrader5 initialized successfully")

    return True

def select_symbol(symbol):
    """Make sure a symbol is available in Market Watch."""

    if not mt5.symbol_select(symbol, True):
        logging.error("Failed to select symbol %s: %s", symbol, mt5.last_error())
        return False

    logging.info("Symbol %s selected successfully", symbol)

    return True

def get_symbol_info(symbol):
    """Return MT5 symbol information."""
    symbol_info = mt5.symbol_info(symbol)

    if symbol_info is None:
        logging.error(
            "Failed to get symbol info for %s: %s", symbol, mt5.last_error())
        return None

    return symbol_info

def get_current_tick(symbol):
    """Return the latest market tick."""
    tick = mt5.symbol_info_tick(symbol)

    if tick is None:
        logging.error("Failed to fetch tick for %s: %s", symbol, mt5.last_error())
        return None

    return tick

def shutdown_mt5():
    """Close the MetaTrader 5 connection."""
    mt5.shutdown()
    logging.info("MetaTrader5 connection closed")