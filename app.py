import streamlit as st
import pandas as pd
import time
import json
import os
from datetime import datetime, date
from scanner.engine import run_all_scans
from scanner.fno_list import get_fno_stocks
from alerts.telegram_alert import send_telegram_alert
from alerts.desktop_alert import send_desktop_alert
from config import load_config, save_config

st.set_page_config(
    page_title="FNO Scanner – NSE",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Minimal custom CSS ──────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stMetricValue"] { font-size: 1.6rem; font-weight: 700; }
.alert-row-green  { background: #e8f5e9; border-left: 4px solid #2e7d32; padding: 6px 10px; border-radius: 4px; margin: 4px 0; }
.alert-row-red    { background: #ffebee; border-left: 4px solid #c62828; padding: 6px 10px; border-radius: 4px; margin: 4px 0; }
.alert-row-yellow { background: #fffde7; border-left: 4px solid #f9a825; padding: 6px 10px; border-radius: 4px; margin: 4px 0; }
.scanner-badge { display:inline-block; padding:2px 8px; border-radius:12px; font-size:12px; font-weight:600; }
.badge-bull { background:#c8e6c9; color:#1b5e20; }
.badge-bear { background:#ffcdd2; color:#b71c1c; }
.badge-neutral { background:#f5f5f5; color:#424242; }
</style>
""", unsafe_allow_html=True)


# ── Session state ────────────────────────────────────────────────────────────
if "scan_results" not in st.session_state:
    st.session_state.scan_results = []
if "last_scan_time" not in st.session_state:
    st.session_state.last_scan_time = None
if "alert_history" not in st.session_state:
    st.session_state.alert_history = []

cfg = load_config()

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.title("⚙️ Scanner Config")

    st.subheader("🔔 Alert Channels")
    cfg["desktop_alerts"] = st.toggle("Desktop Alerts", value=cfg.get("desktop_alerts", True))
    cfg["telegram_alerts"] = st.toggle("Telegram Alerts", value=cfg.get("telegram_alerts", False))

    if cfg["telegram_alerts"]:
        cfg["telegram_token"] = st.text_input("Bot Token", value=cfg.get("telegram_token", ""), type="password")
        cfg["telegram_chat_id"] = st.text_input("Chat ID", value=cfg.get("telegram_chat_id", ""))

    st.divider()
    st.subheader("⏱ Auto-Scan")
    cfg["auto_scan"] = st.toggle("Enable Auto-Scan", value=cfg.get("auto_scan", False))
    if cfg["auto_scan"]:
        cfg["scan_interval"] = st.slider("Interval (minutes)", 1, 30, cfg.get("scan_interval", 5))

    st.divider()
    st.subheader("🎛 Filter")
    cfg["min_price"] = st.number_input("Min Price (₹)", value=cfg.get("min_price", 100), step=50)
    cfg["min_volume_ratio"] = st.number_input("Min Vol Ratio (vs 20d avg)", value=cfg.get("min_volume_ratio", 1.5), step=0.1, format="%.1f")

    st.divider()
    if st.button("💾 Save Config"):
        save_config(cfg)
        st.success("Saved!")


# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════
col_title, col_time, col_scan = st.columns([4, 3, 2])
with col_title:
    st.title("📊 NSE FNO Scanner")
with col_time:
    if st.session_state.last_scan_time:
        st.metric("Last Scan", st.session_state.last_scan_time.strftime("%H:%M:%S"))
    else:
        st.metric("Last Scan", "—")
with col_scan:
    run_scan = st.button("🚀 Run Scan Now", type="primary", use_container_width=True)

st.divider()


# ══════════════════════════════════════════════════════════════════════════════
# SCANNER TABS
# ══════════════════════════════════════════════════════════════════════════════
tab_dashboard, tab_conditions, tab_results, tab_history, tab_setup = st.tabs(
    ["📈 Dashboard", "🔧 Conditions", "📋 Results", "📜 Alert History", "🛠 Setup Guide"]
)


# ── TAB: DASHBOARD ──────────────────────────────────────────────────────────
with tab_dashboard:
    results = st.session_state.scan_results

    if not results:
        st.info("Click **Run Scan Now** to start scanning FNO stocks.")
    else:
        df = pd.DataFrame(results)

        # Summary metrics
        bullish = df[df["signal"].str.contains("Bullish|Breakout|Volume Surge", case=False, na=False)]
        bearish = df[df["signal"].str.contains("Bearish|Breakdown", case=False, na=False)]
        total_hits = len(df)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("📍 Total Hits", total_hits)
        m2.metric("🟢 Bullish Signals", len(bullish))
        m3.metric("🔴 Bearish Signals", len(bearish))
        m4.metric("🔍 Scanned", df["symbol"].nunique() if "symbol" in df.columns else "—")

        st.divider()

        # Signal breakdown chart
        if "scanner" in df.columns:
            scanner_counts = df["scanner"].value_counts().reset_index()
            scanner_counts.columns = ["Scanner", "Count"]
            st.bar_chart(scanner_counts.set_index("Scanner"))

        # Live alerts table
        st.subheader("🚨 Active Signals")
        for _, row in df.iterrows():
            sig = row.get("signal", "")
            sym = row.get("symbol", "")
            price = row.get("ltp", "—")
            scanner = row.get("scanner", "")
            notes = row.get("notes", "")

            css_class = "alert-row-green" if "bull" in sig.lower() or "breakout" in sig.lower() else (
                "alert-row-red" if "bear" in sig.lower() or "breakdown" in sig.lower() else "alert-row-yellow"
            )
            badge_class = "badge-bull" if "bull" in sig.lower() else ("badge-bear" if "bear" in sig.lower() else "badge-neutral")

            st.markdown(
                f'<div class="{css_class}"><b>{sym}</b> &nbsp; ₹{price} &nbsp; '
                f'<span class="scanner-badge {badge_class}">{sig}</span> &nbsp; '
                f'<span style="color:#555;font-size:12px">{scanner} | {notes}</span></div>',
                unsafe_allow_html=True
            )


# ── TAB: CONDITIONS ──────────────────────────────────────────────────────────
with tab_conditions:
    st.subheader("🔧 Scanner Conditions")
    st.caption("Enable/disable built-in scanners or add your own manual condition below.")

    # Load existing conditions
    if "custom_conditions" not in st.session_state:
        st.session_state.custom_conditions = cfg.get("custom_conditions", [])

    # Built-in scanners
    st.markdown("**Built-in Scanners**")
    col_a, col_b = st.columns(2)
    with col_a:
        cfg["scan_52w_high"]       = st.checkbox("52-Week High Breakout",       value=cfg.get("scan_52w_high", True))
        cfg["scan_52w_low"]        = st.checkbox("52-Week Low Breakdown",        value=cfg.get("scan_52w_low", True))
        cfg["scan_volume_surge"]   = st.checkbox("Volume Surge (>2x 20D avg)",   value=cfg.get("scan_volume_surge", True))
        cfg["scan_price_breakout"] = st.checkbox("Price Breakout (Day High+)",   value=cfg.get("scan_price_breakout", True))
    with col_b:
        cfg["scan_rsi_ob"]         = st.checkbox("RSI Overbought (>70)",          value=cfg.get("scan_rsi_ob", True))
        cfg["scan_rsi_os"]         = st.checkbox("RSI Oversold (<30)",            value=cfg.get("scan_rsi_os", True))
        cfg["scan_macd_cross"]     = st.checkbox("MACD Bullish Crossover",        value=cfg.get("scan_macd_cross", True))
        cfg["scan_bb_squeeze"]     = st.checkbox("Bollinger Band Squeeze",        value=cfg.get("scan_bb_squeeze", False))

    st.divider()

    # Manual conditions builder
    st.markdown("**➕ Add Manual Condition**")
    st.caption("Define custom conditions using simple rules. Example: `RSI < 35 AND Volume > 1.5x AND Price > 200`")

    with st.expander("Add New Manual Scanner", expanded=False):
        cname = st.text_input("Condition Name", placeholder="e.g. Morning Momentum")
        cdesc = st.text_area(
            "Condition Logic (plain English / pseudo-code)",
            placeholder=(
                "Example:\n"
                "  Price above 20-day high\n"
                "  AND Volume > 2x 10-day average\n"
                "  AND RSI between 50 and 65\n"
                "  AND Close > Open (green candle)"
            ),
            height=120
        )
        # Condition builder dropdowns
        st.caption("Or use the condition builder:")
        cc1, cc2, cc3, cc4 = st.columns(4)
        with cc1:
            indicator = st.selectbox("Indicator", ["Price", "Volume", "RSI", "MACD", "Close-Open %", "High-Low %", "Volume/20D Avg"])
        with cc2:
            operator  = st.selectbox("Operator", [">", "<", ">=", "<=", "crosses above", "crosses below"])
        with cc3:
            threshold = st.number_input("Value", value=50.0, format="%.2f")
        with cc4:
            unit = st.selectbox("Unit", ["absolute", "% change", "x (multiplier)"])

        if st.button("➕ Add This Condition"):
            if cname:
                new_cond = {
                    "name": cname,
                    "description": cdesc,
                    "rule": f"{indicator} {operator} {threshold} {unit}",
                    "enabled": True,
                    "created": datetime.now().strftime("%Y-%m-%d %H:%M")
                }
                st.session_state.custom_conditions.append(new_cond)
                cfg["custom_conditions"] = st.session_state.custom_conditions
                save_config(cfg)
                st.success(f"Added: {cname}")
                st.rerun()

    # Show existing custom conditions
    if st.session_state.custom_conditions:
        st.markdown("**Your Custom Scanners**")
        for i, cond in enumerate(st.session_state.custom_conditions):
            c1, c2, c3 = st.columns([4, 1, 1])
            with c1:
                enabled = st.checkbox(
                    f"**{cond['name']}** — _{cond.get('rule','')}_",
                    value=cond.get("enabled", True),
                    key=f"cond_{i}"
                )
                st.session_state.custom_conditions[i]["enabled"] = enabled
            with c2:
                st.caption(cond.get("created", ""))
            with c3:
                if st.button("🗑 Delete", key=f"del_{i}"):
                    st.session_state.custom_conditions.pop(i)
                    cfg["custom_conditions"] = st.session_state.custom_conditions
                    save_config(cfg)
                    st.rerun()

    if st.button("💾 Save All Conditions", type="primary"):
        cfg["custom_conditions"] = st.session_state.custom_conditions
        save_config(cfg)
        st.success("Conditions saved!")


# ── TAB: RESULTS ─────────────────────────────────────────────────────────────
with tab_results:
    st.subheader("📋 Scan Results")
    if not st.session_state.scan_results:
        st.info("No scan results yet. Run a scan first.")
    else:
        df = pd.DataFrame(st.session_state.scan_results)
        # Filters
        fc1, fc2 = st.columns(2)
        with fc1:
            scanners = ["All"] + sorted(df["scanner"].unique().tolist()) if "scanner" in df.columns else ["All"]
            sel_scanner = st.selectbox("Filter by Scanner", scanners)
        with fc2:
            signals = ["All"] + sorted(df["signal"].unique().tolist()) if "signal" in df.columns else ["All"]
            sel_signal = st.selectbox("Filter by Signal", signals)

        filtered = df.copy()
        if sel_scanner != "All":
            filtered = filtered[filtered["scanner"] == sel_scanner]
        if sel_signal != "All":
            filtered = filtered[filtered["signal"] == sel_signal]

        st.dataframe(
            filtered.sort_values("ltp", ascending=False) if "ltp" in filtered.columns else filtered,
            use_container_width=True,
            hide_index=True
        )

        # Download
        csv = filtered.to_csv(index=False)
        st.download_button("⬇️ Download CSV", csv, "fno_scan_results.csv", "text/csv")


# ── TAB: ALERT HISTORY ───────────────────────────────────────────────────────
with tab_history:
    st.subheader("📜 Alert History")
    if not st.session_state.alert_history:
        st.info("No alerts fired yet.")
    else:
        hist_df = pd.DataFrame(st.session_state.alert_history)
        st.dataframe(hist_df.sort_values("time", ascending=False), use_container_width=True, hide_index=True)
        if st.button("🗑 Clear History"):
            st.session_state.alert_history = []
            st.rerun()


# ── TAB: SETUP GUIDE ─────────────────────────────────────────────────────────
with tab_setup:
    st.subheader("🛠 Setup Guide")
    st.markdown("""
### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Locally
```bash
streamlit run app.py
```

### 3. Telegram Alerts (Optional)
1. Message **@BotFather** on Telegram → create a new bot → copy the token
2. Message **@userinfobot** to get your Chat ID
3. Paste both in the sidebar under **Alert Channels**

### 4. Deploy to Streamlit Cloud (Free)
1. Push this folder to a **GitHub repo**
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repo → deploy `app.py`
4. Add Telegram token/chat ID in **Secrets** (Settings → Secrets)

### 5. Data Source
This scanner uses **`nsepython`** (unofficial NSE library — no API key needed).
- Data is pulled directly from NSE's public endpoints
- Works best during **market hours (9:15 AM – 3:30 PM IST)**
- Outside market hours returns previous day's closing data

### 6. Adding Custom Conditions
Go to the **Conditions** tab. You can:
- Enable/disable built-in scanners
- Write plain-English custom conditions
- Use the condition builder dropdowns

### ⚠️ Disclaimer
This tool is for **educational and informational purposes only**.
It is NOT financial advice. Always do your own research before trading.
    """)


# ══════════════════════════════════════════════════════════════════════════════
# SCAN TRIGGER
# ══════════════════════════════════════════════════════════════════════════════
if run_scan:
    with st.spinner("🔍 Fetching NSE data and running scans..."):
        try:
            results = run_all_scans(cfg)
            st.session_state.scan_results = results
            st.session_state.last_scan_time = datetime.now()

            # Fire alerts for new signals
            new_alerts = []
            for r in results:
                msg = f"📈 {r['symbol']} | {r['signal']} | ₹{r['ltp']} | {r['scanner']}"
                if cfg.get("desktop_alerts"):
                    send_desktop_alert(r["symbol"], r["signal"], r["ltp"])
                if cfg.get("telegram_alerts") and cfg.get("telegram_token") and cfg.get("telegram_chat_id"):
                    send_telegram_alert(cfg["telegram_token"], cfg["telegram_chat_id"], msg)
                new_alerts.append({
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "symbol": r["symbol"],
                    "signal": r["signal"],
                    "ltp": r["ltp"],
                    "scanner": r["scanner"]
                })

            st.session_state.alert_history = new_alerts + st.session_state.alert_history
            if results:
                st.success(f"✅ Scan complete — {len(results)} signal(s) found!")
            else:
                st.info("✅ Scan complete — no signals matched current conditions.")
        except Exception as e:
            st.error(f"❌ Scan error: {e}")
            st.exception(e)

# ── Auto-scan loop ────────────────────────────────────────────────────────────
if cfg.get("auto_scan") and cfg.get("scan_interval"):
    interval_sec = cfg["scan_interval"] * 60
    time.sleep(1)
    st.rerun()
