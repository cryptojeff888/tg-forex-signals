import os
import time
import requests
from supabase import create_client
from datetime import datetime

# 从 Railway 环境变量读取
SUPABASE_URL = os.getenv("SUPABASE_URL")         # 旧库（signals）
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_USER_URL = os.getenv("SUPABASE_USER_URL")  # 新库（用户）
SUPABASE_USER_KEY = os.getenv("SUPABASE_USER_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

# 初始化 Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)              # 旧的 → 读 signals
user_db = create_client(SUPABASE_USER_URL, SUPABASE_USER_KEY)     # 新的 → 写用户

# 记录上一次发送过的信号 ID
last_sent_id = None

def get_latest_signal():
    """获取 signals_with_rates 表中最新 1 条信号"""
    res = (
        supabase.table("signals_with_rates")
        .select("id, symbol, direction, entry, tp, sl, group_win_rate_calc")
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

        # 先从 signal 里取出 direction
        direction = sig.get("direction", "")
        if direction:
            d = direction.lower()
            if "buy_limit" in d:
                direction_display = "*Direction:* BUY LIMIT 📈"
            elif "sell_limit" in d:
                direction_display = "*Direction:* SELL LIMIT 📉"
            elif "buy_stop" in d:
                direction_display = "*Direction:* BUY STOP 📈"
            elif "sell_stop" in d:
                direction_display = "*Direction:* SELL STOP 📉"
            elif d == "buy":
                direction_display = "*Direction:* BUY 📈"
            elif d == "sell":
                direction_display = "*Direction:* SELL 📉"
            else:
                direction_display = f"*Direction:* {direction.replace('_', ' ').upper()}"
        else:
            direction_display = "*Direction:* N/A"
        msg = f"""
🔥 *New Signal* 🔥

💹 *Pair:* {sig.get('symbol')}
📍 {direction_display}
🎯 *Entry:* {sig.get('entry')}
✔️ *TP:* {sig.get('tp')}
🛑 *SL:* {sig.get('sl')}

🏆 *Win Rate:* {sig.get('group_win_rate_calc', 'N/A')}% 
"""
        send_to_channel(msg)

if __name__ == "__main__":
    while True:
        run()
        time.sleep(60)

