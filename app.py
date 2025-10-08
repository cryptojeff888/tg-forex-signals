import os
import time
import threading
import requests
import stripe
from datetime import datetime
from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client

# === 初始化 FastAPI ===
app = FastAPI()

# === 引入 Stripe & PayPal webhook 函数 ===
from stripe_webhook import stripe_webhook
from paypal_webhook import app as paypal_app  # PayPal 保持原状

# ✅ 注册 Stripe webhook 路由（用函数版本）
app.post("/stripe-webhook")(stripe_webhook)

# ✅ 合并 PayPal 路由进主 app（这段保留）
for route in paypal_app.routes:
    app.router.routes.append(route)

# === CORS 设置（先放开所有域，测试用）===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # 生产环境最好改成 https://tradingvault.base44.app
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Stripe 初始化 ===
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# === Supabase 初始化 ===
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_USER_URL = os.getenv("SUPABASE_USER_URL")
SUPABASE_USER_KEY = os.getenv("SUPABASE_USER_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)              # 旧的 → 读 signals
user_db = create_client(SUPABASE_USER_URL, SUPABASE_USER_KEY)     # 新的 → 写用户

# === Worker 用到的变量 ===
last_sent_id = None


# === Worker 函数 ===
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
        "parse_mode": "Markdown"
    })


def worker_loop():
    global last_sent_id
    while True:
        try:
            signals = get_latest_signal()
            for sig in signals:
                sig_id = sig.get("id")
                if sig_id == last_sent_id:
                    continue  # 已经发过，跳过

                # 格式化 direction
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

                # ✅ 发完之后更新 last_sent_id
                last_sent_id = sig_id

        except Exception as e:
            print(f"Worker error: {e}")

        time.sleep(60)


# === 在 FastAPI 启动时，开一个后台线程跑 worker ===
@app.on_event("startup")
def start_worker():
    thread = threading.Thread(target=worker_loop, daemon=True)
    thread.start()


# === Stripe Checkout Session 创建接口 ===
@app.post("/create-checkout-session")
async def create_checkout_session(
    plan: str = Body("trial", embed=True),
    email: str = Body(..., embed=True),
    tg_username: str = Body(..., embed=True)
):
    # Stripe Price IDs
    price_map = {
        "monthly": "price_1SD6H1EqeYLgpt07bVN9S6xP",    # $29.90 / month
        "lifetime": "price_1SD6JvEqeYLgpt079qicqkx4",   # $299 one-time
    }

    try:
        if plan == "trial":
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                mode="subscription",
                line_items=[
                    {
                        "price_data": {
                            "currency": "usd",
                            "unit_amount": 1290,   # upfront $12.90
                            "product_data": {
                                "name": "TradingVault 7-day Trial Fee"
                            },
                        },
                        "quantity": 1,
                    },
                    {
                        "price": price_map["monthly"],  # $29.90 / month
                        "quantity": 1,
                    }
                ],
                metadata={
                    "email": email,
                    "tg_username": tg_username
                },  # ✅ 将两者一起写入 metadata
                subscription_data={"trial_period_days": 7},
                success_url="https://tradingvault.base44.app/?status=success",
                cancel_url="https://tradingvault.base44.app/?status=cancel",
            )

        elif plan == "lifetime":
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                mode="payment",
                line_items=[{
                    "price": price_map["lifetime"],
                    "quantity": 1,
                }],
                metadata={
                    "email": email,
                    "tg_username": tg_username
                },  # ✅ 同样写入 metadata
                success_url="https://tradingvault.base44.app/?status=success",
                cancel_url="https://tradingvault.base44.app/?status=cancel",
            )

        else:
            return {"error": f"Invalid plan: {plan}"}

        return {"url": checkout_session.url}

    except Exception as e:
        return {"error": str(e)}
