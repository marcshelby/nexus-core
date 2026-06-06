import streamlit as st
import requests
import yfinance as yf
import pandas as pd
import asyncio
import threading
from datetime import datetime

# --- KONFIGURASI DASHBOARD ---
st.set_page_config(page_title="Nexus Core | V13 Pure M5", page_icon="🎯", layout="wide")
st.title("🛰️ NEXUS CORE: V13 Pure M5 Sniper")
st.markdown("---")

# --- AMBIL AMUNISI RAHASIA ---
try:
    TOKEN = st.secrets["DISCORD_TOKEN"]
    CHANNEL_ID = st.secrets["CHANNEL_ID"]
except KeyError:
    st.error("🚨 KODE MERAH: Token/Channel ID belum ditanam di Streamlit Secrets!")
    st.stop()

# --- DAFTAR ASET TEMPUR ---
RADAR_MAP = {
    "BTCUSD": "BTC-USD", "ETHUSD": "ETH-USD", "SOLUSD": "SOL-USD", "XRPUSD": "XRP-USD",
    "NASDAQ": "NQ=F", "USOIL": "CL=F", "GOLD": "GC=F", "SILVER": "SI=F",
    "EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X"
}

LTF_INTERVAL = "5m"  
LOOKBACK = 300
if "last_alerts" not in st.session_state:
    st.session_state.last_alerts = {}

# --- FUNGSI KOMUNIKASI KE MARKAS (DISCORD) ---
def send_discord_alert(setup_type, symbol, entry, sl, tp, trigger_time):
    url = f"https://discord.com/api/v10/channels/{CHANNEL_ID}/messages"
    headers = {"Authorization": f"Bot {TOKEN}", "Content-Type": "application/json"}
    
    warna = "🟢" if "LONG" in setup_type else "🔴"
    pesan = (
        f"🚨 **NEXUS V13 M5 SNIPER: {setup_type}!** 🚨\n\n"
        f"**Aset:** {symbol}\n"
        f"**Setup (M5):** {warna} {setup_type}\n"
        f"**Entry Point:** {entry:.5f} *(Breakout Momentum)*\n"
        f"**Stop Loss:** {sl:.5f}\n"
        f"**Take Profit:** {tp:.5f}\n"
        f"**Waktu Sinyal:** {trigger_time}\n"
        f"**Status AI:** Pure M5 Price Action. Sikat!"
    )
    requests.post(url, headers=headers, json={"content": pesan})

# --- MESIN PENARIK DATA ---
async def fetch_data(ticker, interval, period):
    df = yf.download(ticker, period=period, interval=interval, progress=False)
    return df

# --- OTAK V13 (PURE M5 FVG + APIT MOMENTUM) ---
async def run_radar():
    while True:
        current_clock = datetime.now().strftime('%H:%M:%S')
        print(f"🛰️ [{current_clock}] Nexus V13 menyapu M5 murni...")
        
        for mt5_symbol, yf_ticker in RADAR_MAP.items():
            try:
                df = await fetch_data(yf_ticker, LTF_INTERVAL, "5d")
                if df.empty or len(df) < LOOKBACK:
                    continue
                
                df = df.tail(LOOKBACK).copy()
                df.rename(columns={"Open":"open", "High":"high", "Low":"low", "Close":"close"}, inplace=True)
                df['time_str'] = df.index.astype(str)
                df['is_green'] = df['close'] > df['open']
                
                current_price = float(df['close'].iloc[-1])
                touch_tolerance = current_price * 0.0005 
                
                setup_found = None
                
                for i in range(10, len(df) - 3):
                    c1, c2, c3, c4 = df.iloc[i-4], df.iloc[i-3], df.iloc[i-2], df.iloc[i-1]
                    
                    # ==========================================
                    # 🔴 SETUP SHORT (BREAKOUT SUPPORT M5)
                    # ==========================================
                    if (not c1['is_green']) and (not c2['is_green']) and (c3['is_green']) and (c4['is_green']):
                        if (c2['low'] < c1['low']) and (c3['high'] > c2['high']) and (c4['high'] > c3['high']):
                            support = float(c2['low'])
                            break_candle = df.iloc[i]
                            
                            if (not break_candle['is_green']) and (break_candle['close'] < support):
                                retest_candle = df.iloc[i+1] # Apit Hijau
                                trigger_candle = df.iloc[i+2] # Momentum Merah
                                
                                if retest_candle['is_green'] and (not trigger_candle['is_green']):
                                    # Presisi ke RBS
                                    if (support - touch_tolerance) <= retest_candle['high'] <= (support + touch_tolerance):
                                        # Entry Momentum jebol low
                                        if trigger_candle['close'] < retest_candle['low']:
                                            entry = float(retest_candle['low']) 
                                            sl = max(float(retest_candle['high']), support) + (support * 0.0002) 
                                            tp = entry - (sl - entry) * 1.5
                                            setup_found = {"type": "SHORT (RBS)", "entry": entry, "sl": sl, "tp": tp, "time": str(trigger_candle['time_str'])}

                    # ==========================================
                    # 🟢 SETUP LONG (BREAKOUT RESISTANCE M5)
                    # ==========================================
                    if (c1['is_green']) and (c2['is_green']) and (not c3['is_green']) and (not c4['is_green']):
                        if (c2['high'] > c1['high']) and (c3['low'] < c2['low']) and (c4['low'] < c3['low']):
                            resistance = float(c2['high'])
                            break_candle = df.iloc[i]
                            
                            if (break_candle['is_green']) and (break_candle['close'] > resistance):
                                retest_candle = df.iloc[i+1] # Apit Merah
                                trigger_candle = df.iloc[i+2] # Momentum Hijau
                                
                                if (not retest_candle['is_green']) and trigger_candle['is_green']:
                                    # Presisi ke SBR
                                    if (resistance - touch_tolerance) <= retest_candle['low'] <= (resistance + touch_tolerance):
                                        # Entry Momentum jebol high
                                        if trigger_candle['close'] > retest_candle['high']:
                                            entry = float(retest_candle['high']) 
                                            sl = min(float(retest_candle['low']), resistance) - (resistance * 0.0002) 
                                            tp = entry + (entry - sl) * 1.5
                                            setup_found = {"type": "LONG (SBR)", "entry": entry, "sl": sl, "tp": tp, "time": str(trigger_candle['time_str'])}

                if setup_found:
                    alert_key = f"{mt5_symbol}_{setup_found['time']}"
                    if st.session_state.last_alerts.get(mt5_symbol) != alert_key:
                        st.session_state.last_alerts[mt5_symbol] = alert_key
                        send_discord_alert(setup_found["type"], mt5_symbol, setup_found["entry"], setup_found["sl"], setup_found["tp"], setup_found["time"])
                
                await asyncio.sleep(2)
                
            except Exception as e:
                pass
        
        await asyncio.sleep(300) 

# --- BYPASS ---
def start_agent_in_background():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_radar())

if "agent_active" not in st.session_state:
    st.session_state.agent_active = True
    agent_thread = threading.Thread(target=start_agent_in_background, daemon=True)
    agent_thread.start()

# --- TAMPILAN WEB ---
st.success(f"🤖 V13 Pure M5 Sniper Aktif! Memantau {len(RADAR_MAP)} Aset.")
st.info("Logika: 100% Price Action M5. Bebas dari belenggu bias H4. Fokus eksekusi Momentum!")
