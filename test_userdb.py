import os
from supabase import create_client
from datetime import datetime

# 从 Railway 环境变量读取
SUPABASE_USER_URL = os.getenv("SUPABASE_USER_URL")
SUPABASE_USER_KEY = os.getenv("SUPABASE_USER_KEY")

# 初始化 Supabase 用户库
user_db = create_client(SUPABASE_USER_URL, SUPABASE_USER_KEY)

def test_insert_user():
    """往用户库写一条测试数据"""
    res = user_db.table("profiles").insert({
        "email": "testuser@example.com",
        "membership_type": "monthly",
        "payment_method": "stripe",
        "created_at": datetime.utcnow().isoformat()
    }).execute()
    print("✅ Insert result:", res)

if __name__ == "__main__":
    test_insert_user()
