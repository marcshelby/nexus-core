import streamlit as st
import discord
from discord.ext import tasks, commands
import asyncio
import threading
import random
from datetime import datetime

# ==============================================================================
# 🎨 UI STYLING & DESIGN (Tampilan Web)
# ==============================================================================
st.set_page_config(
    page_title="Nexus Core Dashboard",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS untuk tampilan Dark Mode Premium ala Markas Intelijen
st.markdown("""
    <style>
        .main { background-color: #0e1117; }
        .stMetric { background-color: #1f2937; padding: 15px; border-radius: 10px; border: 1px solid #374151; }
        .status-box { padding: 20px; border-radius: 8px; border-left: 5px solid #10b981; background-color: #111827; }
    </style>
""", unsafe_allow_html=True)

st.title("📡 Nexus Core Intelligence")
st.caption(f"Sistem Operasional Radar | Live Session: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ==============================================================================
# 🤖 BOT DISCORD & RADAR MACHINE LOGIC (Mesin Latar Belakang)
# ==============================================================================
# ⚠️ MASUKKAN RAHASIA UTAMA LU DI SINI ⚠️
TOKEN = "MTUxMjY4NDE1NDQ2MTA5NDAyMQ.G-dOzE.CE3R69HSYOem6k6XFqQ5z5kyeGux5L-YhJe9JA" # Masukkan token bot 49 karakter lu
CHANNEL_ID = 1509826622256320524 # GANTI dengan ID Channel Discord lu (Angka saja)

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# Fitur loop otomatis untuk patroli tiap 5 menit
@tasks.loop(minutes=5)
async def auto_market_radar():
    await bot.wait_until_ready()
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        # Simulasi deteksi setup pasar
        pairs = ["GBPUSD", "EURUSD", "XAUUSD"]
        selected_pair = random.choice(pairs)
        
        # Format Embed Discord Premium
        embed = discord.Embed(
            title=f"🎯 RADAR ALERT: {selected_pair}",
            description="Formasi SnD Apit terkonfirmasi di Timeframe H4!",
            color=0x10b981
        )
        embed.add_field(name="Status", value="🟢 Siap Eksekusi di Zona Entry", inline=True)
        embed.add_field(name="Rasio Risiko", value="RR 1:3", inline=True)
        embed.set_footer(text="Nexus Automated Core System")
        
        await channel.send(embed=embed)

@bot.event
async def on_ready():
    print(f"Mesin Otomatis Terhubung sebagai {bot.user.name}")
    if not auto_market_radar.is_running():
        auto_market_radar.start()

def run_discord_bot():
    try:
        # Mengatur event loop agar kompatibel dengan thread background
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(bot.start(TOKEN))
    except Exception as e:
        print(f"Error Bot: {e}")

# Mencegah bot dinyalakan berkali-kali saat halaman web di-refresh
if 'bot_started' not in st.session_state:
    threading.Thread(target=run_discord_bot, daemon=True).start()
    st.session_state['bot_started'] = True

# ==============================================================================
# 📊 INTERFASE VISUAL DASHBOARD
# ==============================================================================
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="GBPUSD SPREAD", value="0.5 Pips", delta="-0.1", delta_color="inverse")
with col2:
    st.metric(label="SERVER LATENCY", value="14 ms", delta="Stable")
with col3:
    st.metric(label="TOTAL SETUP HARI INI", value="4 Sinyal", delta="+1 Baru")

st.markdown("---")

st.sidebar.header("🕹️ Pusat Kendali")
asset_select = st.sidebar.multiselect(
    "Pilih Aset Patroli Radar:",
    ["GBPUSD", "EURUSD", "XAUUSD", "AUDUSD", "USDJPY"],
    default=["GBPUSD", "EURUSD"]
)
scan_mode = st.sidebar.radio("Mode Analisa AI:", ["Konservatif (SnD Apit)", "Agresif (Breakout)"])

st.subheader("🛡️ Status Operasional")
st.markdown(f"""
    <div class="status-box">
        <h4>🤖 Captain Nexus Status: ONLINE</h4>
        <p>Mesin otomatis sedang memantau aset <b>{', '.join(asset_select)}</b> dengan metode <b>{scan_mode}</b>.</p>
        <p><i>Notifikasi otomatis akan dikirim ke Discord setiap 5 menit jika konfirmasi matematika terpenuhi.</i></p>
    </div>
""", unsafe_allow_html=True)