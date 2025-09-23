import os
import time
import requests
from supabase import create_client
from datetime import datetime

# 从 Railway 环境变量读取
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

# 初始化 Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_latest_signals():
    # 先取最近 1 条测试
    res = supabase.table("signals").select("*").order("created_at", desc=True).limit(1).execute()
    return res.data

def send_to_channel(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHANNEL_ID, "text": text})

def run():
    signals = get_latest_signals()
    for sig in signals:
        msg = f"""
🔥 New Signal
Pair: {sig.get('symbol')}
Direction: {sig.get('direction')}
Entry: {sig.get('entry')} | TP: {sig.get('tp')} | SL: {sig.get('sl')}
📊 Win Rate: {sig.get('win_rate', 'N/A')}%
"""
        send_to_channel(msg)

if __name__ == "__main__":
    send_to_channel("✅ Bot connected successfully! Test message.")
    while True:
        run()
        time.sleep(60)  # 每分钟检查一次
