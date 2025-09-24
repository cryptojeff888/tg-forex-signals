from datetime import datetime, timedelta
from supabase import create_client
import os

SUPABASE_USER_URL = os.getenv("SUPABASE_USER_URL")
SUPABASE_USER_KEY = os.getenv("SUPABASE_USER_KEY")

user_db = create_client(SUPABASE_USER_URL, SUPABASE_USER_KEY)

def add_subscriber(email: str, tg_username: str, plan: str = "monthly"):
    now = datetime.utcnow()
    expire_at = now + timedelta(days=30)  # monthly 默认 +30 天

    data = {
        "email": email,
        "tg_username": tg_username,
        "plan": plan,
        "created_at": now.isoformat(),
        "expire_at": expire_at.isoformat(),
        "status": "active"
    }

    res = user_db.table("subscribers").insert(data).execute()
    print("✅ New subscriber added:", res)
    return res
