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
    Calculate Stop Loss and Take Profit
    based on the entry price.
    """

    if order_type == mt5.ORDER_TYPE_BUY:

        sl = (
            entry_price
            - (
                stop_loss_pips
                * (
                    symbol_info.point
                    * (
                        10
                        if symbol_info.digits
                        in (3, 5)
                        else 1
                    )
                )
            )
        )

        tp = (
            entry_price
            + (
                take_profit_pips
                * (
                    symbol_info.point
                    * (
                        10
                        if symbol_info.digits
                        in (3, 5)
                        else 1
                    )
                )
            )
        )


    elif order_type == mt5.ORDER_TYPE_SELL:

        sl = (
            entry_price
            + (
                stop_loss_pips
                * (
                    symbol_info.point
                    * (
                        10
                        if symbol_info.digits
                        in (3, 5)
                        else 1
                    )
                )
            )
        )

        tp = (
            entry_price
            - (
                take_profit_pips
                * (
                    symbol_info.point
                    * (
                        10
                        if symbol_info.digits
                        in (3, 5)
                        else 1
                    )
                )
            )
        )

    else:

        return None, None

    sl = round(sl, symbol_info.digits)
    tp = round(tp, symbol_info.digits)

    return sl, tp


def execute_market_order(config, symbol_info, tick, order_type, volume):
    """
    Validate and execute a market order.

    Returns:
        tuple[bool, str, object]
    """

    symbol = config[
        "symbol"
    ]

    entry_price = get_order_price(
        tick,
        order_type
    )

    if entry_price is None:

        return (
            False,
            "Invalid order type.",
            None
        )

    sl, tp = calculate_sl_tp(
        entry_price,
        order_type,
        config[
            "stop_loss_pips"
        ],
        config[
            "take_profit_pips"
        ],
        symbol_info
    )

    if sl is None or tp is None:

        return (
            False,
            "Failed to calculate SL/TP.",
            None
        )

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
        "type_filling": mt5.ORDER_FILLING_IOC
    }

    logging.info(
        "Preparing order: "
        "%s | Volume: %s | "
        "Entry: %s | SL: %s | TP: %s",
        symbol,
        volume,
        entry_price,
        sl,
        tp
    )

    # Validate order with MT5 before execution
    check_result = mt5.order_check(
        request
    )

    if check_result is None:

        return (
            False,
            (
                "MT5 order_check() failed: "
                f"{mt5.last_error()}"
            ),
            None
        )

    if check_result.retcode != 0:

        return (
            False,
            (
                "Order validation failed: "
                f"{check_result.comment}"
            ),
            check_result
        )

    # Execute order
    result = mt5.order_send(
        request
    )

    if result is None:

        return (
            False,
            (
                "MT5 order_send() returned "
                f"None: {mt5.last_error()}"
            ),
            None
        )

    if result.retcode != mt5.TRADE_RETCODE_DONE:

        return (
            False,
            (
                "Order execution failed: "
                f"{result.retcode} - "
                f"{result.comment}"
            ),
            result
        )

    logging.info(
        "Order executed successfully: "
        "%s | Ticket: %s",
        symbol,
        result.order
    )

    return (
        True,
        (
            f"Order executed successfully. "
            f"Ticket: {result.order}"
        ),
        result
    )