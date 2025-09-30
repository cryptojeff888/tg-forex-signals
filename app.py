from fastapi import FastAPI
from paypal_webhook import app as paypal_app
from stripe_webhook import app as stripe_app

app = FastAPI()

# 合并 PayPal 路由
for route in paypal_app.routes:
    app.router.routes.append(route)

# 合并 Stripe 路由
for route in stripe_app.routes:
    app.router.routes.append(route)
