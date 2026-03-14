import os
import logging
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
        response = supabase.table("users").select("*").eq("telegram_id", user_id).execute()
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
            supabase.table("users").update(data).eq("telegram_id", user_id).execute()
        else:
            # Insert
            insert_data = {"telegram_id": user_id, **data}
            supabase.table("users").insert(insert_data).execute()
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
    user = await get_user(user_id)
    if user:
        return float(user.get("balance", 0.0))
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
        response = supabase.table("payments").insert(data).execute()
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
        response = supabase.table("payments").select("*").eq("id", payment_id).execute()
        if not response.data:
            return None
        
        payment = response.data[0]
        if payment["status"] != "pending":
            return None

        # Update balance
        success = await update_user_balance(payment["user_id"], payment["amount"])
        if success:
            # Update payment status
            supabase.table("payments").update({"status": "completed"}).eq("id", payment_id).execute()
            return payment
        return None
    except Exception as e:
        logger.error(f"Error approving payment {payment_id}: {e}")
        return None

async def reject_pending_payment(payment_id: str) -> Optional[Dict[str, Any]]:
    """Reject a pending payment."""
    try:
        # Get payment info
        response = supabase.table("payments").select("*").eq("id", payment_id).execute()
        if not response.data:
            return None
        
        payment = response.data[0]
        if payment["status"] != "pending":
            return None

        # Update payment status
        supabase.table("payments").update({"status": "rejected"}).eq("id", payment_id).execute()
        return payment
    except Exception as e:
        logger.error(f"Error rejecting payment {payment_id}: {e}")
        return None

async def get_pending_payments_count() -> int:
    """Get the number of pending payments."""
    try:
        response = supabase.table("payments").select("count", count="exact").eq("status", "pending").execute()
        return response.count if response.count is not None else 0
    except Exception as e:
        logger.error(f"Error getting pending payments count: {e}")
        return 0

async def get_pending_payments_list() -> List[Dict[str, Any]]:
    """Get list of all pending payments."""
    try:
        response = supabase.table("payments").select("*").eq("status", "pending").execute()
        return response.data if response.data else []
    except Exception as e:
        logger.error(f"Error getting pending payments list: {e}")
        return []

# ──────────────────────────────────────────────────────────────
# Statistics
# ──────────────────────────────────────────────────────────────

async def log_user_action(user_id: int, action_type: str, amount: int = 0):
    """Log user action for statistics."""
    try:
        data = {
            "user_id": user_id,
            "action_type": action_type,
            "amount": amount
        }
        supabase.table("statistics").insert(data).execute()
    except Exception as e:
        logger.error(f"Error logging action for {user_id}: {e}")

async def get_admin_stats() -> Dict[str, Any]:
    """Get general statistics for admin."""
    try:
        # Total users
        users_resp = supabase.table("users").select("count", count="exact").execute()
        total_users = users_resp.count if users_resp.count is not None else 0

        # Total revenue (completed payments)
        payments_resp = supabase.table("payments").select("amount").eq("status", "completed").execute()
        total_revenue = sum(p["amount"] for p in payments_resp.data) if payments_resp.data else 0

        # Actions today
        # Note: Ideally filter by date, for now simple count
        stats_resp = supabase.table("statistics").select("count", count="exact").execute()
        total_actions = stats_resp.count if stats_resp.count is not None else 0

        return {
            "total_users": total_users,
            "total_revenue": total_revenue,
            "active_users": total_actions # Placeholder for active users
        }
    except Exception as e:
        logger.error(f"Error getting admin stats: {e}")
        return {"total_users": 0, "total_revenue": 0, "active_users": 0}
