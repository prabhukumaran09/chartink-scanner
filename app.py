import streamlit as st
import pandas as pd
import time
from datetime import datetime
from scanner.engine import run_all_scans, market_status_label, is_market_open
from scanner.fno_list import get_fno_stocks, get_fno_count
from alerts.telegram_alert import send_telegram_batch
from alerts.desktop_alert import send_desktop_alert
from config import load_config, save_config

st.set_page_config(page_title="FNO Scanner – NSE", page_icon="📈", layout="wide")

st.markdown("""
<style>
[data-testid="stMetricValue"] { font-size:1.5rem; font-weight:700; }
.sig-bull  { background:#e8f5e9; border-left:4px solid #2e7d32; padding:6px 12px; border-radius:4px; margin:3px 0; }
.sig-bear  { background:#ffebee; border-left:4px solid #c62828; padding:6px 12px; border-radius:4px; margin:3px 0; }
.sig-other { background:#fff8e1; border-left:4px solid #f9a825; padding:6px 12px; border-radius:4px; margin:3px 0; }
.badge { display:inline-block; padding:1px 8px; border-radius:10px; font-size:11px; font-weight:700; }
.b-bull { background:#c8e6c9; color:#1b5e20; }
.b-bear { background:#ffcdd2; color:#b71c1c; }
.b-neu  { background:#eeeeee; color:#333; }
</style>
""", unsafe_allow_html=True)

if "scan_results"    not in st.session_state: st.session_state.scan_results    = []
if "last_scan_time"  not in st.session_state: st.session_state.last_scan_time  = None
if "alert_history"   not in st.session_state: st.session_state.alert_history   = []
if "custom_conditions" not in st.session_state: st.session_state.custom_conditions = []

cfg = load_config()

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Config")
    st.caption(market_status_label())
    st.divider()

    st.subheader("🔔 Alerts")
    cfg["desktop_alerts"]  = st.toggle("Desktop Alerts",  value=cfg.get("desktop_alerts", True))
    cfg["telegram_alerts"] = st.toggle("Telegram Alerts", value=cfg.get("telegram_alerts", False))
    if cfg["telegram_alerts"]:
        cfg["telegram_token"]   = st.text_input("Bot Token",  value=cfg.get("telegram_token",""),   type="password")
        cfg["telegram_chat_id"] = st.text_input("Chat ID",    value=cfg.get("telegram_chat_id",""))

    st.divider()
    st.subheader("⏱ Auto-Scan")
    cfg["auto_scan"] = st.toggle("Auto-Scan", value=cfg.get("auto_scan", False))
    if cfg["auto_scan"]:
        cfg["scan_interval"] = st.slider("Every (min)", 1, 30, cfg.get("scan_interval", 5))

    st.divider()
    st.subheader("🎛 Filters")
    cfg["min_price"]        = st.number_input("Min Price ₹",    value=cfg.get("min_price", 100),        step=50)
    cfg["min_volume_ratio"] = st.number_input("Min Vol Ratio ×", value=cfg.get("min_volume_ratio", 1.5), step=0.1, format="%.1f")

    st.divider()
    if st.button("💾 Save Config"): save_config(cfg); st.success("Saved!")

# ── Header ───────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns([4, 2, 2, 2])
with c1: st.title("📊 NSE FNO Scanner")
with c2: st.metric("FNO Universe", f"{get_fno_count()} stocks")
with c3:
    lbl = st.session_state.last_scan_time.strftime("%H:%M:%S") if st.session_state.last_scan_time else "—"
    st.metric("Last Scan", lbl)
with c4:
    run_scan = st.button("🚀 Run Scan Now", type="primary", use_container_width=True)

st.caption(market_status_label())
st.divider()

# ── Tabs ─────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["📈 Dashboard", "🔧 Conditions", "📋 Results", "📜 History", "🛠 Setup"])

# ── Dashboard ────────────────────────────────────────────────────────────────
with tab1:
    results = st.session_state.scan_results
    if not results:
        st.info("👆 Click **Run Scan Now** to scan all FNO stocks.")
    else:
        df = pd.DataFrame(results)
        bullish = df[df["badge"] == "bull"]
        bearish = df[df["badge"] == "bear"]

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Signals",   len(df))
        m2.metric("🟢 Bullish",      len(bullish))
        m3.metric("🔴 Bearish",      len(bearish))
        m4.metric("🟡 Neutral",      len(df) - len(bullish) - len(bearish))

        if "scanner" in df.columns:
            st.bar_chart(df["scanner"].value_counts())

        st.subheader("🚨 Live Signals")
        for _, r in df.sort_values("change_pct", ascending=False).iterrows():
            badge  = r.get("badge","neutral")
            css    = "sig-bull" if badge=="bull" else ("sig-bear" if badge=="bear" else "sig-other")
            bcss   = "b-bull"   if badge=="bull" else ("b-bear"   if badge=="bear" else "b-neu")
            chg    = r.get("change_pct", 0)
            chg_s  = f"+{chg}%" if chg >= 0 else f"{chg}%"
            st.markdown(
                f'<div class="{css}"><b>{r["symbol"]}</b> &nbsp; ₹{r["ltp"]} '
                f'<span style="color:{"#2e7d32" if chg>=0 else "#c62828"}">({chg_s})</span> &nbsp;'
                f'<span class="badge {bcss}">{r["signal"]}</span> &nbsp;'
                f'<span style="font-size:12px;color:#555">{r.get("scanner","")} | {r.get("notes","")}</span></div>',
                unsafe_allow_html=True
            )

# ── Conditions ───────────────────────────────────────────────────────────────
with tab2:
    st.subheader("🔧 Scanner Conditions")
    st.markdown("**Built-in Scanners**")
    ca, cb = st.columns(2)
    with ca:
        cfg["scan_52w_high"]      = st.checkbox("52W High Breakout",      value=cfg.get("scan_52w_high", True))
        cfg["scan_52w_low"]       = st.checkbox("52W Low Breakdown",       value=cfg.get("scan_52w_low", True))
        cfg["scan_volume_surge"]  = st.checkbox("Volume Surge (>1.5× avg)",value=cfg.get("scan_volume_surge", True))
        cfg["scan_price_breakout"]= st.checkbox("Intraday High Breakout",  value=cfg.get("scan_price_breakout", True))
    with cb:
        cfg["scan_rsi_ob"]        = st.checkbox("RSI Overbought (>70)",    value=cfg.get("scan_rsi_ob", True))
        cfg["scan_rsi_os"]        = st.checkbox("RSI Oversold (<30)",      value=cfg.get("scan_rsi_os", True))
        cfg["scan_macd_cross"]    = st.checkbox("Strong Momentum (±2.5%)", value=cfg.get("scan_macd_cross", True))

    st.divider()
    st.markdown("**➕ Custom Scanner**")
    if "custom_conditions" not in st.session_state:
        st.session_state.custom_conditions = cfg.get("custom_conditions", [])

    with st.expander("Add Custom Condition"):
        cname = st.text_input("Name", placeholder="e.g. Gap Up + Volume")
        cdesc = st.text_area("Description (optional)", height=60)
        x1, x2, x3, x4 = st.columns(4)
        with x1: ind = st.selectbox("Indicator", ["Price","Volume","RSI","Close-Open %","High-Low %","Volume/20D Avg"])
        with x2: op  = st.selectbox("Operator",  [">","<",">=","<="])
        with x3: val = st.number_input("Value", value=50.0, format="%.2f")
        with x4: unit= st.selectbox("Unit", ["absolute","% change","x (multiplier)"])
        if st.button("➕ Add"):
            if cname:
                st.session_state.custom_conditions.append({
                    "name": cname, "description": cdesc,
                    "rule": f"{ind} {op} {val} {unit}", "enabled": True,
                    "created": datetime.now().strftime("%Y-%m-%d %H:%M")
                })
                cfg["custom_conditions"] = st.session_state.custom_conditions
                save_config(cfg); st.success(f"Added: {cname}"); st.rerun()

    for i, cond in enumerate(st.session_state.custom_conditions):
        cc1, cc2 = st.columns([5,1])
        with cc1:
            en = st.checkbox(f"**{cond['name']}** — _{cond.get('rule','')}_ ({cond.get('created','')})",
                             value=cond.get("enabled",True), key=f"c{i}")
            st.session_state.custom_conditions[i]["enabled"] = en
        with cc2:
            if st.button("🗑", key=f"d{i}"):
                st.session_state.custom_conditions.pop(i)
                cfg["custom_conditions"] = st.session_state.custom_conditions
                save_config(cfg); st.rerun()

    if st.button("💾 Save Conditions", type="primary"):
        cfg["custom_conditions"] = st.session_state.custom_conditions
        save_config(cfg); st.success("Saved!")

# ── Results ──────────────────────────────────────────────────────────────────
with tab3:
    if not st.session_state.scan_results:
        st.info("No results yet.")
    else:
        df = pd.DataFrame(st.session_state.scan_results)
        f1, f2 = st.columns(2)
        with f1:
            opts = ["All"] + sorted(df["scanner"].unique().tolist())
            sel  = st.selectbox("Filter Scanner", opts)
        with f2:
            sigs = ["All"] + sorted(df["signal"].unique().tolist())
            ssig = st.selectbox("Filter Signal", sigs)
        fd = df.copy()
        if sel  != "All": fd = fd[fd["scanner"] == sel]
        if ssig != "All": fd = fd[fd["signal"]  == ssig]
        cols = ["symbol","ltp","change_pct","high","low","volume","week52_high","week52_low","signal","scanner","notes"]
        st.dataframe(fd[[c for c in cols if c in fd.columns]], use_container_width=True, hide_index=True)
        st.download_button("⬇️ CSV", fd.to_csv(index=False), "fno_scan.csv", "text/csv")

# ── Alert History ─────────────────────────────────────────────────────────────
with tab4:
    if not st.session_state.alert_history:
        st.info("No alerts yet.")
    else:
        hdf = pd.DataFrame(st.session_state.alert_history)
        st.dataframe(hdf.sort_values("time", ascending=False), use_container_width=True, hide_index=True)
        if st.button("🗑 Clear"): st.session_state.alert_history = []; st.rerun()

# ── Setup ─────────────────────────────────────────────────────────────────────
with tab5:
    st.markdown("""
### Quick Setup
```bash
pip install -r requirements.txt
streamlit run app.py
```
### Telegram
1. **@BotFather** → `/newbot` → copy token  
2. **@userinfobot** → copy your Chat ID  
3. Paste both in sidebar → Save Config

### Deploy Free (Streamlit Cloud)
1. Push to GitHub  
2. [share.streamlit.io](https://share.streamlit.io) → New App → select repo → deploy `app.py`  
3. Settings → Secrets → add Telegram token & chat_id

### Notes
- Data from **NSE public API** — no key needed
- Market hours: **9:15 AM – 3:30 PM IST** (Mon–Fri)
- Outside hours: shows **previous day's closing data** (useful for pre-market prep)
- Scans **~180 FNO stocks** in parallel (~30–60 seconds)

> ⚠️ For education only. Not financial advice.
""")

# ── Scan trigger ──────────────────────────────────────────────────────────────
if run_scan:
    total  = get_fno_count()
    prog   = st.progress(0, text="Initialising NSE session...")
    status = st.empty()

    def progress_cb(done, total, sym):
        pct = done / total
        prog.progress(pct, text=f"Scanning {sym} ... ({done}/{total})")
        status.caption(f"✅ Done: {done} | Signals found: {len(st.session_state.scan_results)}")

    try:
        results = run_all_scans(cfg, progress_cb=progress_cb)
        prog.progress(1.0, text="✅ Scan complete!")
        st.session_state.scan_results   = results
        st.session_state.last_scan_time = datetime.now()

        new_alerts = []
        for r in results:
            if cfg.get("desktop_alerts"):
                send_desktop_alert(r["symbol"], r["signal"], r["ltp"])
            new_alerts.append({"time": datetime.now().strftime("%H:%M:%S"),
                               "symbol": r["symbol"], "signal": r["signal"],
                               "ltp": r["ltp"], "scanner": r["scanner"]})

        if cfg.get("telegram_alerts") and cfg.get("telegram_token") and cfg.get("telegram_chat_id"):
            send_telegram_batch(cfg["telegram_token"], cfg["telegram_chat_id"], results[:20])

        st.session_state.alert_history = new_alerts + st.session_state.alert_history

        if results:
            st.success(f"✅ {len(results)} signal(s) found across {total} FNO stocks!")
        else:
            st.info(f"✅ Scan done — no signals matched. Try adjusting conditions.")
    except Exception as e:
        st.error(f"❌ Scan error: {e}")
        st.exception(e)

if cfg.get("auto_scan") and cfg.get("scan_interval"):
    time.sleep(1); st.rerun()
