"""
scanner/engine.py - Fast parallel NSE fetcher with market hours detection
"""

import requests, json, time
from datetime import datetime, time as dtime
from concurrent.futures import ThreadPoolExecutor, as_completed
from .fno_list import get_fno_stocks

_SESSION = None

def get_session():
    global _SESSION
    if _SESSION is None:
        s = requests.Session()
        s.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.nseindia.com/",
            "Connection": "keep-alive",
        })
        try:
            s.get("https://www.nseindia.com", timeout=8)
        except Exception:
            pass
        _SESSION = s
    return _SESSION

def reset_session():
    global _SESSION
    _SESSION = None

def is_market_open():
    now = datetime.now()
    if now.weekday() >= 5:
        return False
    return dtime(9, 15) <= now.time() <= dtime(15, 30)

def market_status_label():
    if is_market_open():
        return "🟢 Market OPEN — live data"
    now = datetime.now()
    if now.weekday() >= 5:
        return "🔴 Weekend — showing last traded data"
    if now.time() < dtime(9, 15):
        return "🟡 Pre-market — showing previous close data"
    return "🔴 Market CLOSED — showing today's final data"

def fetch_quote(symbol, session, retries=2):
    url = f"https://www.nseindia.com/api/quote-equity?symbol={symbol}"
    for attempt in range(retries):
        try:
            resp = session.get(url, timeout=6)
            if resp.status_code in (401, 403):
                reset_session()
                session = get_session()
                continue
            if resp.status_code != 200:
                return None
            data = resp.json()
            pi   = data.get("priceInfo", {})
            whl  = pi.get("weekHighLow", {})
            ild  = pi.get("intraDayHighLow", {})
            ti   = data.get("tradeInfo", {})

            ltp   = float(pi.get("lastPrice",     0) or 0)
            prev  = float(pi.get("previousClose", ltp) or ltp)
            open_ = float(pi.get("open",          ltp) or ltp)
            high  = float(ild.get("max",          ltp) or ltp)
            low   = float(ild.get("min",          ltp) or ltp)
            vol   = int(ti.get("totalTradedVolume", 0) or 0)
            w52h  = float(whl.get("max", ltp) or ltp)
            w52l  = float(whl.get("min", ltp) or ltp)
            avg_vol = int(vol * 0.55) if vol > 0 else 1
            chg_pct = round((ltp - prev) / prev * 100, 2) if prev else 0

            return {
                "symbol": symbol, "ltp": round(ltp, 2),
                "open": round(open_, 2), "high": round(high, 2),
                "low": round(low, 2), "prev_close": round(prev, 2),
                "volume": vol, "week52_high": round(w52h, 2),
                "week52_low": round(w52l, 2), "change_pct": chg_pct,
                "avg_volume_20d": avg_vol,
            }
        except Exception as e:
            if attempt == retries - 1:
                print(f"[WARN] {symbol}: {e}")
            time.sleep(0.2)
    return None

def _hit(q, signal, scanner, notes, badge="neutral"):
    return {**q, "signal": signal, "scanner": scanner, "notes": notes, "badge": badge}

def _rsi_proxy(q):
    rng = q["week52_high"] - q["week52_low"]
    if rng <= 0: return 50
    return round(((q["ltp"] - q["week52_low"]) / rng) * 100, 1)

def _is_num(s):
    try: float(s); return True
    except: return False

def _eval_rule(q, rule):
    try:
        rule_l = rule.lower()
        MAP = {
            "price":          q["ltp"],
            "volume":         q["volume"],
            "rsi":            _rsi_proxy(q),
            "close-open %":   round((q["ltp"] - q["open"]) / max(q["open"], 1) * 100, 2),
            "high-low %":     round((q["high"] - q["low"]) / max(q["low"], 1) * 100, 2),
            "volume/20d avg": round(q["volume"] / max(q["avg_volume_20d"], 1), 2),
        }
        for name, val in MAP.items():
            if name in rule_l:
                nums = [float(p) for p in rule.split() if _is_num(p)]
                if not nums: continue
                t = nums[0]
                if ">=" in rule: return val >= t
                if "<=" in rule: return val <= t
                if ">"  in rule: return val > t
                if "<"  in rule: return val < t
        return False
    except: return False

def scan_52w_high(q, cfg):
    if cfg.get("scan_52w_high", True) and q["ltp"] >= q["week52_high"] * 0.995:
        return _hit(q, "52W High Breakout", "52W Breakout", f"LTP ₹{q['ltp']} near 52W High ₹{q['week52_high']}", "bull")

def scan_52w_low(q, cfg):
    if cfg.get("scan_52w_low", True) and q["ltp"] <= q["week52_low"] * 1.005:
        return _hit(q, "52W Low Breakdown", "52W Breakdown", f"LTP ₹{q['ltp']} near 52W Low ₹{q['week52_low']}", "bear")

def scan_volume_surge(q, cfg):
    if not cfg.get("scan_volume_surge", True): return None
    thr = cfg.get("min_volume_ratio", 1.5)
    ratio = q["volume"] / max(q["avg_volume_20d"], 1)
    if ratio >= thr:
        return _hit(q, f"Volume Surge ({ratio:.1f}x)", "Volume Surge", f"Vol {q['volume']:,} vs est.avg {q['avg_volume_20d']:,}", "neutral")

def scan_price_breakout(q, cfg):
    if cfg.get("scan_price_breakout", True) and q["high"] > 0 and q["ltp"] >= q["high"] * 0.998:
        pct = round((q["high"] - q["prev_close"]) / q["prev_close"] * 100, 2) if q["prev_close"] else 0
        return _hit(q, f"Intraday High Breakout (+{pct}%)", "Price Breakout", f"LTP = Day High ₹{q['high']}", "bull")

def scan_rsi_ob(q, cfg):
    if not cfg.get("scan_rsi_ob", True): return None
    rsi = _rsi_proxy(q)
    if rsi > 70:
        return _hit(q, f"RSI Overbought ({rsi:.0f})", "RSI", "RSI>70 — potential reversal", "bear")

def scan_rsi_os(q, cfg):
    if not cfg.get("scan_rsi_os", True): return None
    rsi = _rsi_proxy(q)
    if rsi < 30:
        return _hit(q, f"RSI Oversold ({rsi:.0f})", "RSI", "RSI<30 — potential bounce", "bull")

def scan_momentum(q, cfg):
    if cfg.get("scan_macd_cross", True) and q["change_pct"] > 2.5:
        return _hit(q, f"Strong Momentum (+{q['change_pct']}%)", "Momentum", "Price up >2.5% on day", "bull")

def scan_bear_momentum(q, cfg):
    if cfg.get("scan_macd_cross", True) and q["change_pct"] < -2.5:
        return _hit(q, f"Sharp Fall ({q['change_pct']}%)", "Momentum", "Price down >2.5% on day", "bear")

def scan_custom(q, cfg):
    hits = []
    for cond in cfg.get("custom_conditions", []):
        if not cond.get("enabled", True): continue
        if _eval_rule(q, cond.get("rule", "")):
            hits.append(_hit(q, cond["name"], "Custom", cond.get("description", cond.get("rule", "")), "neutral"))
    return hits

SCANNERS = [scan_52w_high, scan_52w_low, scan_volume_surge,
            scan_price_breakout, scan_rsi_ob, scan_rsi_os,
            scan_momentum, scan_bear_momentum]

def run_all_scans(cfg: dict, progress_cb=None) -> list[dict]:
    symbols   = get_fno_stocks()
    min_price = cfg.get("min_price", 100)
    results   = []
    session   = get_session()
    total     = len(symbols)
    done      = 0

    def scan_one(symbol):
        q = fetch_quote(symbol, session)
        if not q or q["ltp"] < min_price:
            return []
        hits = [h for fn in SCANNERS if (h := fn(q, cfg))]
        hits.extend(scan_custom(q, cfg))
        return hits

    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = {ex.submit(scan_one, sym): sym for sym in symbols}
        for future in as_completed(futures):
            sym = futures[future]
            done += 1
            try:
                results.extend(future.result())
            except Exception as e:
                print(f"[ERROR] {sym}: {e}")
            if progress_cb:
                progress_cb(done, total, sym)

    return results
