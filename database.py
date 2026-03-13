import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = Path("bot_database.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. user_profiles jadvalini yaratish
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id INTEGER PRIMARY KEY,
            universitet TEXT,
            fakultet TEXT,
            kafedra TEXT,
            muallif TEXT,
            kurs TEXT,
            guruh TEXT,
            uslub TEXT,
            til TEXT DEFAULT "O'zbek",
            balance INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 2. referat_users jadvalini yaratish (qolishi mumkin, lekin balans app.db dan olinadi)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS referat_users (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 0,
            last_topic TEXT,
            last_plan TEXT
        )
    """)
    
    # 3. action_logs jadvalini yaratish (statistika uchun)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS action_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action_type TEXT, -- 'referat', 'course_work', 'presentation', 'topup'
            amount INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 4. pending_payments jadvalini yaratish (to'lov so'rovlarini kuzatish)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pending_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            full_name TEXT,
            amount INTEGER,
            status TEXT DEFAULT 'pending',
            receipt_file_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            reviewed_at TIMESTAMP
        )
    """)
    
    # 5. Agar jadval oldindan bo'lsa, 'created_at' ustuni borligini tekshirish va qo'shish
    try:
        cursor.execute("SELECT created_at FROM user_profiles LIMIT 1")
    except sqlite3.OperationalError:
        logger.info("Adding 'created_at' column to user_profiles table")
        cursor.execute("ALTER TABLE user_profiles ADD COLUMN created_at TIMESTAMP")
        cursor.execute("UPDATE user_profiles SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
    
    conn.commit()
    conn.close()

def save_user_referat_data(user_id: int, data: dict):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if user exists in user_profiles
        cursor.execute("SELECT user_id FROM user_profiles WHERE user_id = ?", (user_id,))
        exists = cursor.fetchone()

        if exists:
             cursor.execute("""
                UPDATE user_profiles 
                SET universitet=?, fakultet=?, kafedra=?, muallif=?, kurs=?, guruh=?, uslub=?, til=?
                WHERE user_id=?
            """, (
                data.get('universitet'),
                data.get('fakultet'),
                data.get('kafedra'),
                data.get('muallif'),
                data.get('kurs'),
                data.get('guruh'),
                data.get('uslub'),
                data.get('til'),
                user_id
            ))
        else:
            cursor.execute("""
                INSERT INTO user_profiles 
                (user_id, universitet, fakultet, kafedra, muallif, kurs, guruh, uslub, til)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                data.get('universitet'),
                data.get('fakultet'),
                data.get('kafedra'),
                data.get('muallif'),
                data.get('kurs'),
                data.get('guruh'),
                data.get('uslub'),
                data.get('til')
            ))
        
        conn.commit()
        conn.close()
        logger.info(f"User data saved for {user_id}")
    except Exception as e:
        logger.error(f"Error saving user data: {e}")

# Alias functions for generic use
save_user_profile = save_user_referat_data

def get_user_referat_data(user_id: int):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row # Access columns by name
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM user_profiles WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        
        conn.close()
        
        if row:
            data = {
                'universitet': row['universitet'] if 'universitet' in row.keys() else None,
                'fakultet': row['fakultet'] if 'fakultet' in row.keys() else None,
                'kafedra': row['kafedra'] if 'kafedra' in row.keys() else None,
                'muallif': row['muallif'] if 'muallif' in row.keys() else None,
                'kurs': row['kurs'] if 'kurs' in row.keys() else None,
                'guruh': row['guruh'] if 'guruh' in row.keys() else None,
                'uslub': row['uslub'] if 'uslub' in row.keys() else None,
                'til': row['til'] if 'til' in row.keys() else None,
                'sahifa': 25, # Default for course work
                'kurs_guruh': f"{row['kurs']} {row['guruh']}".strip() if 'kurs' in row.keys() and 'guruh' in row.keys() else ""
            }
            return data
        return None
    except Exception as e:
        logger.error(f"Error getting user data: {e}")
        return None

# Alias for generic use
get_user_profile = get_user_referat_data

def update_user_balance(user_id: int, amount: int):
    """Balansni bot_database.db da yangilash va app.db ga sinxronlash."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # user_profiles da borligini tekshirish
        cursor.execute("SELECT balance FROM user_profiles WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        
        if row:
            current = row[0] if row[0] else 0
            new_balance = current + amount
            cursor.execute(
                "UPDATE user_profiles SET balance = ? WHERE user_id = ?",
                (new_balance, user_id)
            )
        else:
            new_balance = max(amount, 0)
            cursor.execute(
                "INSERT INTO user_profiles (user_id, balance) VALUES (?, ?)",
                (user_id, new_balance)
            )
        
        conn.commit()
        conn.close()
        logger.info(f"Bot DB balance updated for {user_id} by {amount}. New: {new_balance}")
        
        # app.db ga ham sinxronlash
        try:
            update_app_user_balance(user_id, amount)
        except Exception as e:
            logger.warning(f"App DB sync failed for {user_id}: {e}")
        
        return int(new_balance)
    except Exception as e:
        logger.error(f"Error updating bot balance for {user_id}: {e}")
        return 0

def get_user_balance(user_id: int) -> int:
    """Balansni doim bot_database.db dan olish."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM user_profiles WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        return int(row[0]) if row and row[0] else 0
    except Exception as e:
        logger.error(f"Error getting bot balance for {user_id}: {e}")
        return 0

def log_user_action(user_id: int, action_type: str, amount: int = 0):
    """Foydalanuvchi harakatini statistikaga qo'shish"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO action_logs (user_id, action_type, amount) VALUES (?, ?, ?)",
            (user_id, action_type, amount)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error logging action: {e}")

def get_admin_stats():
    """Admin uchun umumiy statistikani olish"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 1. Umumiy obunachilar (user_profiles jadvalidan)
        cursor.execute("SELECT COUNT(*) FROM user_profiles")
        total_users = cursor.fetchone()[0]
        
        # 2. Shu oyda qo'shilgan obunachilar
        # SQLite'da strftime orqali joriy oyni tekshiramiz
        cursor.execute("""
            SELECT COUNT(*) FROM user_profiles 
            WHERE strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now')
        """)
        monthly_users = cursor.fetchone()[0]
        
        # 3. Harakatlar statistikasi (shu oy uchun)
        cursor.execute("""
            SELECT action_type, COUNT(*), SUM(amount) FROM action_logs
            WHERE strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now')
            GROUP BY action_type
        """)
        action_stats = cursor.fetchall()
        
        stats = {
            "total_users": total_users,
            "monthly_users": monthly_users,
            "referat_count": 0,
            "course_work_count": 0,
            "presentation_count": 0,
            "topup_count": 0,
            "topup_sum": 0
        }
        
        for row in action_stats:
            act_type, count, total_amount = row
            if act_type == 'referat':
                stats['referat_count'] += count
            elif act_type == 'course_work':
                stats['course_work_count'] += count
            elif act_type == 'presentation':
                stats['presentation_count'] += count
            elif act_type == 'topup':
                stats['topup_count'] += count
                if total_amount:
                    stats['topup_sum'] += total_amount
        
        conn.close()
        return stats
    except Exception as e:
        logger.error(f"Error getting admin stats: {e}")
        return {
            "total_users": 0,
            "monthly_users": 0,
            "referat_count": 0,
            "course_work_count": 0,
            "presentation_count": 0,
            "topup_count": 0,
            "topup_sum": 0
        }


# ──────────────────────────────────────────────────────────────
# Pending Payments (To'lov so'rovlarini boshqarish)
# ──────────────────────────────────────────────────────────────

def create_pending_payment(user_id: int, amount: int, receipt_file_id: str,
                           username: str = None, full_name: str = None) -> int:
    """Yangi to'lov so'rovini yaratish. Payment ID qaytaradi."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO pending_payments (user_id, username, full_name, amount, receipt_file_id) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, username, full_name, amount, receipt_file_id)
        )
        payment_id = cursor.lastrowid
        conn.commit()
        conn.close()
        logger.info(f"Pending payment #{payment_id} created: user={user_id}, amount={amount}")
        return payment_id
    except Exception as e:
        logger.error(f"Error creating pending payment: {e}")
        return 0


def approve_pending_payment(payment_id: int) -> dict:
    """To'lovni tasdiqlash. user_id va amount qaytaradi."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_id, amount, status FROM pending_payments WHERE id = ?",
            (payment_id,)
        )
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None
        
        user_id, amount, status = row
        if status != 'pending':
            conn.close()
            return None  # Allaqachon ko'rib chiqilgan
        
        cursor.execute(
            "UPDATE pending_payments SET status = 'approved', reviewed_at = CURRENT_TIMESTAMP WHERE id = ?",
            (payment_id,)
        )
        conn.commit()
        conn.close()
        logger.info(f"Payment #{payment_id} approved for user {user_id}, amount {amount}")
        return {"user_id": user_id, "amount": amount}
    except Exception as e:
        logger.error(f"Error approving payment #{payment_id}: {e}")
        return None


def reject_pending_payment(payment_id: int) -> dict:
    """To'lovni rad etish. user_id va amount qaytaradi."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_id, amount, status FROM pending_payments WHERE id = ?",
            (payment_id,)
        )
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None
        
        user_id, amount, status = row
        if status != 'pending':
            conn.close()
            return None
        
        cursor.execute(
            "UPDATE pending_payments SET status = 'rejected', reviewed_at = CURRENT_TIMESTAMP WHERE id = ?",
            (payment_id,)
        )
        conn.commit()
        conn.close()
        logger.info(f"Payment #{payment_id} rejected for user {user_id}")
        return {"user_id": user_id, "amount": amount}
    except Exception as e:
        logger.error(f"Error rejecting payment #{payment_id}: {e}")
        return None


def get_pending_payments_count() -> int:
    """Kutilayotgan to'lovlar sonini qaytaradi."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM pending_payments WHERE status = 'pending'")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        logger.error(f"Error getting pending payments count: {e}")
        return 0


def get_pending_payments_list():
    """Barcha kutilayotgan to'lovlar ro'yxatini qaytaradi."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM pending_payments WHERE status = 'pending' ORDER BY created_at DESC"
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error getting pending payments list: {e}")
        return []


# ──────────────────────────────────────────────────────────────
# Backend app.db bilan balans sinxronizatsiyasi
# ──────────────────────────────────────────────────────────────

def get_app_user_balance(telegram_id: int) -> int:
    """Backend app.db dan foydalanuvchi balansini olish (telegram_id orqali)."""
    try:
        from config import BACKEND_DB_PATH
        conn = sqlite3.connect(BACKEND_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM users WHERE telegram_id = ?", (telegram_id,))
        row = cursor.fetchone()
        conn.close()
        return int(float(row[0])) if row else 0
    except Exception as e:
        logger.error(f"Error getting app balance for {telegram_id}: {e}")
        return 0


def update_app_user_balance(telegram_id: int, amount: int, first_name: str = "User") -> int:
    """Backend app.db da foydalanuvchi balansini yangilash.
    Agar foydalanuvchi topilmasa, skip qiladi (bot_database.db asosiy manba).
    """
    try:
        from config import BACKEND_DB_PATH
        conn = sqlite3.connect(BACKEND_DB_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT id, balance FROM users WHERE telegram_id = ?", (telegram_id,))
        row = cursor.fetchone()

        if row:
            new_balance = float(row[1]) + amount
            cursor.execute(
                "UPDATE users SET balance = ? WHERE telegram_id = ?",
                (new_balance, telegram_id)
            )
            conn.commit()
            conn.close()
            logger.info(f"App balance updated for tg:{telegram_id} by {amount}. New: {new_balance}")
            return int(new_balance)
        else:
            # Foydalanuvchi app.db da yo'q — skip qilamiz
            # Bot DB asosiy manba, app.db ga faqat mavjud userlar uchun sync
            conn.close()
            logger.info(f"User tg:{telegram_id} not found in app.db, skipping sync")
            return 0
    except Exception as e:
        logger.error(f"Error updating app balance for {telegram_id}: {e}")
        return 0

