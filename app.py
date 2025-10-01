from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from paypal_webhook import app as paypal_app
from stripe_webhook import app as stripe_app
import stripe
import os

# === 初始化 FastAPI ===
app = FastAPI()

# === CORS 设置 ===
origins = [
    "https://tradingvault.base44.app",  # 前端域名
    "http://localhost:3000",            # 本地调试时用
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === 合并 PayPal 路由 ===
for route in paypal_app.routes:
    app.router.routes.append(route)

# === 合并 Stripe Webhook 路由 ===
for route in stripe_app.routes:
    app.router.routes.append(route)

# === Stripe 初始化 ===
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# Stripe Price IDs
price_map = {
    "monthly": "price_1SD6H1EqeYLgpt07bVN9S6xP",    # TradingVault Monthly ($29.90 / month, recurring)
    "lifetime": "price_1SD6JvEqeYLgpt079qicqkx4",   # TradingVault Lifetime ($299 one-time)
}

# Plan 名字映射
plan_map = {
    "7-Day Trial": "trial",
    "Lifetime Access": "lifetime",
    "trial": "trial",
    "lifetime": "lifetime",
}

# === Stripe Checkout Session 创建接口 ===
@app.post("/create-checkout-session")
async def create_checkout_session(payload: dict):
    plan = payload.get("plan", "trial")
    normalized_plan = plan_map.get(plan, None)

    if not normalized_plan:
        return {"error": f"Invalid plan: {plan}"}

    try:
        if normalized_plan == "trial":
            # Trial: $12.90 upfront + 7天 trial → 之后 $29.90/month
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                mode="subscription",
                line_items=[
                    {
                        "price_data": {
                            "currency": "usd",
                            "unit_amount": 1290,
                            "product_data": {"name": "TradingVault 7-day Trial Setup Fee"},
                        },
                        "quantity": 1,
                    },
                    {
                        "price": price_map["monthly"],  # recurring $29.90/month
                        "quantity": 1,
                    },
                ],
                subscription_data={
                    "trial_period_days": 7
                },
                success_url="https://tradingvault.base44.app/?status=success",
                cancel_url="https://tradingvault.base44.app/?status=cancel",
            )

        elif normalized_plan == "lifetime":
            # 一次性 $299
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                mode="payment",
                line_items=[{
                    "price": price_map["lifetime"],
                    "quantity": 1,
                }],
                success_url="https://tradingvault.base44.app/?status=success",
                cancel_url="https://tradingvault.base44.app/?status=cancel",
            )

        return {"url": checkout_session.url}

    except Exception as e:
        return {"error": str(e)}
