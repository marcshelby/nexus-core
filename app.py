import streamlit as st
import requests
import yfinance as yf
import pandas as pd
import asyncio
import threading
from datetime import datetime
import time

# --- KONFIGURASI DASHBOARD ---
st.set_page_config(page_title="Nexus Core | V11 Sniper Radar", page_icon="🎯", layout="wide")
st.title("🛰️ NEXUS CORE: V11 Sniper Momentum Radar")
st.markdown("---")

# --- AMBIL AMUNISI RAHASIA ---
try:
    TOKEN = st.secrets["DISCORD_TOKEN"]
    CHANNEL_ID = st.secrets["CHANNEL_ID"]
except KeyError:
    st.error("🚨 KODE MERAH: Token/Channel ID belum ditanam di Streamlit Secrets!")
    st.stop()

# --- PENGATURAN MESIN AGEN & DAFTAR ASET ---
RADAR_MAP = {
    "BTCUSD": "BTC-USD",
    "ETHUSD": "ETH-USD",
    "SOLUSD": "SOL-USD",
    "XRPUSD": "XRP-USD",
    "NASDAQ": "NQ=F",
    "USOIL": "CL=F",
    "GOLD": "GC=F",
    "SILVER": "SI=F",
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X"
}

HTF_INTERVAL = "4h"  # Bias Arah
LTF_INTERVAL = "5m"  # Sniper Entry (Diturunkan ke M5)
LOOKBACK = 400
last_alerts = {}

# --- FUNGSI KOMUNIKASI KE MARKAS (DISCORD) ---
def send_discord_alert(setup_type, symbol, entry, sl, tp, trigger_time, bias):
    url = f"https://discord.com/api/v10/channels/{CHANNEL_ID}/messages"
    headers = {"Authorization": f"Bot {TOKEN}", "Content-Type": "application/json"}
    
    warna = "🟢" if "LONG" in setup_type else "🔴"
    pesan = (
        f"🚨 **NEXUS V11 EKSEKUSI MOMENTUM: {setup_type}!** 🚨\n\n"
        f"**Aset:** {symbol}\n"
        f"**HTF Bias (H4):** {bias}\n"
        f"**Setup LTF (M5):** {warna} {setup_type}\n"
        f"**Entry Point:** {entry:.5f} *(Breakout dari Candle Retest)*\n"
        f"**Stop Loss:** {sl:.5f}\n"
        f"**Take Profit:** {tp:.5f}\n"
        f"**Sinyal Terkonfirmasi:** {trigger_time}\n"
        f"**Status AI:** Sikat! Momentum bandar sudah terdeteksi."
    )
    requests.post(url, headers=headers, json={"content": pesan})

# --- MESIN PENARIK DATA ---
async def fetch_data(ticker, interval, period):
    df = yf.download(ticker, period=period, interval=interval, progress=False)
    return df

# --- OTAK MTFA V11 (MOMENTUM SHIFT ENTRY) ---
async def run_radar():
    while True:
        current_clock = datetime.now().strftime('%H:%M:%S')
        print(f"🛰️ [{current_clock}] Nexus V11 menyapu market (HTF: {HTF_INTERVAL} | LTF: {LTF_INTERVAL})...")
        
        for mt5_symbol, yf_ticker in RADAR_MAP.items():
            try:
                # 1. TARIK DATA HTF (UNTUK BIAS)
                htf_df = await fetch_data(yf_ticker, HTF_INTERVAL, "1mo")
                if htf_df.empty or len(htf_df) < 100:
                    continue
                
                htf_df.rename(columns={"High":"high", "Low":"low"}, inplace=True)
                old_h_high = htf_df['high'].iloc[-100:-50].max()
                old_h_low = htf_df['low'].iloc[-100:-50].min()
                rec_h_high = htf_df['high'].iloc[-50:].max()
                rec_h_low = htf_df['low'].iloc[-50:].min()
                
                bias = "NEUTRAL"
                if rec_h_high > old_h_high and rec_h_low > old_h_low:
                    bias = "BULLISH"
                elif rec_h_high < old_h_high and rec_h_low < old_h_low:
                    bias = "BEARISH"

                if bias == "NEUTRAL":
                    continue
                
                # 2. TARIK DATA LTF M5 (UNTUK ENTRY MOMENTUM)
                ltf_df = await fetch_data(yf_ticker, LTF_INTERVAL, "5d")
                if ltf_df.empty or len(ltf_df) < LOOKBACK:
                    continue
                
                df = ltf_df.tail(LOOKBACK).copy()
                df.rename(columns={"Open":"open", "High":"high", "Low":"low", "Close":"close"}, inplace=True)
                df['time_str'] = df.index.astype(str)
                df['is_green'] = df['close'] > df['open']
                
                current_price = float(df['close'].iloc[-1])
                touch_tolerance = current_price * 0.0005 
                
                setup_found = None
                
                for i in range(50, len(df) - 3):
                    c1, c2, c3, c4 = df.iloc[i-4], df.iloc[i-3], df.iloc[i-2], df.iloc[i-1]
                    
                    # ==========================================
                    # 🔴 SETUP SHORT (BIAS HTF BEARISH)
                    # ==========================================
                    if bias == "BEARISH":
                        if (not c1['is_green']) and (not c2['is_green']) and (c3['is_green']) and (c4['is_green']):
                            if (c2['low'] < c1['low']) and (c3['high'] > c2['high']) and (c4['high'] > c3['high']):
                                support = float(c2['low'])
                                break_candle = df.iloc[i]
                                
                                # Breakout Support
                                if (not break_candle['is_green']) and (break_candle['close'] < support):
                                    retest_candle = df.iloc[i+1] # Candle Hijau yang nyentuh area
                                    trigger_candle = df.iloc[i+2] # Candle Merah yang jebol low si Hijau
                                    
                                    if retest_candle['is_green'] and (not trigger_candle['is_green']):
                                        # Sentuhan presisi ke RBS
                                        if (support - touch_tolerance) <= retest_candle['high'] <= (support + touch_tolerance):
                                            # ENTRY MOMENTUM: Candle merah menutup/melewati titik Low candle retest
                                            if trigger_candle['close'] < retest_candle['low']:
                                                entry = float(retest_candle['low']) # Persis di garis Breakout
                                                sl = max(float(retest_candle['high']), support) + (support * 0.0002) # SL di atas RBS
                                                tp = entry - (sl - entry) * 1.5
                                                setup_found = {"type": "SHORT (RBS-Momentum)", "entry": entry, "sl": sl, "tp": tp, "time": str(trigger_candle['time_str'])}

                    # ==========================================
                    # 🟢 SETUP LONG (BIAS HTF BULLISH)
                    # ==========================================
                    elif bias == "BULLISH":
                        if (c1['is_green']) and (c2['is_green']) and (not c3['is_green']) and (not c4['is_green']):
                            if (c2['high'] > c1['high']) and (c3['low'] < c2['low']) and (c4['low'] < c3['low']):
                                resistance = float(c2['high'])
                                break_candle = df.iloc[i]
                                
                                # Breakout Resistance
                                if (break_candle['is_green']) and (break_candle['close'] > resistance):
                                    retest_candle = df.iloc[i+1] # Candle Merah yang nyentuh area
                                    trigger_candle = df.iloc[i+2] # Candle Hijau yang jebol high si Merah
                                    
                                    if (not retest_candle['is_green']) and trigger_candle['is_green']:
                                        # Sentuhan presisi ke SBR
                                        if (resistance - touch_tolerance) <= retest_candle['low'] <= (resistance + touch_tolerance):
                                            # ENTRY MOMENTUM: Candle hijau menutup/melewati titik High candle retest
                                            if trigger_candle['close'] > retest_candle['high']:
                                                entry = float(retest_candle['high']) # Persis di garis Breakout
                                                sl = min(float(retest_candle['low']), resistance) - (resistance * 0.0002) # SL di bawah SBR
                                                tp = entry + (entry - sl) * 1.5
                                                setup_found = {"type": "LONG (SBR-Momentum)", "entry": entry, "sl": sl, "tp": tp, "time": str(trigger_candle['time_str'])}

                if setup_found and last_alerts.get(mt5_symbol) != setup_found["time"]:
                    last_alerts[mt5_symbol] = setup_found["time"]
                    send_discord_alert(setup_found["type"], mt5_symbol, setup_found["entry"], setup_found["sl"], setup_found["tp"], setup_found["time"], bias)
                
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"Error pada {mt5_symbol}: {e}")
        
        # Istirahat 5 menit sesuai interval M5
        await asyncio.sleep(300) 

# --- BYPASS: JALANKAN AGEN DI LATAR BELAKANG ---
def start_agent_in_background():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_radar())

if "agent_active" not in st.session_state:
    st.session_state.agent_active = True
    agent_thread = threading.Thread(target=start_agent_in_background, daemon=True)
    agent_thread.start()

# --- TAMPILAN WEB (DASHBOARD) ---
st.success(f"🤖 Sistem Sniper V11 Aktif! Memantau {len(RADAR_MAP)} Aset.")
st.info(f"Bias Arah: {HTF_INTERVAL} | Eksekusi Momentum: {LTF_INTERVAL}")
st.write("Daftar Aset Tempur: " + ", ".join(RADAR_MAP.keys()))
st.write("Logika Entry: Breakout dari batas High/Low Candle Retest (Sesuai SOP Visual Terbaru).")

if st.button("Panggil Agen untuk Laporan Manual"):
    st.write("Menyapu market M5...")
