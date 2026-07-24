import math
from datetime import datetime
import MetaTrader5 as mt5

def validate_trading_config(config):
    """
    Validate user-provided trading parameters.

    Returns:
        list[str]: Validation errors.
    """

    errors = []

    if not config["symbol"]:
        errors.append(
            "Trading symbol is required."
        )

    if config["risk_percentage"] <= 0:
        errors.append(
            "Risk percentage must be greater than 0."
        )

    if config["risk_percentage"] > 2:
        errors.append(
            "Risk percentage cannot exceed 2%."
        )

    if config["stop_loss_pips"] <= 0:
        errors.append(
            "Stop loss must be greater than 0."
        )

    if config["take_profit_pips"] <= 0:
        errors.append(
            "Take profit must be greater than 0."
        )

    if config["max_open_positions"] < 1:
        errors.append(
            "Maximum open positions must be at least 1."
        )

    if config["max_daily_loss_percentage"] <= 0:
        errors.append(
            "Maximum daily loss must be greater than 0."
        )

    if config["max_spread_pips"] <= 0:
        errors.append(
            "Maximum spread must be greater than 0."
        )

    return errors

def get_open_positions(symbol=None):
    """
    Get actual open positions from MetaTrader 5.

    MT5 is treated as the source of truth.

    Returns:
        tuple: Open positions or empty tuple.
    """

    if symbol:
        positions = mt5.positions_get(
            symbol=symbol
        )

    else:
        positions = mt5.positions_get()

    if positions is None:
        return ()

    return positions

def count_open_positions(symbol=None):
    """
    Count actual open MT5 positions.
    """
    positions = get_open_positions(
        symbol
    )

    return len(positions)

def can_open_position(config):
    """
    Check whether the bot is allowed to open
    another position for the configured symbol.

    Returns:
        tuple[bool, str]
    """
    open_positions = count_open_positions(
        config["symbol"]
    )

    maximum = config["max_open_positions"]

    if open_positions >= maximum:
        return (
            False,
            (
                f"Maximum open positions "
                f"reached: "
                f"{open_positions}/"
                f"{maximum}"
            )
        )

    return (
        True,
        "Position limit check passed."
    )

def get_pip_size(symbol_info):
    """
    Determine pip size for a Forex symbol.

    For 5-digit and 3-digit symbols,
    one pip equals 10 points.

    For other symbols, one pip equals
    one point.

    Returns:
        float
    """
    if symbol_info.digits in (3, 5):
        return symbol_info.point * 10

    return symbol_info.point


def get_spread_pips(symbol_info, tick):
    """
    Calculate current spread in pips.
    """
    pip_size = get_pip_size(
        symbol_info
    )

    spread = tick.ask - tick.bid

    return spread / pip_size

def check_spread(config, symbol_info, tick):
    """
    Check whether current spread is
    within the configured limit.

    Returns:
        tuple[bool, str, float]
    """
    spread_pips = get_spread_pips(symbol_info, tick)

    maximum_spread = config["max_spread_pips"]

    if spread_pips > maximum_spread:
        return (
            False,
            (
                f"Spread too high: "
                f"{spread_pips:.2f} pips "
                f"(maximum "
                f"{maximum_spread:.2f})"
            ),
            spread_pips
        )

    return (
        True,
        (
            f"Spread acceptable: "
            f"{spread_pips:.2f} pips"
        ),
        spread_pips
    )

def normalize_volume(volume, symbol_info):
    """
    Normalize volume according to the
    broker's minimum, maximum and step.
    """
    volume_min = symbol_info.volume_min
    volume_max = symbol_info.volume_max
    volume_step = symbol_info.volume_step


    if volume_step <= 0:
        return None

    volume = max(
        volume_min,
        min(
            volume,
            volume_max
        )
    )

    steps = math.floor(
        volume / volume_step
    )

    normalized_volume = (
        steps * volume_step
    )

    normalized_volume = max(
        volume_min,
        min(
            normalized_volume,
            volume_max
        )
    )

    # Determine decimal precision
    # required by the volume step.
    if volume_step >= 1:
        decimals = 0
    elif volume_step >= 0.1:
        decimals = 1
    elif volume_step >= 0.01:
        decimals = 2
    elif volume_step >= 0.001:
        decimals = 3
    else:
        decimals = 4

    return round(normalized_volume, decimals)

def calculate_position_size(account_balance, risk_percentage, stop_loss_pips, symbol_info):
    """
    Calculate position volume using
    the symbol's actual tick value.

    Risk amount:
        balance * risk %

    Uses MT5 tick size and tick value
    rather than assuming $10 per pip.
    """
    if account_balance <= 0:
        return None

    if risk_percentage <= 0:
        return None

    if stop_loss_pips <= 0:
        return None

    tick_size = symbol_info.trade_tick_size
    tick_value = symbol_info.trade_tick_value

    if tick_size <= 0 or tick_value <= 0:
        return None

    pip_size = get_pip_size(symbol_info)

    risk_amount = (account_balance * risk_percentage / 100)

    loss_per_lot = (stop_loss_pips * pip_size / tick_size * tick_value)

    if loss_per_lot <= 0:
        return None

    raw_volume = (risk_amount / loss_per_lot)

    return normalize_volume(raw_volume, symbol_info)
    
def get_start_of_day():
    """
    Return the current day at midnight.
    """
    now = datetime.now()
    return datetime(now.year, now.month, now.day)

def get_daily_starting_equity():
    """
    Find the account equity at the beginning
    of the current trading day.

    Uses the current balance plus today's
    realized profit/loss.

    This reconstructs the approximate equity
    before today's realized trading activity.
    """
    account_info = mt5.account_info()
    if account_info is None:
        return None

    start_of_day = get_start_of_day()

    deals = mt5.history_deals_get(start_of_day, datetime.now())

    if deals is None:
        return account_info.equity

    realized_profit = 0.0

    for deal in deals:

        # Only count closing deals.
        # Entry OUT represents a position
        # being closed.
        if deal.entry == mt5.DEAL_ENTRY_OUT:
            realized_profit += (deal.profit + deal.swap + deal.commission)

    starting_equity = (account_info.equity - realized_profit)

    return starting_equity

def calculate_daily_drawdown(starting_equity, current_equity):
    """
    Calculate current daily equity drawdown
    as a percentage.
    """
    if starting_equity is None:
        return None

    if starting_equity <= 0:
        return None

    drawdown = (
        (
            starting_equity
            - current_equity
        )
        / starting_equity
    ) * 100

    return max(0.0, drawdown)

def check_daily_drawdown(config, starting_equity, current_equity):
    """
    Determine whether the daily loss limit
    has been breached.

    Returns:
        tuple[bool, str, float]

    True means trading is allowed.

    False means the circuit breaker has
    been triggered.
    """
    drawdown = calculate_daily_drawdown(starting_equity, current_equity)

    if drawdown is None:
        return (
            False,
            "Unable to calculate daily drawdown.",
            0.0
        )

    maximum_drawdown = config["max_daily_loss_percentage"]

    if drawdown >= maximum_drawdown:
        return (
            False,
            (
                f"DAILY LOSS LIMIT BREACHED: "
                f"{drawdown:.2f}% "
                f"(maximum "
                f"{maximum_drawdown:.2f}%). "
                f"New trades are blocked."
            ),
            drawdown
        )

    return (
        True,
        (
            f"Daily drawdown acceptable: "
            f"{drawdown:.2f}%"
        ),
        drawdown
    )