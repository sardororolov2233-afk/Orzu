import asyncio
import os
from database import supabase, get_user, get_admin_stats

async def test_connection():
    print("Testing Supabase connection...")
    try:
        # Test table access
        response = supabase.table("users").select("count", count="exact").execute()
        print(f"Connection successful! Total users in DB: {response.count}")
        
        # Test admin stats
        stats = await get_admin_stats()
        print(f"Admin stats test: {stats}")
        
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())
