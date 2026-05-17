"""
scanner/fno_list.py
Fetches the live FNO stock list using nsepython's fnolist().
Falls back to hardcoded list if nsepython fails.
"""

# ── Clean fallback — verified FNO symbols ────────────────────────────────────
_FALLBACK_FNO = sorted([
    "AARTIIND","ABB","ABBOTINDIA","ABCAPITAL","ABFRL","ACC","ADANIENT",
    "ADANIGREEN","ADANIPORTS","ADANIPOWER","ATGL","ALKEM","AMBUJACEM",
    "ANGELONE","APLAPOLLO","APOLLOHOSP","APOLLOTYRE","ASHOKLEY","ASIANPAINT",
    "ASTRAL","ATUL","AUBANK","AUROPHARMA","AXISBANK",
    "BAJAJ-AUTO","BAJAJFINSV","BAJFINANCE","BALKRISIND","BANDHANBNK",
    "BANKBARODA","BANKINDIA","BATAINDIA","BEL","BERGEPAINT","BHARATFORG",
    "BHARTIARTL","BHEL","BIOCON","BOSCHLTD","BPCL","BRITANNIA","BSE","BSOFT",
    "CAMS","CANFINHOME","CANBK","CDSL","CHAMBLFERT","CHOLAFIN","CIPLA",
    "COALINDIA","COFORGE","COLPAL","CONCOR","COROMANDEL","CROMPTON","CUB","CUMMINSIND",
    "DABUR","DALBHARAT","DEEPAKNTR","DIVISLAB","DIXON","DLF","DMART","DRREDDY",
    "EICHERMOT","ESCORTS","EXIDEIND",
    "FEDERALBNK","FLUOROCHEM",
    "GAIL","GLENMARK","GMRINFRA","GNFC","GODREJCP","GODREJPROP","GRANULES",
    "GRASIM","GSPL","GUJGASLTD",
    "HAL","HAVELLS","HCLTECH","HDFCAMC","HDFCBANK","HDFCLIFE","HEROMOTOCO",
    "HINDALCO","HINDCOPPER","HINDPETRO","HINDUNILVR","HONAUT",
    "ICICIBANK","ICICIGI","ICICIPRULI","IDEA","IDFCFIRSTB","IEX","IGL",
    "INDIAMART","INDIACEM","INDIGO","INDUSINDBK","INDUSTOWER","INFY","INTELLECT",
    "IOC","IPCALAB","IRB","IRCTC","IRFC","ITC",
    "JINDALSTEL","JKCEMENT","JSWENERGY","JSWSTEEL","JUBLFOOD","JUSTDIAL",
    "KAJARIACER","KALYANKJIL","KEI","KOTAKBANK",
    "LALPATHLAB","LAURUSLABS","LICHSGFIN","LICI","LT","LTIM","LTTS","LUPIN",
    "M&M","M&MFIN","MANAPPURAM","MARICO","MARUTI","MCX","METROPOLIS",
    "MFSL","MOTHERSON","MPHASIS","MRF","MUTHOOTFIN",
    "NATIONALUM","NAUKRI","NAVINFLUOR","NBCC","NCC","NESTLEIND","NMDC","NTPC","NYKAA",
    "OBEROIRLTY","OFSS","OIL","ONGC",
    "PAGEIND","PATANJALI","PEL","PERSISTENT","PETRONET","PFC","PIDILITIND",
    "PIIND","PNB","POLYCAB","POLICYBZR","POWERGRID","PVRINOX",
    "RAIN","RAMCOCEM","RBLBANK","RECLTD","RELIANCE",
    "SAIL","SBICARD","SBILIFE","SBIN","SHREECEM","SHRIRAMFIN","SIEMENS",
    "SJVN","SKFINDIA","SOBHA","SONACOMS","SRF","SUNDARMFIN","SUNPHARMA",
    "SUNTV","SUPREMEIND","SYNGENE",
    "TATACHEM","TATACOMM","TATACONSUM","TATAELXSI","TATAMOTORS","TATAPOWER",
    "TATASTEEL","TCS","TECHM","TIINDIA","TITAN","TORNTPHARM","TORNTPOWER",
    "TRENT","TVSMOTOR",
    "UBL","UCOBANK","UJJIVANSFB","ULTRACEMCO","UNIONBANK","UPL",
    "VBL","VEDL","VOLTAS",
    "WIPRO",
    "ZOMATO","ZYDUSLIFE",
])

_cached_list  = None   # cached after first successful fetch
_source_label = None


def _fetch_via_nsepython() -> list[str] | None:
    """Fetch live FNO list using nsepython.fnolist()."""
    try:
        from nsepython import fnolist
        stocks = fnolist()
        if stocks and len(stocks) > 50:
            # fnolist() returns a list of symbols directly
            cleaned = sorted(set(str(s).strip().upper() for s in stocks if s))
            print(f"[fno_list] nsepython fnolist() → {len(cleaned)} symbols")
            return cleaned
        return None
    except Exception as e:
        print(f"[fno_list] nsepython fnolist() failed: {e}")
        return None


def refresh_live_list() -> None:
    """Force a fresh fetch — call this on app startup or manual refresh."""
    global _cached_list, _source_label
    _cached_list  = None
    _source_label = None
    get_fno_stocks()


def get_fno_stocks(limit: int = None) -> list[str]:
    """
    Returns the current FNO stock list.
    - First call fetches live via nsepython.fnolist()
    - Subsequent calls return cached result
    - Falls back to hardcoded list if nsepython fails
    """
    global _cached_list, _source_label

    if _cached_list is None:
        live = _fetch_via_nsepython()
        if live:
            _cached_list  = live
            _source_label = f"🟢 Live via nsepython ({len(live)} stocks)"
        else:
            _cached_list  = _FALLBACK_FNO
            _source_label = f"🟡 Fallback list ({len(_FALLBACK_FNO)} stocks — nsepython unavailable)"

    return _cached_list[:limit] if limit else _cached_list


def get_fno_count() -> int:
    return len(get_fno_stocks())


def get_fno_source() -> str:
    if _source_label is None:
        get_fno_stocks()   # trigger fetch so label is set
    return _source_label
