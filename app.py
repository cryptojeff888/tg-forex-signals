from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from paypal_webhook import app as paypal_app
from stripe_webhook import app as stripe_app
import stripe
import os

app = FastAPI()

# === CORS 设置（先放开所有域，测试用）===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # 👈 允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === 合并 PayPal 路由 ===
for route in paypal_app.routes:
    app.router.routes.append(route)

# === 合并 Stripe 路由 ===
for route in stripe_app.routes:
    app.router.routes.append(route)

# === Stripe 初始化 ===
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# === Stripe Checkout Session 创建接口 ===
@app.post("/create-checkout-session")
async def create_checkout_session(plan: str = "trial"):
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
                line_items=[{
                    "price": price_map["monthly"],  # 每月 $29.90
                    "quantity": 1,
                }],
                subscription_data={
                    "trial_period_days": 7,
                    "add_invoice_items": [
                        {
                            "price_data": {
                                "currency": "usd",
                                "unit_amount": 1290,   # upfront $12.90
                                "product_data": {
                                    "name": "TradingVault 7-day Trial Fee"
                                }
                            }
                        }
                    ]
                },
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
                success_url="https://tradingvault.base44.app/?status=success",
                cancel_url="https://tradingvault.base44.app/?status=cancel",
            )
        else:
            return {"error": f"Invalid plan: {plan}"}

        return {"url": checkout_session.url}

    except Exception as e:
        return {"error": str(e)}
