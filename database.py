import os
import logging
import asyncio
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.error("SUPABASE_URL or SUPABASE_KEY not found in environment variables")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ──────────────────────────────────────────────────────────────
# User Management
# ──────────────────────────────────────────────────────────────

async def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    """Get user by telegram_id."""
    try:
        response = await asyncio.to_thread(supabase.table("users").select("*").eq("telegram_id", user_id).execute)
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {e}")
        return None

async def create_or_update_user(user_id: int, data: Dict[str, Any]) -> bool:
    """Create or update user profile."""
    try:
        # Check if user exists
        user = await get_user(user_id)
        if user:
            # Update
            await asyncio.to_thread(supabase.table("users").update(data).eq("telegram_id", user_id).execute)
        else:
            # Insert
            insert_data = {"telegram_id": user_id, **data}
            await asyncio.to_thread(supabase.table("users").insert(insert_data).execute)
        return True
    except Exception as e:
        logger.error(f"Error saving user {user_id}: {e}")
        return False

# Alias functions for compatibility with existing code
save_user_profile = create_or_update_user
get_user_profile = get_user
save_user_referat_data = create_or_update_user
get_user_referat_data = get_user

# ──────────────────────────────────────────────────────────────
# Balance & Payments
# ──────────────────────────────────────────────────────────────

async def get_user_balance(user_id: int) -> float:
    """Get user balance."""
    try:
        user = await get_user(user_id)
        if user:
            balance = user.get("balance")
            if balance is None:
                return 0.0
            return float(balance)
        return 0.0
    except Exception as e:
        logger.error(f"Error getting balance for {user_id}: {e}")
        return 0.0

async def update_user_balance(user_id: int, amount: float) -> bool:
    """Update user balance (increment/decrement)."""
    try:
        current_balance = await get_user_balance(user_id)
        new_balance = current_balance + amount
        return await create_or_update_user(user_id, {"balance": new_balance})
    except Exception as e:
        logger.error(f"Error updating balance for {user_id}: {e}")
        return False

async def create_pending_payment(user_id: int, amount: int, receipt_file_id: str,
                               username: str = None, full_name: str = None) -> Optional[str]:
    """Create a new pending payment request."""
    try:
        data = {
            "user_id": user_id,
            "amount": amount,
            "receipt_file_id": receipt_file_id,
            "username": username,
            "full_name": full_name,
            "status": "pending"
        }
        response = await asyncio.to_thread(supabase.table("payments").insert(data).execute)
        if response.data:
            return response.data[0].get("id")
        return None
    except Exception as e:
        logger.error(f"Error creating pending payment for {user_id}: {e}")
        return None

async def approve_pending_payment(payment_id: str) -> Optional[Dict[str, Any]]:
    """Approve a pending payment."""
    try:
        # Get payment info
        response = await asyncio.to_thread(supabase.table("payments").select("*").eq("id", payment_id).execute)
        if not response.data:
            return None
        
        payment = response.data[0]
        if payment["status"] != "pending":
            return None

        # Calculate final amount with 50% bonus for 20000+ topups
        actual_amount = payment["amount"]
        final_amount = actual_amount
        if actual_amount >= 20000:
            final_amount += actual_amount * 0.5

        # Update balance
        success = await update_user_balance(payment["user_id"], final_amount)
        if success:
            # Update payment status
            await asyncio.to_thread(supabase.table("payments").update({"status": "completed"}).eq("id", payment_id).execute)
            payment["amount"] = final_amount
            return payment
        return None
    except Exception as e:
        logger.error(f"Error approving payment {payment_id}: {e}")
        return None

async def reject_pending_payment(payment_id: str) -> Optional[Dict[str, Any]]:
    """Reject a pending payment."""
    try:
        # Get payment info
        response = await asyncio.to_thread(supabase.table("payments").select("*").eq("id", payment_id).execute)
        if not response.data:
            return None
        
        payment = response.data[0]
        if payment["status"] != "pending":
            return None

        # Update payment status
        await asyncio.to_thread(supabase.table("payments").update({"status": "rejected"}).eq("id", payment_id).execute)
        return payment
    except Exception as e:
        logger.error(f"Error rejecting payment {payment_id}: {e}")
        return None

async def get_pending_payments_count() -> int:
    """Get the number of pending payments."""
    try:
        response = await asyncio.to_thread(supabase.table("payments").select("*", count="exact").eq("status", "pending").execute)
        return response.count if response.count is not None else 0
    except Exception as e:
        logger.error(f"Error getting pending payments count: {e}")
        return 0

async def get_pending_payments_list() -> List[Dict[str, Any]]:
    """Get list of all pending payments."""
    try:
        response = await asyncio.to_thread(supabase.table("payments").select("*").eq("status", "pending").execute)
        return response.data if response.data else []
    except Exception as e:
        logger.error(f"Error getting pending payments list: {e}")
        return []

# ──────────────────────────────────────────────────────────────
# Statistics
# ──────────────────────────────────────────────────────────────

async def log_user_action(user_id: int, action_type: str, amount: int = 0):
    """Log user action for statistics."""
    from datetime import datetime
    try:
        data = {
            "user_id": user_id,
            "action_type": action_type,
            "amount": amount,
            "created_at": datetime.utcnow().isoformat()
        }
        await asyncio.to_thread(supabase.table("statistics").insert(data).execute)
    except Exception as e:
        logger.error(f"Error logging action for {user_id}: {e}")

async def has_used_promo(user_id: int, promo_code: str) -> bool:
    """Check if user has already used this promo code."""
    try:
        response = await asyncio.to_thread(supabase.table("statistics").select("*").eq("user_id", user_id).eq("action_type", f"promo_{promo_code}").execute)
        return len(response.data) > 0 if response.data else False
    except Exception as e:
        logger.error(f"Error checking promo for {user_id}: {e}")
        return False

async def mark_promo_used(user_id: int, promo_code: str):
    """Mark a promo code as used by the user."""
    await log_user_action(user_id, f"promo_{promo_code}", amount=0)

async def get_admin_stats() -> Dict[str, Any]:
    """Get general statistics for admin."""
    from datetime import datetime
    try:
        now = datetime.utcnow()
        first_day_of_month = datetime(now.year, now.month, 1).isoformat()

        # Total users
        users_resp = await asyncio.to_thread(supabase.table("users").select("*", count="exact").execute)
        total_users = users_resp.count if users_resp.count is not None else 0

        # Monthly users
        m_users_resp = await asyncio.to_thread(supabase.table("users").select("*", count="exact").gte("created_at", first_day_of_month).execute)
        monthly_users = m_users_resp.count if m_users_resp.count is not None else 0

        # Stats for this month (referats, course works, presentations)
        stats_data = await asyncio.to_thread(supabase.table("statistics").select("action_type, amount").gte("created_at", first_day_of_month).execute)
        
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
            supabase.table("payments")
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
            supabase.table("payments")
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
        response = await asyncio.to_thread(supabase.table("users").select("telegram_id").execute)
        if response.data:
            return [row["telegram_id"] for row in response.data]
        return []
    except Exception as e:
        logger.error(f"Error getting all user ids: {e}")
        return []


# ──────────────────────────────────────────────────────────────
# Receipt Duplicate Tracking & Verification
# ──────────────────────────────────────────────────────────────
import sqlite3
import re

def _init_sqlite_receipts():
    try:
        conn = sqlite3.connect("bot_database.db")
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS verified_receipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tx_id TEXT,
                image_hash TEXT,
                user_id INTEGER,
                amount INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_verified_receipts_tx ON verified_receipts(tx_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_verified_receipts_hash ON verified_receipts(image_hash)")
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error initializing sqlite receipts: {e}")

_init_sqlite_receipts()

def _clean_tx_key(tx_id: str) -> str:
    if not tx_id:
        return ""
    cleaned = re.sub(r'[^a-zA-Z0-9]', '', str(tx_id)).lower()
    return cleaned

async def is_receipt_duplicate(tx_id: Optional[str] = None, image_hash: Optional[str] = None) -> tuple[bool, str]:
    """Check if receipt (by image hash or transaction ID) has already been used."""
    clean_tx = _clean_tx_key(tx_id) if tx_id else ""
    
    # 1. Local SQLite check
    try:
        conn = sqlite3.connect("bot_database.db")
        cur = conn.cursor()
        if image_hash:
            cur.execute("SELECT id FROM verified_receipts WHERE image_hash = ?", (image_hash,))
            if cur.fetchone():
                conn.close()
                return True, "Ushbu to'lov cheki (rasm) allaqachon botda ishlatilgan!"
        if clean_tx and len(clean_tx) >= 4:
            cur.execute("SELECT id FROM verified_receipts WHERE tx_id = ?", (clean_tx,))
            if cur.fetchone():
                conn.close()
                return True, f"Ushbu chek (Tranzaksiya ID: {tx_id}) allaqachon botda ishlatilgan!"
        conn.close()
    except Exception as e:
        logger.error(f"SQLite duplicate check error: {e}")

    # 2. Supabase statistics check
    try:
        if image_hash:
            resp_hash = await asyncio.to_thread(
                supabase.table("statistics")
                .select("id")
                .eq("action_type", f"receipt_hash_{image_hash}")
                .execute
            )
            if resp_hash.data and len(resp_hash.data) > 0:
                return True, "Ushbu to'lov cheki (rasm) oldin ro'yxatdan o'tgan!"

        if clean_tx and len(clean_tx) >= 4:
            resp_tx = await asyncio.to_thread(
                supabase.table("statistics")
                .select("id")
                .eq("action_type", f"receipt_tx_{clean_tx}")
                .execute
            )
            if resp_tx.data and len(resp_tx.data) > 0:
                return True, f"Ushbu chek (Tranzaksiya ID: {tx_id}) oldin tasdiqlangan!"
    except Exception as e:
        logger.error(f"Supabase duplicate check error: {e}")

    return False, ""

async def record_verified_receipt(user_id: int, tx_id: Optional[str], image_hash: Optional[str], amount: int):
    """Save verified receipt to SQLite and Supabase to prevent duplicate reuse."""
    clean_tx = _clean_tx_key(tx_id) if tx_id else ""

    # 1. Save to local SQLite
    try:
        conn = sqlite3.connect("bot_database.db")
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO verified_receipts (tx_id, image_hash, user_id, amount) VALUES (?, ?, ?, ?)",
            (clean_tx if clean_tx else None, image_hash, user_id, amount)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error saving to SQLite verified_receipts: {e}")

    # 2. Save to Supabase statistics
    try:
        if image_hash:
            await log_user_action(user_id, f"receipt_hash_{image_hash}", amount=amount)
        if clean_tx and len(clean_tx) >= 4:
            await log_user_action(user_id, f"receipt_tx_{clean_tx}", amount=amount)
    except Exception as e:
        logger.error(f"Error logging verified receipt to Supabase: {e}")

