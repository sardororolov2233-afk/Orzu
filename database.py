"""One Supabase project shared with the presentation API. No local balance ledger."""
import asyncio
import logging
import os
import re
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from supabase import create_client, Client
from commerce import rpc, register

load_dotenv()
logger = logging.getLogger(__name__)
_client = None


def get_supabase() -> Client:
    global _client
    if _client is None:
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY", "")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL va SUPABASE_SERVICE_ROLE_KEY kerak")
        _client = create_client(url, key)
    return _client


async def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    response = await asyncio.to_thread(get_supabase().table("users").select("*").eq("telegram_id", user_id).execute)
    return response.data[0] if response.data else None


async def create_or_update_user(user_id: int, data: Dict[str, Any]) -> bool:
    await register(get_supabase(), {"id": user_id, **data})
    return True


async def save_user_profile(user_id: int, data: Dict[str, Any]) -> bool:
    # FSM keys belong in JSON, not arbitrary columns on the users table.
    await asyncio.to_thread(get_supabase().table("users").update({"bot_profiles": data}).eq("telegram_id", user_id).execute)
    return True


async def get_user_profile(user_id: int):
    user = await get_user(user_id)
    return (user or {}).get("bot_profiles", {})


save_user_referat_data = save_user_profile
get_user_referat_data = get_user_profile


async def get_user_balance(user_id: int) -> float:
    user = await get_user(user_id)
    return float((user or {}).get("balance") or 0)


async def create_pending_payment(user_id: int, amount: int, receipt_file_id: str,
                                 username=None, full_name=None, purpose="topup",
                                 receipt_hash=None, receipt_tx=None, review=None):
    if amount not in {8000, 10000, 25000, 30000, 50000} or purpose not in {"topup", "subscription"}:
        raise ValueError("Noto‘g‘ri to‘lov")
    data = {"user_id": user_id, "amount": amount, "receipt_file_id": receipt_file_id,
        "username": username, "full_name": full_name, "status": "pending", "purpose": purpose,
        "receipt_hash": receipt_hash, "receipt_tx": _clean_tx_key(receipt_tx) or None,
        "review": review or {}}
    response = await asyncio.to_thread(get_supabase().table("payments").insert(data).execute)
    return str(response.data[0]["id"]) if response.data else None


async def approve_pending_payment(payment_id):
    return await rpc(get_supabase(), "commerce_approve_payment", p_payment_id=str(payment_id))


async def reject_pending_payment(payment_id):
    return await rpc(get_supabase(), "commerce_reject_payment", p_payment_id=str(payment_id))


async def get_pending_payments_count():
    response = await asyncio.to_thread(get_supabase().table("payments").select("id", count="exact").eq("status", "pending").execute)
    return response.count or 0


async def get_pending_payments_list():
    response = await asyncio.to_thread(get_supabase().table("payments").select("*").eq("status", "pending").execute)
    return response.data or []


async def log_user_action(user_id: int, action_type: str, amount: int = 0):
    await asyncio.to_thread(get_supabase().table("statistics").insert({"user_id": user_id,
        "action_type": action_type, "amount": amount}).execute)


def _clean_tx_key(tx_id):
    return re.sub(r"[^a-zA-Z0-9]", "", str(tx_id or "")).lower()


async def is_receipt_duplicate(tx_id=None, image_hash=None):
    # Persistent across restarts and multiple bot processes; unique indexes close the race.
    for column, value in (("receipt_hash", image_hash), ("receipt_tx", _clean_tx_key(tx_id))):
        if value:
            result = await asyncio.to_thread(get_supabase().table("payments").select("id")
                .eq(column, value).in_("status", ["pending", "completed"]).limit(1).execute)
            if result.data:
                return True, "Ushbu chek allaqachon yuborilgan yoki tasdiqlangan."
            legacy = await asyncio.to_thread(get_supabase().table("commerce_receipt_keys").select("key")
                .eq("kind", "hash" if column == "receipt_hash" else "tx").eq("key", value).limit(1).execute)
            if legacy.data:
                return True, "Ushbu chek avval tasdiqlangan."
    return False, ""


async def get_admin_stats() -> Dict[str, Any]:
    """Get general statistics for admin."""
    from datetime import datetime
    try:
        now = datetime.utcnow()
        first_day_of_month = datetime(now.year, now.month, 1).isoformat()

        # Total users
        users_resp = await asyncio.to_thread(get_supabase().table("users").select("*", count="exact").execute)
        total_users = users_resp.count if users_resp.count is not None else 0

        # Monthly users
        m_users_resp = await asyncio.to_thread(get_supabase().table("users").select("*", count="exact").gte("created_at", first_day_of_month).execute)
        monthly_users = m_users_resp.count if m_users_resp.count is not None else 0

        # Stats for this month (referats, course works, presentations)
        stats_data = await asyncio.to_thread(get_supabase().table("statistics").select("action_type, amount").gte("created_at", first_day_of_month).execute)
        
        referat_count = 0
        course_work_count = 0
        presentation_count = 0
        
        if stats_data.data:
            for row in stats_data.data:
                action = row.get("action_type")
                if action == "referat":
                    referat_count += 1
                elif action == "course_work":
                    course_work_count += 1
                elif action == "presentation":
                    presentation_count += 1

        # Get payments stats from payments table directly (status = completed, created_at >= first_day_of_month)
        payments_resp = await asyncio.to_thread(
            get_supabase().table("payments")
            .select("amount")
            .eq("status", "completed")
            .gte("created_at", first_day_of_month)
            .execute
        )
        
        topup_count = 0
        topup_sum = 0
        if payments_resp.data:
            topup_count = len(payments_resp.data)
            topup_sum = sum(int(row.get("amount") or 0) for row in payments_resp.data)

        # Get total payments stats from payments table (status = completed)
        total_payments_resp = await asyncio.to_thread(
            get_supabase().table("payments")
            .select("amount")
            .eq("status", "completed")
            .execute
        )
        
        total_topup_count = 0
        total_topup_sum = 0
        if total_payments_resp.data:
            total_topup_count = len(total_payments_resp.data)
            total_topup_sum = sum(int(row.get("amount") or 0) for row in total_payments_resp.data)

        return {
            "total_users": total_users,
            "monthly_users": monthly_users,
            "referat_count": referat_count,
            "course_work_count": course_work_count,
            "presentation_count": presentation_count,
            "topup_count": topup_count,
            "topup_sum": topup_sum,
            "total_topup_count": total_topup_count,
            "total_topup_sum": total_topup_sum
        }
    except Exception as e:
        logger.error(f"Error getting admin stats: {e}")
        return {}

async def get_all_user_ids() -> List[int]:
    """Get all user telegram_ids for broadcast."""
    try:
        response = await asyncio.to_thread(get_supabase().table("users").select("telegram_id").execute)
        if response.data:
            return [row["telegram_id"] for row in response.data]
        return []
    except Exception as e:
        logger.error(f"Error getting all user ids: {e}")
        return []
