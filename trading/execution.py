import logging
import MetaTrader5 as mt5

def get_order_price(tick, order_type):
    """
    Return the correct execution price.

    BUY  -> Ask
    SELL -> Bid
    """

    if order_type == mt5.ORDER_TYPE_BUY:
        return tick.ask

    if order_type == mt5.ORDER_TYPE_SELL:
        return tick.bid

    return None

def calculate_sl_tp(entry_price, order_type, stop_loss_pips, take_profit_pips, symbol_info):
    """
    Calculate Stop Loss and Take Profit based on the entry price.
    """

    # Calculate the point value based on the symbol's precision
    point_value = symbol_info.point * (10 if symbol_info.digits in (3, 5) else 1)

    if order_type == mt5.ORDER_TYPE_BUY:
        # Calculate Stop Loss for a BUY order
        sl = entry_price - (stop_loss_pips * point_value)
        # Calculate Take Profit for a BUY order
        tp = entry_price + (take_profit_pips * point_value)

    elif order_type == mt5.ORDER_TYPE_SELL:
        # Calculate Stop Loss for a SELL order
        sl = entry_price + (stop_loss_pips * point_value)
        # Calculate Take Profit for a SELL order
        tp = entry_price - (take_profit_pips * point_value)

    else:
        # Return None if the order type is not recognized
        return None, None

    # Round the calculated values to the correct number of decimal places
    sl = round(sl, symbol_info.digits)
    tp = round(tp, symbol_info.digits)

    return sl, tp


def execute_market_order(config, symbol_info, tick, order_type, volume):
    """
    Validate and execute a market order.

    Returns:
        tuple[bool, str, object]
    """
    logging.info(f"execute_market_order called with: config={config}, symbol_info={symbol_info}, tick={tick}, order_type={order_type}, volume={volume}")
    try:
        symbol = config["symbol"]
        entry_price = get_order_price(tick, order_type)

        if entry_price is None:
            return False, "Invalid order type.", None

        sl, tp = calculate_sl_tp(entry_price, order_type, config["stop_loss_pips"], config["take_profit_pips"], symbol_info)

        if sl is None or tp is None:
            logging.error("Failed to calculate SL/TP.")
            return False, "Failed to calculate SL/TP.", None
        
        if symbol_info.filling_mode & 1:
            filling_mode = mt5.ORDER_FILLING_FOK
        elif symbol_info.filling_mode & 2:
            filling_mode = mt5.ORDER_FILLING_IOC
        else:
            filling_mode = mt5.ORDER_FILLING_RETURN

        logging.info(f"Selected filling mode: {filling_mode}")

        request = {

            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": order_type,
            "price": entry_price,
            "sl": sl,
            "tp": tp,
            "deviation": 20,
            "magic": 123456,
            "comment": "Python Bot Order",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": filling_mode
        }

        logging.info(f"Order request: {request}")
        logging.info(f"Preparing order: {symbol} | Volume: {volume} | Entry: {entry_price} | SL: {sl} | TP: {tp}")

        # Validate order with MT5 before execution
        check_result = mt5.order_check(request)

        if check_result is None:
            logging.error(f"MT5 order_check() failed: {mt5.last_error()}")
            return False, f"MT5 order_check() failed.", None

        if check_result.retcode != 0:
            logging.error(f"Order validation failed: {check_result.comment}")
            return False, f"Order validation failed: {check_result.comment}", check_result

        # Execute order
        result = mt5.order_send(request)

        if result is None:
            logging.error(f"MT5 order_send() returned None: {mt5.last_error()}")
            return False, f"MT5 order_send() returned None.", None

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logging.error(f"Order execution failed: {result.retcode} - {result.comment}")
            return False, f"Order execution failed: {result.retcode} - {result.comment}", result

        logging.info(f"Order executed successfully: {symbol} | Ticket: {result.order}")

        return True, f"Order executed successfully. Ticket: {result.order}", result

    except Exception as e:
        logging.error(f"Exception during order execution: {e}")
        return False, str(e), None