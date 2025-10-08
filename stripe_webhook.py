import os
import json
import stripe
from fastapi import FastAPI, Request
from supabase import create_client
from datetime import datetime, timedelta

# === Railway 环境变量 ===
SUPABASE_USER_URL = os.getenv("SUPABASE_USER_URL")
SUPABASE_USER_KEY = os.getenv("SUPABASE_USER_KEY")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

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

    # ✅ checkout.session.completed → 12.90 trial
    if event_type == "checkout.session.completed":
        email = data.get("customer_email")
        customer_id = data.get("customer")

        if not email and customer_id:
            try:
                customer = stripe.Customer.retrieve(customer_id)
                email = customer.get("email")
            except Exception as e:
                print("⚠️ 获取 email 失败:", e)

        if not email:
            print(f"⚠️ Skipped checkout webhook - missing email (customer: {customer_id})")
            return {"status": "skipped"}

        expire_at = (datetime.utcnow() + timedelta(days=7)).isoformat()

        supabase.table("subscribers").upsert({
            "email": email,
            "tg_username": customer_id or "unknown",
            "plan": "trial",
            "created_at": datetime.utcnow().isoformat(),
            "expired_at": expire_at,
            "status": "active"
        }, on_conflict="email").execute()

        print(f"✅ Stripe Trial 已写入 Supabase: {email} -> trial")

    # ========== 订阅扣款成功 (trial 结束 or 月费续费) ==========
    elif event_type in ["invoice.paid", "invoice.payment_succeeded"]:
        customer_id = data.get("customer")
        email = data.get("customer_email")

        if not email and customer_id:
            try:
                customer = stripe.Customer.retrieve(customer_id)
                email = customer.get("email")
            except Exception as e:
                print("⚠️ 无法获取 email:", e)

        if not email:
            print(f"⚠️ Skipped invoice webhook - missing email (customer: {customer_id})")
            return {"status": "skipped"}

        expire_at = (datetime.utcnow() + timedelta(days=30)).isoformat()

        supabase.table("subscribers").upsert({
            "email": email,
            "tg_username": customer_id or "unknown",
            "plan": "monthly",
            "created_at": datetime.utcnow().isoformat(),
            "expired_at": expire_at,
            "status": "active"
        }, on_conflict="email").execute()

        print(f"💰 Stripe Monthly 已更新 Supabase: {email} -> monthly")

    # ========== 用户退订 ==========
    elif event_type == "customer.subscription.deleted":
        customer_id = data.get("customer")

        supabase.table("subscribers").update({
            "status": "canceled"
        }).eq("tg_username", customer_id).execute()

        print(f"❌ Stripe 用户退订: {customer_id}")

    else:
        print("⚠️ 未处理的事件:", event_type)

    return {"status": "ok"}
