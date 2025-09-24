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
    res = user_db.table("subscribers").insert({
        "email": "testuser@example.com",
        "tg_username": "testuser123",
        "plan": "monthly",
        "created_at": datetime.utcnow().isoformat(),
        "expired_at": "2025-10-24T08:54:34.512Z",   # 测试先写死，实际用代码算
        "status": "active"
    }).execute()
    print("✅ Insert result:", res)

if __name__ == "__main__":
    test_insert_user()
