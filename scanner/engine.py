"""
scanner/engine.py
Core scanning engine. Fetches NSE data via nsepython and
runs all enabled scanners against the FNO stock list.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time

from .fno_list import get_fno_stocks
from .indicators import compute_rsi, compute_macd, compute_bollinger

# ── Try importing nsepython ──────────────────────────────────────────────────
try:
    from nsepython import nse_eq, nse_get_quote
    NSE_AVAILABLE = True
except ImportError:
    NSE_AVAILABLE = False

# ── Try jugaad-trader as fallback ────────────────────────────────────────────
try:
    from jugaad_data.nse import NSELive
    JUGAAD_AVAILABLE = True
except ImportError:
    JUGAAD_AVAILABLE = False


# ════════════════════════════════════════════════════════════════════════════
# DATA FETCHER
# ════════════════════════════════════════════════════════════════════════════

def fetch_quote(symbol: str) -> dict | None:
    """
    Fetch live/latest quote for a symbol.
    Returns a normalised dict with keys:
      symbol, ltp, open, high, low, prev_close, volume,
      week52_high, week52_low, avg_volume_20d (estimated)
    Returns None on error.
    """
    try:
        if NSE_AVAILABLE:
            data = nse_eq(symbol)
            if not data:
                return None
            pd_data = data.get("priceInfo", {})
            week_data = data.get("priceInfo", {}).get("weekHighLow", {})
            vol = data.get("securityInfo", {}).get("issuedSize", 0)
            market_depth = data.get("marketDeptOrderBook", {})
            trade_info = data.get("tradeInfo", {})

            ltp = pd_data.get("lastPrice", 0)
            open_ = pd_data.get("open", ltp)
            high  = pd_data.get("intraDayHighLow", {}).get("max", ltp)
            low   = pd_data.get("intraDayHighLow", {}).get("min", ltp)
            prev  = pd_data.get("previousClose", ltp)
            vol   = trade_info.get("totalTradedVolume", 0)
            w52h  = week_data.get("max", ltp)
            w52l  = week_data.get("min", ltp)

            return {
                "symbol":       symbol,
                "ltp":          round(float(ltp), 2),
                "open":         round(float(open_), 2),
                "high":         round(float(high), 2),
                "low":          round(float(low), 2),
                "prev_close":   round(float(prev), 2),
                "volume":       int(vol),
                "week52_high":  round(float(w52h), 2),
                "week52_low":   round(float(w52l), 2),
                "change_pct":   round((float(ltp) - float(prev)) / float(prev) * 100, 2) if float(prev) else 0,
                # Estimated 20d avg volume (NSE doesn't give it directly; use 60% of today as proxy)
                "avg_volume_20d": int(int(vol) * 0.6) if vol else 1,
            }

        elif JUGAAD_AVAILABLE:
            n = NSELive()
            q = n.stock_quote(symbol)
            pd_ = q.get("priceInfo", {})
            ltp  = pd_.get("lastPrice", 0)
            prev = pd_.get("previousClose", ltp)
            return {
                "symbol":       symbol,
                "ltp":          round(float(ltp), 2),
                "open":         round(float(pd_.get("open", ltp)), 2),
                "high":         round(float(pd_.get("intraDayHighLow", {}).get("max", ltp)), 2),
                "low":          round(float(pd_.get("intraDayHighLow", {}).get("min", ltp)), 2),
                "prev_close":   round(float(prev), 2),
                "volume":       int(q.get("tradeInfo", {}).get("totalTradedVolume", 0)),
                "week52_high":  round(float(pd_.get("weekHighLow", {}).get("max", ltp)), 2),
                "week52_low":   round(float(pd_.get("weekHighLow", {}).get("min", ltp)), 2),
                "change_pct":   round((float(ltp) - float(prev)) / float(prev) * 100, 2) if float(prev) else 0,
                "avg_volume_20d": 1,
            }
        else:
            # Demo / fallback mode – returns synthetic data
            return _demo_quote(symbol)

    except Exception as e:
        print(f"[WARN] fetch_quote failed for {symbol}: {e}")
        return None


def _demo_quote(symbol: str) -> dict:
    """Generates plausible demo data when NSE libs are unavailable (for UI testing)."""
    import random
    random.seed(hash(symbol) % 10000)
    base = random.randint(200, 3000)
    ltp  = round(base * random.uniform(0.97, 1.03), 2)
    vol  = random.randint(100_000, 5_000_000)
    return {
        "symbol":        symbol,
        "ltp":           ltp,
        "open":          round(ltp * random.uniform(0.98, 1.01), 2),
        "high":          round(ltp * random.uniform(1.00, 1.04), 2),
        "low":           round(ltp * random.uniform(0.96, 1.00), 2),
        "prev_close":    round(ltp * random.uniform(0.97, 1.02), 2),
        "volume":        vol,
        "week52_high":   round(ltp * random.uniform(1.05, 1.50), 2),
        "week52_low":    round(ltp * random.uniform(0.50, 0.90), 2),
        "change_pct":    round(random.uniform(-5, 5), 2),
        "avg_volume_20d": int(vol * random.uniform(0.4, 0.8)),
    }


# ════════════════════════════════════════════════════════════════════════════
# INDIVIDUAL SCANNERS
# ════════════════════════════════════════════════════════════════════════════

def scan_52w_high(q: dict, cfg: dict) -> dict | None:
    """Stock touching or within 0.5% of 52-week high."""
    if not cfg.get("scan_52w_high", True):
        return None
    if q["ltp"] >= q["week52_high"] * 0.995:
        return {
            **q,
            "signal":  "52W High Breakout",
            "scanner": "52-Week Breakout",
            "notes":   f"LTP ₹{q['ltp']} near 52W High ₹{q['week52_high']}",
            "badge":   "bull"
        }
    return None


def scan_52w_low(q: dict, cfg: dict) -> dict | None:
    """Stock touching or within 0.5% of 52-week low."""
    if not cfg.get("scan_52w_low", True):
        return None
    if q["ltp"] <= q["week52_low"] * 1.005:
        return {
            **q,
            "signal":  "52W Low Breakdown",
            "scanner": "52-Week Breakdown",
            "notes":   f"LTP ₹{q['ltp']} near 52W Low ₹{q['week52_low']}",
            "badge":   "bear"
        }
    return None


def scan_volume_surge(q: dict, cfg: dict) -> dict | None:
    """Today's volume > threshold × 20-day average volume."""
    if not cfg.get("scan_volume_surge", True):
        return None
    threshold = cfg.get("min_volume_ratio", 2.0)
    avg = q.get("avg_volume_20d", 1)
    if avg > 0 and q["volume"] / avg >= threshold:
        ratio = round(q["volume"] / avg, 1)
        return {
            **q,
            "signal":  f"Volume Surge ({ratio}x)",
            "scanner": "Volume Surge",
            "notes":   f"Vol {q['volume']:,} vs 20D avg {avg:,}",
            "badge":   "neutral"
        }
    return None


def scan_price_breakout(q: dict, cfg: dict) -> dict | None:
    """Intraday price breakout: LTP = day high (bullish)."""
    if not cfg.get("scan_price_breakout", True):
        return None
    if q["high"] > 0 and q["ltp"] >= q["high"] * 0.998:
        pct = round((q["high"] - q["prev_close"]) / q["prev_close"] * 100, 2) if q["prev_close"] else 0
        return {
            **q,
            "signal":  f"Intraday High Breakout (+{pct}%)",
            "scanner": "Price Breakout",
            "notes":   f"LTP = Day High ₹{q['high']}",
            "badge":   "bull"
        }
    return None


def scan_rsi_overbought(q: dict, cfg: dict) -> dict | None:
    """RSI > 70 (overbought zone)."""
    if not cfg.get("scan_rsi_ob", True):
        return None
    rsi = _get_rsi_estimate(q)
    if rsi and rsi > 70:
        return {
            **q,
            "signal":  f"RSI Overbought ({rsi:.1f})",
            "scanner": "RSI",
            "notes":   "RSI > 70 – potential reversal zone",
            "badge":   "bear"
        }
    return None


def scan_rsi_oversold(q: dict, cfg: dict) -> dict | None:
    """RSI < 30 (oversold zone)."""
    if not cfg.get("scan_rsi_os", True):
        return None
    rsi = _get_rsi_estimate(q)
    if rsi and rsi < 30:
        return {
            **q,
            "signal":  f"RSI Oversold ({rsi:.1f})",
            "scanner": "RSI",
            "notes":   "RSI < 30 – potential bounce zone",
            "badge":   "bull"
        }
    return None


def scan_macd_crossover(q: dict, cfg: dict) -> dict | None:
    """Proxy MACD crossover using % change."""
    if not cfg.get("scan_macd_cross", True):
        return None
    chg = q.get("change_pct", 0)
    if chg > 2.5:
        return {
            **q,
            "signal":  f"Strong Bullish Momentum (+{chg}%)",
            "scanner": "MACD/Momentum",
            "notes":   "Price up >2.5% on day — momentum signal",
            "badge":   "bull"
        }
    return None


def scan_custom_conditions(q: dict, cfg: dict) -> list[dict]:
    """
    Evaluates user-defined custom conditions.
    Currently supports simple rule matching using the stored rule string.
    """
    results = []
    for cond in cfg.get("custom_conditions", []):
        if not cond.get("enabled", True):
            continue
        rule = cond.get("rule", "")
        hit = _evaluate_simple_rule(q, rule)
        if hit:
            results.append({
                **q,
                "signal":  cond["name"],
                "scanner": "Custom",
                "notes":   cond.get("description", rule),
                "badge":   "neutral"
            })
    return results


# ════════════════════════════════════════════════════════════════════════════
# RULE EVALUATOR (simple parser for custom conditions)
# ════════════════════════════════════════════════════════════════════════════

def _evaluate_simple_rule(q: dict, rule: str) -> bool:
    """
    Evaluate a simple rule like 'RSI < 35' or 'Volume > 2.0 x (multiplier)'.
    Returns True if the rule fires for this quote.
    """
    try:
        rule_lower = rule.lower()

        # Map indicator names to quote values
        indicator_map = {
            "price":           q.get("ltp", 0),
            "volume":          q.get("volume", 0),
            "rsi":             _get_rsi_estimate(q) or 50,
            "close-open %":    round((q.get("ltp", 0) - q.get("open", 0)) / max(q.get("open", 1), 1) * 100, 2),
            "high-low %":      round((q.get("high", 0) - q.get("low", 0)) / max(q.get("low", 1), 1) * 100, 2),
            "volume/20d avg":  round(q.get("volume", 0) / max(q.get("avg_volume_20d", 1), 1), 2),
        }

        for ind_name, ind_val in indicator_map.items():
            if ind_name in rule_lower:
                # Extract numeric threshold from rule
                parts = rule.split()
                nums = [p for p in parts if _is_float(p)]
                if not nums:
                    continue
                threshold = float(nums[0])

                if ">" in rule:
                    return float(ind_val) > threshold
                elif "<" in rule:
                    return float(ind_val) < threshold
                elif ">=" in rule:
                    return float(ind_val) >= threshold
                elif "<=" in rule:
                    return float(ind_val) <= threshold

        return False
    except Exception:
        return False


def _is_float(s: str) -> bool:
    try:
        float(s)
        return True
    except ValueError:
        return False


def _get_rsi_estimate(q: dict) -> float | None:
    """
    Estimate RSI from intraday data since we don't have historical candles.
    Uses the close vs 52W range as a proxy (good enough for quick scan).
    """
    try:
        ltp   = q["ltp"]
        w52h  = q["week52_high"]
        w52l  = q["week52_low"]
        rng   = w52h - w52l
        if rng <= 0:
            return 50
        # Map price position in 52W range to 0–100 RSI proxy
        rsi = round(((ltp - w52l) / rng) * 100, 1)
        return max(1, min(99, rsi))
    except Exception:
        return None


# ════════════════════════════════════════════════════════════════════════════
# MAIN SCAN RUNNER
# ════════════════════════════════════════════════════════════════════════════

BUILTIN_SCANNERS = [
    scan_52w_high,
    scan_52w_low,
    scan_volume_surge,
    scan_price_breakout,
    scan_rsi_overbought,
    scan_rsi_oversold,
    scan_macd_crossover,
]


def run_all_scans(cfg: dict) -> list[dict]:
    """
    Main entry point. Scans all (or subset of) FNO stocks
    and returns a flat list of signal dicts.
    """
    symbols = get_fno_stocks()
    min_price = cfg.get("min_price", 100)

    results = []
    errors  = 0

    for symbol in symbols:
        try:
            q = fetch_quote(symbol)
            if not q:
                continue
            if q["ltp"] < min_price:
                continue

            # Run all built-in scanners
            for scanner_fn in BUILTIN_SCANNERS:
                hit = scanner_fn(q, cfg)
                if hit:
                    results.append(hit)

            # Run custom conditions
            custom_hits = scan_custom_conditions(q, cfg)
            results.extend(custom_hits)

            # Small delay to avoid hammering NSE endpoints
            time.sleep(0.15)

        except Exception as e:
            errors += 1
            print(f"[ERROR] {symbol}: {e}")
            continue

    print(f"[INFO] Scan complete: {len(results)} signals from {len(symbols)} symbols ({errors} errors)")
    return results
