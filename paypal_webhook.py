import os
import json
from fastapi import FastAPI, Request
from supabase import create_client
from datetime import datetime, timedelta

# === Railway 环境变量 ===
SUPABASE_USER_URL = os.getenv("SUPABASE_USER_URL")
SUPABASE_USER_KEY = os.getenv("SUPABASE_USER_KEY")
PAYPAL_WEBHOOK_ID = os.getenv("PAYPAL_WEBHOOK_ID")  # PayPal dashboard 生成
PAYPAL_MODE = os.getenv("PAYPAL_MODE", "sandbox")   # sandbox / live

# === 初始化 Supabase ===
supabase = create_client(SUPABASE_USER_URL, SUPABASE_USER_KEY)

# === FastAPI 应用 ===
app = FastAPI()

# === PayPal Webhook 入口 ===
@app.post("/paypal-webhook")
async def paypal_webhook(request: Request):
    body = await request.body()
    data = json.loads(body.decode("utf-8"))
    print("🔔 收到 PayPal Webhook:", data)

    event_type = data.get("event_type")
    resource = data.get("resource", {})

    # ========== Trial + Monthly ==========
    if event_type == "BILLING.SUBSCRIPTION.ACTIVATED":
        subscriber = resource.get("subscriber", {})
        email = subscriber.get("email_address")
        tg_username = subscriber.get("payer_id") or "unknown"

        plan_id = resource.get("plan_id", "")
        # ⚠️ 这里你可以根据 PayPal plan_id 判断到底是 trial 还是 monthly
        if "trial" in plan_id.lower():
            plan = "trial"
            expire_at = (datetime.utcnow() + timedelta(days=7)).isoformat()
        else:
            plan = "monthly"
            expire_at = (datetime.utcnow() + timedelta(days=30)).isoformat()

        supabase.table("subscribers").insert({
            "email": email,
            "tg_username": tg_username,
            "plan": plan,
            "created_at": datetime.utcnow().isoformat(),
            "expired_at": expire_at,
            "status": "active"
        }).execute()

        print(f"✅ 已写入 Supabase: {email} -> {plan}")

    # ========== Lifetime ==========
    elif event_type == "PAYMENT.SALE.COMPLETED":
        payer = resource.get("payer", {})
        email = payer.get("email_address")
        tg_username = payer.get("payer_id") or "unknown"

        supabase.table("subscribers").insert({
            "email": email,
            "tg_username": tg_username,
            "plan": "lifetime",
            "created_at": datetime.utcnow().isoformat(),
            "expired_at": None,
            "status": "active"
        }).execute()

        print(f"✅ 已写入 Supabase: {email} -> lifetime")

    else:
        print("⚠️ 未处理的 event:", event_type)

    return {"status": "ok"}
