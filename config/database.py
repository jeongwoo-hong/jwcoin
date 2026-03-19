"""
데이터베이스 클라이언트 (싱글톤)
"""
import os
from supabase import create_client, Client

_supabase_client: Client = None


def get_supabase() -> Client:
    """Supabase 클라이언트 싱글톤"""
    global _supabase_client

    if _supabase_client is None:
        _supabase_client = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_KEY")
        )

    return _supabase_client