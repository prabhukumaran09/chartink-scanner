# 📈 NSE FNO Scanner

A free, open-source stock scanner for NSE Futures & Options stocks — built with Python + Streamlit.
Replacement for Chartink with desktop alerts, Telegram alerts, and a live dashboard.

---

## ✅ Features

| Feature | Details |
|---|---|
| 🔍 Stock Universe | All ~180 NSE FNO stocks |
| 📡 Data Source | `nsepython` (free, no API key) |
| 🖥 Dashboard | Streamlit web UI (runs locally or on cloud) |
| 🔔 Desktop Alerts | Windows / macOS / Linux via `plyer` |
| 📲 Telegram Alerts | Via Telegram Bot API |
| 🎛 Custom Conditions | Add your own scanner rules in the UI |
| ☁️ Free Hosting | GitHub + Streamlit Community Cloud |

---

## 🚀 Quick Start (Local)

### Step 1 — Clone or download the project

```bash
git clone https://github.com/YOUR_USERNAME/fno-scanner.git
cd fno-scanner
```

Or just download and unzip the folder.

### Step 2 — Create a Python virtual environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

> ⚠️ If `nsepython` fails to install, try:
> ```bash
> pip install nsepython --upgrade
> ```

### Step 4 — Run the app

```bash
streamlit run app.py
```

The dashboard opens automatically at `http://localhost:8501`

### Step 5 — Run your first scan

1. Click **Run Scan Now** (top right of the dashboard)
2. Results appear under the **Dashboard** and **Results** tabs
3. Signals with 🟢 are bullish, 🔴 are bearish

---

## 🔔 Setting Up Telegram Alerts

### Step 1 — Create a Telegram Bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot`
3. Follow the prompts — choose a name like `MyFNOScanner`
4. Copy the **Bot Token** (looks like `123456789:ABCdef...`)

### Step 2 — Get your Chat ID

1. Search for **@userinfobot** on Telegram
2. Send `/start`
3. Copy the **Id** field (a number like `987654321`)

### Step 3 — Enter in the app

- In the sidebar, toggle **Telegram Alerts ON**
- Paste your Bot Token and Chat ID
- Click **Save Config**

### Step 4 — Test

Run a scan. If signals are found, you'll receive a Telegram message like:

```
📊 NSE FNO Scanner Alert

🟢 RELIANCE | ₹2950.50 | 52W High Breakout
   ↳ LTP ₹2950.50 near 52W High ₹2955.00

🔴 IDEA | ₹13.20 | 52W Low Breakdown
   ↳ LTP near 52W Low ₹13.00
```

---

## ☁️ Free Cloud Deployment (Streamlit Community Cloud)

### Step 1 — Push to GitHub

```bash
git init
git add .
git commit -m "Initial FNO scanner"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/fno-scanner.git
git push -u origin main
```

> Make sure `.gitignore` is in place — it excludes `config.json` and `secrets.toml`

### Step 2 — Deploy on Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with GitHub
3. Click **New app**
4. Select your repo → branch: `main` → file: `app.py`
5. Click **Deploy**

The app gets a public URL like `https://your-app.streamlit.app`

### Step 3 — Add Telegram secrets on Cloud

1. In Streamlit Cloud dashboard → your app → **Settings → Secrets**
2. Paste:
```toml
[telegram]
token   = "YOUR_BOT_TOKEN"
chat_id = "YOUR_CHAT_ID"
```
3. Click **Save** — app restarts automatically

> ℹ️ On Streamlit Cloud, desktop notifications won't work (no desktop).
> Use Telegram alerts for cloud deployments.

---

## 🎛 Adding Custom Scan Conditions

Go to the **Conditions** tab in the app:

1. Click **Add New Manual Scanner**
2. Give it a name (e.g. "Morning Gap Up")
3. Use the condition builder dropdowns:
   - Indicator: `Price`, `Volume`, `RSI`, `Volume/20D Avg`, etc.
   - Operator: `>`, `<`, `>=`, `crosses above`, etc.
   - Value: your threshold number
4. Click **Add This Condition**
5. Click **Save All Conditions**

### Example Custom Conditions

| Name | Rule |
|---|---|
| Gap Up Open | `Price > 2.0 % change` (open vs prev close) |
| Heavy Volume | `Volume/20D Avg > 3.0 x` |
| Oversold RSI | `RSI < 30 absolute` |
| Near Day High | `High-Low % < 1.0 %` |

---

## 📁 Project Structure

```
fno-scanner/
├── app.py                  ← Streamlit dashboard (main entry point)
├── config.py               ← Config loader/saver
├── requirements.txt        ← Python dependencies
├── .gitignore
├── .streamlit/
│   ├── config.toml         ← Theme and server settings
│   └── secrets.toml        ← Telegram credentials (NOT committed to git)
├── scanner/
│   ├── __init__.py
│   ├── engine.py           ← Core scan engine
│   ├── fno_list.py         ← List of all FNO stocks
│   └── indicators.py       ← RSI, MACD, Bollinger Band calculations
└── alerts/
    ├── __init__.py
    ├── telegram_alert.py   ← Telegram Bot API integration
    └── desktop_alert.py    ← Cross-platform desktop notifications
```

---

## ⚙️ Built-in Scanners

| Scanner | Condition |
|---|---|
| 52W High Breakout | LTP within 0.5% of 52-week high |
| 52W Low Breakdown | LTP within 0.5% of 52-week low |
| Volume Surge | Today's volume > 2× 20-day average |
| Intraday High Breakout | LTP = day high (bullish momentum) |
| RSI Overbought | RSI proxy > 70 |
| RSI Oversold | RSI proxy < 30 |
| Strong Momentum | Price change > +2.5% on day |

---

## ⚠️ Disclaimer

This tool is for **educational and informational purposes only** and does not constitute financial advice. Always do your own research before making trading decisions. The author is not responsible for any financial losses.

---

## 🔄 Updating the FNO Stock List

NSE updates the FNO segment periodically. To update the stock list:

1. Visit: https://www.nseindia.com/products-services/equity-derivatives-list-underlyings-information
2. Download the list of F&O securities
3. Update the `FNO_STOCKS` list in `scanner/fno_list.py`
