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

# 记录上一次发送过的信号 ID
last_sent_id = None

def get_latest_signal():
    """获取 signals_with_rates 表中最新 1 条信号"""
    res = (
        supabase.table("signals_with_rates")
        .select("id, symbol, direction, entry, tp, sl, group_win_rate")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    return res.data

def send_to_channel(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": CHANNEL_ID,
        "text": text,
        "parse_mode": "Markdown"   # ✅ 让 **加粗** 生效
    })

def run():
    """检查并发送新信号"""
    global last_sent_id
    signals = get_latest_signal()
    for sig in signals:
        sig_id = sig.get("id")
        if sig_id == last_sent_id:
            continue  # 已经发过，跳过

        # 更新为最新 ID
        last_sent_id = sig_id  
                        
        # 根据方向加上 emoji
        direction = sig.get('direction', '')
        if direction and "buy" in direction.lower():
            direction_display = f"*Direction:* BUY 📈"
        elif direction and "sell" in direction.lower():
            direction_display = f"*Direction:* SELL 📉"
        else:
            direction_display = f"*Direction:* {direction}"

        msg = f"""
🔥 *New Signal*

*Pair:* {sig.get('symbol')}
{direction_display}
*Entry:* {sig.get('entry')}
*TP:* {sig.get('tp')}
*SL:* {sig.get('sl')}
*Win Rate:* {sig.get('group_win_rate_calc', 'N/A')}%
"""
        send_to_channel(msg)

if __name__ == "__main__":
    send_to_channel("🔄 Bot restarted, now monitoring signals...")
    while True:
        run()
        time.sleep(60)  # 每分钟检查一次
