import os
import asyncio
import logging
import aiosqlite
import random
import string
import json

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Update
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from flask import Flask, request
import httpx  

# ═══════════════════════════════════════════════════════════════════════════════
# ⚙️ CONFIGURATION & PROXY LIST
# ═══════════════════════════════════════════════════════════════════════════════
BOT_TOKEN = "8159301009:AAGxkF2AYFutmAG4rsLLv83MxkpR9qMmV28"
ADMIN_ID = 8406485762
ADMIN_IDS = [8406485762]

CHANNEL_USERNAME = "@hakzsaru" 
CHANNEL_LINK = "https://t.me/hakzsaru"

SUPPORT_USERNAME = "Anibal_cortees"
MADE_BY = "@Anibal_cortees"

START_BONUS_CREDITS = 5.0
POINTS_PER_ACCOUNT = 3.0

# Vercel supports temp directory for lightweight dynamic DBs like SQLite
DATABASE_PATH = "/tmp/bot.db"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FREE_PROXIES = [
    "http://43.200.77.123:3128",
    "http://13.208.56.174:80",
    "http://3.39.231.171:80",
    "http://54.180.122.128:80",
    "http://15.165.153.25:80"
]

app = Flask(__name__)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

# ═══════════════════════════════════════════════════════════════════════════════
# 📸 INSTAGRAM CREATOR MODULE (WITH PROXY ROTATION)
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
        self.proxy = random.choice(FREE_PROXIES) if FREE_PROXIES else None

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
        mounts = {"http://": httpx.AsyncHTTPTransport(proxy=self.proxy), "https://": httpx.AsyncHTTPTransport(proxy=self.proxy)} if self.proxy else None
        try:
            async with httpx.AsyncClient(mounts=mounts, timeout=20.0, verify=False) as client:
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
                return False, f"Instagram Blocked Request: {r.status_code}"
        except Exception as e:
            logger.error(f"Proxy Error: {e}")
            return False, "Proxy Error! Try Again (IP Rotated Node)..."

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

# FSM STATES
class CreateFlow(StatesGroup):
    gmail = State()
    otp = State()

class AdminStates(StatesGroup):
    broadcast_msg = State()
    ban_uid = State()
    unban_uid = State()
    credit_uid = State()
    credit_amount = State()

# ═══════════════════════════════════════════════════════════════════════════════
# 🧑‍💻 USER FLOWS & ADMIN PANEL
# ═══════════════════════════════════════════════════════════════════════════════

@router.message(Command("start"))
async def cmd_start(message: Message):
    await init_db()
    uid = message.from_user.id
    if await is_banned(uid): return
    await add_user(uid)
    if not await is_user_joined(uid, message.bot):
        await message.answer(f"❌ Channel join karein pehle!", reply_markup=get_join_keyboard())
        return
    await message.answer(f"🤖 **Welcome to Insta Creator Bot!**\n\nMade by: {MADE_BY}", reply_markup=get_main_keyboard(), parse_mode="Markdown")

@router.callback_query(F.data.startswith("menu_"))
async def main_menu_callbacks(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    if await is_banned(uid): return
    if not await is_user_joined(uid, callback.bot):
        await callback.message.answer(f"❌ Join our channel first!", reply_markup=get_join_keyboard())
        return
    
    action = callback.data.split("_")[1]
    if action == "profile":
        credits = await get_user_credits(uid)
        await callback.message.answer(f"👤 **YOUR PROFILE**\n\n🆔 User ID: `{uid}`\n💰 Balance: `{credits}` Credits", reply_markup=get_main_keyboard(), parse_mode="Markdown")
    elif action == "buy":
        await callback.message.answer(f"➕ **BUY CREDITS**\n\nContact: @{SUPPORT_USERNAME}", reply_markup=get_main_keyboard())
    elif action == "create":
        credits = await get_user_credits(uid)
        if credits < POINTS_PER_ACCOUNT:
            await callback.message.answer(f"❌ Insolvent Balance! Need `{POINTS_PER_ACCOUNT}`", reply_markup=get_main_keyboard())
            return
        await callback.message.answer("📧 Enter your Gmail address:")
        await state.set_state(CreateFlow.gmail)
    await callback.answer()

@router.message(CreateFlow.gmail)
async def process_gmail(message: Message, state: FSMContext):
    if await is_banned(message.from_user.id): return
    email = message.text.strip()
    creator = InstagramCreator(email)
    await message.answer("⏳ Sending OTP (Rotating Proxy Engine)...")
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
        await message.answer("❌ Session expired.")
        await state.clear()
        return

    creator = data['creator']
    res = await creator.create_account_with_otp(otp)
    await update_credits(uid, -POINTS_PER_ACCOUNT)
    new_bal = await get_user_credits(uid)
    await message.answer(f"🎉 **Account Created!**\n\n👤 User: `{res['username']}`\n🔑 Pass: `{res['password']}`\n📧 Email: `{res['email']}`\n\nRemaining: `{new_bal}`", parse_mode="Markdown")
    await state.clear()

@router.callback_query(F.data == "check_join")
async def check_join_callback(callback: CallbackQuery):
    if await is_user_joined(callback.from_user.id, callback.bot):
        await callback.message.edit_text(f"🎉 Verification successful! Use /start")
    else:
        await callback.answer("❌ Join nahi kiya hai!", show_alert=True)

# ═══════════════════════════════════════════════════════════════════════════════
# 🚀 VERCEL WEBHOOK INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = Update.model_validate_json(json_string)
    
    # Run async dispatch handling inside Flask lifecycle node
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(init_db())
    loop.run_until_complete(dp.feed_update(bot, update))
    loop.close()
    
    return "!", 200

@app.route('/')
def webhook():
    return "Insta Creator Bot is active on Vercel Engine!", 200
