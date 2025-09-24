import os
from datetime import datetime, timedelta
from supabase import create_client

SUPABASE_USER_URL = os.getenv("SUPABASE_USER_URL")
SUPABASE_USER_KEY = os.getenv("SUPABASE_USER_KEY")
user_db = create_client(SUPABASE_USER_URL, SUPABASE_USER_KEY)

def add_subscriber(email: str, tg_username: str, plan: str = "monthly"):
    """Payment 成功时写入 subscribers"""
    now = datetime.utcnow()
    expired_at = now + timedelta(days=30)  # monthly = 30天

    data = {
        "email": email,
        "tg_username": tg_username,
        "plan": plan,
        "created_at": now.isoformat(),
        "expired_at": expired_at.isoformat(),
        "status": "active"
    }

    res = user_db.table("subscribers").insert(data).execute()
    print("✅ Subscriber added:", res)
    return res
