import os
import stripe
from fastapi import FastAPI
from paypal_webhook import app as paypal_app
from stripe_webhook import app as stripe_app

# 初始化 Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

app = FastAPI()

# === 合并 PayPal 路由 ===
for route in paypal_app.routes:
    app.router.routes.append(route)

# === 合并 Stripe 路由 ===
for route in stripe_app.routes:
    app.router.routes.append(route)


# === Stripe Checkout Session 创建接口 ===
@app.post("/create-checkout-session")
async def create_checkout_session(plan: str = "monthly"):
    """
    根据传入的 plan (trial | monthly | lifetime)
    创建 Stripe Checkout Session
    """

    # === Stripe Price IDs ===
    price_map = {
        "monthly": "price_1SD6H1EqeYLgpt07bVN9S6xP",    # TradingVault Monthly ($29.90 / month)
        "lifetime": "price_1SD6JvEqeYLgpt079qicqkx4",   # TradingVault Lifetime ($299 one-time)
    }

    try:
        if plan == "trial":
            # Trial: 收 $12.90 upfront, 然后 7天后自动转 $29.90/month
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                mode="subscription",
                line_items=[{
                    "price": price_map["monthly"],  # 用 monthly 这个 price
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

        elif plan == "monthly":
            # 直接进入月订阅
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                mode="subscription",
                line_items=[{
                    "price": price_map["monthly"],
                    "quantity": 1,
                }],
                success_url="https://tradingvault.base44.app/?status=success",
                cancel_url="https://tradingvault.base44.app/?status=cancel",
            )

        elif plan == "lifetime":
            # 一次性付费
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
