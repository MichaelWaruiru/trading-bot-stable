import pandas as pd
import pandas_ta as ta

RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70

def calculate_rsi(data, length=14):
    """
    Calculate RSI for the supplied candle data.
    """
    data["rsi"] = data.ta.rsi(
        length=length
    )

    return data

def generate_rsi_signal(
    data,
    oversold=RSI_OVERSOLD,
    overbought=RSI_OVERBOUGHT
):
    """
    Generate a signal only when RSI crosses
    an oversold or overbought threshold.

    BUY:
        Previous RSI >= 30
        Current RSI < 30

    SELL:
        Previous RSI <= 70
        Current RSI > 70

    Returns:
        'long'
        'short'
        None
    """

    if data is None or data.empty:
        return None

    if "rsi" not in data.columns:
        return None

    if len(data) < 2:

        return None

    previous_rsi = data["rsi"].iloc[-2]

    current_rsi = data["rsi"].iloc[-1]

    if pd.isna(
        previous_rsi
    ) or pd.isna(
        current_rsi
    ):

        return None


    # RSI crossed into oversold territory
    if previous_rsi >= oversold and current_rsi < oversold:
        return "long"

    # RSI crossed into overbought territory
    if previous_rsi <= overbought and current_rsi > overbought:
        return "short"

    return None