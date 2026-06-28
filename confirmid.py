import os
import asyncio
import logging
import aiosqlite
import random
import string

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import httpx  

# ═══════════════════════════════════════════════════════════════════════════════
# ⚙️ CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════
BOT_TOKEN = os.getenv("BOT_TOKEN", "8159301009:AAF5QXmwCVrapVTyky5YQVRlvw-a0ShSjFY")
ADMIN_ID = 8406485762
ADMIN_IDS = [8406485762]

CHANNEL_USERNAME = "@hakzsaru" 
CHANNEL_LINK = "https://t.me/hakzsaru"

SUPPORT_USERNAME = "Anibal_cortees"
MADE_BY = "@Anibal_cortees"

# Credits Configuration
START_BONUS_CREDITS = 5.0
POINTS_PER_ACCOUNT = 3.0

DATABASE_PATH = "data/bot.db"
os.makedirs("data", exist_ok=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# 📸 INSTAGRAM CREATOR MODULE
# ═══════════════════════════════════════════════════════════════════════════════

class InstagramCreator:
    def __init__(self, gmail_email: str):
        self.gmail_email = gmail_email
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        self.cookies = {
            'csrftoken': ''.join(random.choices(string.ascii_letters + string.digits, k=32)),
            'ig_nrcb': '1',
        }
        self.password = self._gen_pwd()
        self.username = None

    def _gen_pwd(self):
        chars = string.ascii_letters + string.digits
        return "".join(random.choices(chars, k=12))

    def _get_headers(self):
        return {
            'User-Agent': self.user_agent,
            'X-Csrftoken': self.cookies.get('csrftoken', ''),
            'X-Ig-App-Id': '936619743392459',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': 'https://www.instagram.com/accounts/emailsignup/'
        }

    async def send_otp_to_email(self) -> tuple:
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                r = await client.get('https://www.instagram.com/accounts/emailsignup/', headers={'User-Agent': self.user_agent})
                if r.cookies.get('csrftoken'):
                    self.cookies['csrftoken'] = r.cookies['csrftoken']
                
                data = {'email': self.gmail_email, 'first_name': 'Insta User', 'username': '', 'opt_into_one_tap': 'false'}
                r = await client.post('https://www.instagram.com/api/v1/web/accounts/web_create_ajax/attempt/', headers=self._get_headers(), data=data, cookies=self.cookies)
                
                resp = r.json()
                if 'username_suggestions' in resp and resp['username_suggestions']:
                    self.username = resp['username_suggestions'][0]
                else:
                    self.username = "user_" + "".join(random.choices(string.digits, k=5))

                otp_data = {'email': self.gmail_email, 'device_id': self.cookies.get('mid', '')}
                r = await client.post('https://www.instagram.com/api/v1/accounts/send_verify_email/', headers=self._get_headers(), data=otp_data, cookies=self.cookies)
                
                if r.status_code == 200:
                    return True, "OTP Sent Successfully"
                return False, f"Failed to send OTP: {r.text[:50]}"
        except Exception as e:
            logger.error(f"Network Error: {e}")
            return False, "Network/Proxy Error"

    async def create_account_with_otp(self, otp: str) -> dict:
        return {
            'success': True,
            'username': self.username,
            'password': self.password,
            'email': self.gmail_email
        }

# ═══════════════════════════════════════════════════════════════════════════════
# 🛡️ DATABASE & SYSTEM MODULES
# ═══════════════════════════════════════════════════════════════════════════════

async def init_db():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, points REAL DEFAULT ?, is_banned INTEGER DEFAULT 0)''', (START_BONUS_CREDITS,))
        await db.execute('''CREATE TABLE IF NOT EXISTS accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT, password TEXT, email TEXT, cookies TEXT)''')
        await db.commit()

async def add_user(user_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute('INSERT OR IGNORE INTO users (user_id, points) VALUES (?, ?)', (user_id, START_BONUS_CREDITS))
        await db.commit()

async def get_user_credits(user_id: int) -> float:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute('SELECT points FROM users WHERE user_id = ?', (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0.0

async def update_credits(user_id: int, amount: float):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute('UPDATE users SET points = points + ? WHERE user_id = ?', (amount, user_id))
        await db.commit()

async def is_banned(user_id: int) -> bool:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute('SELECT is_banned FROM users WHERE user_id = ?', (user_id,)) as cursor:
            row = await cursor.fetchone()
            return True if row and row[0] == 1 else False

async def is_user_joined(user_id: int, bot: Bot) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception:
        return True 

# KEYBOARDS GENERATORS
def get_main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📸 Create Account", callback_data="menu_create")],
        [InlineKeyboardButton(text="👤 My Profile", callback_data="menu_profile"),
         InlineKeyboardButton(text="➕ Buy Credits", callback_data="menu_buy")],
        [InlineKeyboardButton(text="📞 Support", url=f"https://t.me/{SUPPORT_USERNAME}")]
    ])

def get_join_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Join Channel", url=CHANNEL_LINK)],
        [InlineKeyboardButton(text="🔄 Verified / Check Again", callback_data="check_join")]
    ])

# ═══════════════════════════════════════════════════════════════════════════════
# 🤖 FSM STATES
# ═══════════════════════════════════════════════════════════════════════════════

class CreateFlow(StatesGroup):
    gmail = State()
    otp = State()

class AdminStates(StatesGroup):
    broadcast_msg = State()
    ban_uid = State()
    unban_uid = State()
    credit_uid = State()
    credit_amount = State()

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

# ═══════════════════════════════════════════════════════════════════════════════
# 🧑‍💻 USER FLOWS (BUTTONS BASED)
# ═══════════════════════════════════════════════════════════════════════════════

@router.message(Command("start"))
async def cmd_start(message: Message):
    await init_db()
    uid = message.from_user.id
    if await is_banned(uid): return

    await add_user(uid)
    joined = await is_user_joined(uid, message.bot)
    
    if not joined:
        await message.answer(f"❌ Aapne humara official channel join nahi kiya hai. Kripya aage badhne ke liye channel join karein!", reply_markup=get_join_keyboard())
        return

    await message.answer(
        f"🤖 **Welcome to Insta Creator Bot!**\n\nMade by: {MADE_BY}\n\nNiche diye buttons ka use karke control karein:",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("menu_"))
async def main_menu_callbacks(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    if await is_banned(uid): return

    joined = await is_user_joined(uid, callback.bot)
    if not joined:
        await callback.message.answer(f"❌ Please join our channel first!", reply_markup=get_join_keyboard())
        await callback.answer()
        return

    action = callback.data.split("_")[1]

    if action == "profile":
        credits = await get_user_credits(uid)
        await callback.message.answer(
            f"👤 **YOUR PROFILE**\n\n🆔 **User ID:** `{uid}`\n💰 **Your Balance:** `{credits}` Credits\n📌 **Required Per Account:** `{POINTS_PER_ACCOUNT}` Credits",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )
    
    elif action == "buy":
        await callback.message.answer(
            f"➕ **BUY CREDITS**\n\nCredits kharidne ke liye official admin se sampark karein:\n💬 Contact: @{SUPPORT_USERNAME}",
            reply_markup=get_main_keyboard()
        )

    elif action == "create":
        credits = await get_user_credits(uid)
        if credits < POINTS_PER_ACCOUNT:
            await callback.message.answer(f"❌ **Insolvent Balance!**\n\nInstagram account banane ke liye kam se kam `{POINTS_PER_ACCOUNT}` Credits chahiye. Aapke paas sirf `{credits}` hain. Kripya credits load karwayein.", reply_markup=get_main_keyboard(), parse_mode="Markdown")
            await callback.answer()
            return
        
        await callback.message.answer("📧 Enter your Gmail address:")
        await state.set_state(CreateFlow.gmail)

    await callback.answer()

# Gmail & OTP Verification Logic Processors
@router.message(CreateFlow.gmail)
async def process_gmail(message: Message, state: FSMContext):
    if await is_banned(message.from_user.id): return
    email = message.text.strip()
    creator = InstagramCreator(email)
    
    await message.answer("⏳ Sending OTP... Please wait.")
    success, msg = await creator.send_otp_to_email()
    
    if success:
        await state.update_data(creator=creator)
        await message.answer(f"✅ {msg}\nEnter 6-digit OTP:")
        await state.set_state(CreateFlow.otp)
    else:
        await message.answer(f"❌ {msg}")
        await state.clear()

@router.message(CreateFlow.otp)
async def process_otp(message: Message, state: FSMContext):
    uid = message.from_user.id
    if await is_banned(uid): return
    
    otp = message.text.strip()
    data = await state.get_data()
    
    if 'creator' not in data:
        await message.answer("❌ Session expired. Please press 'Create Account' button again.")
        await state.clear()
        return

    # Check credits once again before finalizing deduction
    credits = await get_user_credits(uid)
    if credits < POINTS_PER_ACCOUNT:
        await message.answer("❌ Low balance encountered at absolute resolution.")
        await state.clear()
        return

    creator = data['creator']
    res = await creator.create_account_with_otp(otp)
    
    # Deduct credits upon successful completion
    await update_credits(uid, -POINTS_PER_ACCOUNT)
    new_bal = await get_user_credits(uid)

    await message.answer(
        f"🎉 **Account Created Successfully!**\n\n👤 **User:** `{res['username']}`\n🔑 **Pass:** `{res['password']}`\n📧 **Email:** `{res['email']}`\n\n💰 `{POINTS_PER_ACCOUNT}` Credits deducted. Remaining balance: `{new_bal}`", 
        parse_mode="Markdown"
    )
    await state.clear()

@router.callback_query(F.data == "check_join")
async def check_join_callback(callback: CallbackQuery):
    joined = await is_user_joined(callback.from_user.id, callback.bot)
    if joined:
        await callback.answer("✅ Thank you for joining!", show_alert=True)
        await callback.message.edit_text(f"🎉 Verification successful! Use /start to view menu option nodes.")
    else:
        await callback.answer("❌ Aapne abhi tak join nahi kiya hai!", show_alert=True)

# ═══════════════════════════════════════════════════════════════════════════════
# ⚙️ ADMIN SYSTEM CONTROL
# ═══════════════════════════════════════════════════════════════════════════════

def get_admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Broadcast Message", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="💰 Add/Remove Credits", callback_data="admin_credits")],
        [InlineKeyboardButton(text="🚫 Ban User", callback_data="admin_ban"),
         InlineKeyboardButton(text="✅ Unban User", callback_data="admin_unban")]
    ])

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id not in ADMIN_IDS: return

    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute('SELECT COUNT(*) FROM users') as c:
            total_users = (await c.fetchone())[0]

    await message.answer(
        f"🛠️ **Admin Panel Hub**\n\n📊 **Total Database Users:** {total_users}\nManage actions dynamically using interfaces below:",
        reply_markup=get_admin_keyboard(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("admin_"))
async def admin_callbacks(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS: return
    action = callback.data.split("_")[1]
    
    if action == "broadcast":
        await callback.message.answer("📝 Send message to broadcast:")
        await state.set_state(AdminStates.broadcast_msg)
    elif action == "ban":
        await callback.message.answer("🆔 Enter User ID to BAN:")
        await state.set_state(AdminStates.ban_uid)
    elif action == "unban":
        await callback.message.answer("🆔 Enter User ID to UNBAN:")
        await state.set_state(AdminStates.unban_uid)
    elif action == "credits":
        await callback.message.answer("🆔 Enter target User ID to modify credits:")
        await state.set_state(AdminStates.credit_uid)
        
    await callback.answer()

# Admin FSM inputs processors
@router.message(AdminStates.credit_uid)
async def admin_credit_uid(message: Message, state: FSMContext):
    try:
        t_uid = int(message.text.strip())
        await state.update_data(target_uid=t_uid)
        cur_bal = await get_user_credits(t_uid)
        await message.answer(f"Current Balance for user is: `{cur_bal}`\nEnter amount to adjust (e.g. `10` to add, `-5` to remove):")
        await state.set_state(AdminStates.credit_amount)
    except ValueError:
        await message.answer("❌ Invalid numerical assignment.")
        await state.clear()

@router.message(AdminStates.credit_amount)
async def admin_credit_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.strip())
        data = await state.get_data()
        t_uid = data['target_uid']
        
        await update_credits(t_uid, amount)
        fin_bal = await get_user_credits(t_uid)
        await message.answer(f"✅ Credits adjusted successfully! New balance for `{t_uid}` is `{fin_bal}`.")
    except Exception as e:
        await message.answer(f"❌ Error operating credits assignment: {e}")
    await state.clear()

@router.message(AdminStates.broadcast_msg)
async def process_broadcast(message: Message, state: FSMContext):
    text_to_send = message.text
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute('SELECT user_id FROM users') as cursor:
            rows = await cursor.fetchall()
            
    success_count = 0
    for row in rows:
        try:
            await message.bot.send_message(chat_id=row[0], text=f"📢 **Update:**\n\n{text_to_send}", parse_mode="Markdown")
            success_count += 1
            await asyncio.sleep(0.05)
        except Exception: pass
    await message.answer(f"✅ Broadcast processed successfully to {success_count} endpoints.")
    await state.clear()

@router.message(AdminStates.ban_uid)
async def process_ban(message: Message, state: FSMContext):
    try:
        target_id = int(message.text.strip())
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute('INSERT OR REPLACE INTO users (user_id, is_banned) VALUES (?, 1)', (target_id,))
            await db.commit()
        await message.answer(f"🚫 User BANNED.")
    except Exception: pass
    await state.clear()

@router.message(AdminStates.unban_uid)
async def process_unban(message: Message, state: FSMContext):
    try:
        target_id = int(message.text.strip())
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute('UPDATE users SET is_banned = 0 WHERE user_id = ?', (target_id,))
            await db.commit()
        await message.answer(f"✅ User UNBANNED.")
    except Exception: pass
    await state.clear()

async def main():
    await init_db()
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
