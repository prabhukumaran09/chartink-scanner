"""
scanner/indicators.py
Pure-Python / NumPy technical indicator calculations.
Used when historical OHLCV data is available (e.g. from jugaad-data).
"""

import numpy as np


def compute_rsi(closes: list[float], period: int = 14) -> float | None:
    """Standard Wilder RSI on a list of closing prices."""
    if len(closes) < period + 1:
        return None
    closes = np.array(closes, dtype=float)
    deltas = np.diff(closes)
    gains  = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    rs  = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return round(float(rsi), 2)


def compute_ema(closes: list[float], period: int) -> list[float]:
    """Exponential moving average."""
    closes = np.array(closes, dtype=float)
    k = 2 / (period + 1)
    ema = [closes[0]]
    for price in closes[1:]:
        ema.append(price * k + ema[-1] * (1 - k))
    return ema


def compute_macd(closes: list[float],
                 fast: int = 12, slow: int = 26, signal: int = 9
                 ) -> dict | None:
    """
    Returns dict with keys: macd_line, signal_line, histogram, crossover_bull, crossover_bear
    """
    if len(closes) < slow + signal:
        return None
    ema_fast   = compute_ema(closes, fast)
    ema_slow   = compute_ema(closes, slow)
    macd_line  = [f - s for f, s in zip(ema_fast, ema_slow)]
    sig_line   = compute_ema(macd_line, signal)
    histogram  = [m - s for m, s in zip(macd_line, sig_line)]

    bull_cross = histogram[-1] > 0 and histogram[-2] <= 0
    bear_cross = histogram[-1] < 0 and histogram[-2] >= 0

    return {
        "macd_line":      round(macd_line[-1], 4),
        "signal_line":    round(sig_line[-1], 4),
        "histogram":      round(histogram[-1], 4),
        "crossover_bull": bull_cross,
        "crossover_bear": bear_cross,
    }


def compute_bollinger(closes: list[float], period: int = 20, std_dev: float = 2.0) -> dict | None:
    """Bollinger Bands — returns upper, mid, lower, bandwidth, squeeze flag."""
    if len(closes) < period:
        return None
    arr    = np.array(closes[-period:], dtype=float)
    mid    = float(np.mean(arr))
    std    = float(np.std(arr, ddof=1))
    upper  = mid + std_dev * std
    lower  = mid - std_dev * std
    bw     = round((upper - lower) / mid * 100, 2) if mid else 0
    # Squeeze: bandwidth in bottom 10% of recent 50-bar range (proxy)
    squeeze = bw < 5.0

    return {
        "upper":     round(upper, 2),
        "mid":       round(mid, 2),
        "lower":     round(lower, 2),
        "bandwidth": bw,
        "squeeze":   squeeze,
    }


def compute_sma(closes: list[float], period: int) -> float | None:
    """Simple moving average."""
    if len(closes) < period:
        return None
    return round(float(np.mean(closes[-period:])), 2)


def volume_ratio(today_vol: int, avg_vol: int) -> float:
    """Ratio of today's volume to average volume."""
    if avg_vol <= 0:
        return 0.0
    return round(today_vol / avg_vol, 2)
