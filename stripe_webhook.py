import os
import json
import stripe
from fastapi import FastAPI, Request
from supabase import create_client
from datetime import datetime, timedelta

# === Railway 环境变量 ===
SUPABASE_USER_URL = os.getenv("SUPABASE_USER_URL")
SUPABASE_USER_KEY = os.getenv("SUPABASE_USER_KEY")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")  # 你的 Stripe live secret key
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")  # Webhook signing secret

# === 初始化 Supabase & Stripe ===
supabase = create_client(SUPABASE_USER_URL, SUPABASE_USER_KEY)
stripe.api_key = STRIPE_SECRET_KEY

# ✅ 改成纯函数，不再创建 FastAPI 实例
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except Exception as e:
        print("❌ Webhook 验证失败:", e)
        return {"status": "invalid"}

    event_type = event["type"]
    data = event["data"]["object"]

    print("🔔 收到 Stripe Webhook:", event_type)

    # === 获取 metadata ===
    metadata = data.get("metadata", {}) or {}
    email = metadata.get("email")
    tg_username = metadata.get("tg_username")

    # === 结账完成（12.90 Trial）===
    if event_type == "checkout.session.completed":
        expire_at = (datetime.utcnow() + timedelta(days=7)).isoformat()

        supabase.table("subscribers").upsert({
            "email": email,
            "tg_username": tg_username or "unknown",
            "plan": "trial",
            "created_at": datetime.utcnow().isoformat(),
            "expired_at": expire_at,
            "status": "active"
        }, on_conflict="email").execute()

        print(f"✅ Stripe Trial 已写入 Supabase: {email} ({tg_username}) -> trial")

    # === 订阅扣款成功（trial 结束 or 月费续费）===
    elif event_type in ["invoice.paid", "invoice.payment_succeeded"]:
        # 如果 email 为空，尝试从对象字段拿
        if not email:
            email = data.get("customer_email")

        expire_at = (datetime.utcnow() + timedelta(days=30)).isoformat()

        supabase.table("subscribers").upsert({
            "email": email,
            "tg_username": tg_username or "unknown",
            "plan": "monthly",
            "created_at": datetime.utcnow().isoformat(),
            "expired_at": expire_at,
            "status": "active"
        }, on_conflict="email").execute()

        print(f"💰 Stripe Monthly 已更新 Supabase: {email} ({tg_username}) -> monthly")

    # === 用户退订 ===
    elif event_type == "customer.subscription.deleted":
        supabase.table("subscribers").update({
            "status": "canceled"
        }).eq("email", email).execute()

        print(f"❌ Stripe 用户退订: {email}")

    else:
        print("⚠️ 未处理的事件:", event_type)

    return {"status": "ok"}
