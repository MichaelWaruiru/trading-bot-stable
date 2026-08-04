import pandas as pd
import pandas_ta as ta

RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
EMA_LENGTH = 50
SMA_LENGTH = 200

def calculate_indicators(data):
    """
    Calculate RSI for the supplied candle data.
    Indicators:
        RSI (Relative Strength Index) 14
        EMA (Exponential Moving Average) 50
        SMA (Simple Moving Average) 200
    """
    data = data.copy()
    data["rsi"] = data.ta.rsi(length=14)
    
    data["ema_50"] = data.ta.ema(length=EMA_LENGTH)

    data["sma_200"] = data.ta.sma(length=SMA_LENGTH)

    return data

def generate_rsi_signal(data, oversold=RSI_OVERSOLD, overbought=RSI_OVERBOUGHT):
    """
    Generate an RSI transition signal using completed candles only.

    LONG:
        Previous RSI >= 30
        Current RSI < 30
        EMA_50 > SMA_200

    SHORT:
        Previous RSI <= 70
        Current RSI > 70
        EMA_50 < SMA_200

    Returns:
        'long'
        'short'
        None
    """

    if data is None or data.empty:
        return None
    
    required_columns = ["rsi", "ema_50", "sma_200"]
    
    for column in required_columns:
        if column not in data.columns:
            return None
        
    # Removed the currently forming candle
    closed_data = data.iloc[:-1]
    
    if len(closed_data) < 2:
        return None
    
    previous = closed_data.iloc[-2]
    current = closed_data.iloc[-1]
    
    previous_rsi = previous["rsi"]
    current_rsi = current["rsi"]
    
    ema_50 = current["ema_50"]
    sma_200 = current["sma_200"]

    if pd.isna(previous_rsi) or pd.isna(current_rsi):
        return None
    
    if pd.isna(ema_50) or pd.isna(sma_200):
        return None

    # RSI crossed into oversold territory
    if previous_rsi >= oversold and current_rsi < oversold:
        return "long"

    # RSI crossed into overbought territory
    if previous_rsi <= overbought and current_rsi > overbought and ema_50 < sma_200:
        return "short"

    return None