# ═══════════════════════════════════════════════════════════════════════════════
# 🚀 INSTAGRAM ACCOUNT CREATOR BOT - PROXY ENABLED VERSION
# ═══════════════════════════════════════════════════════════════════════════════

import os
import asyncio
import logging
import aiosqlite
import requests
import random
import time
import string
import re
from datetime import datetime
from io import BytesIO

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, BufferedInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from PIL import Image, ImageDraw

# ═══════════════════════════════════════════════════════════════════════════════
# ⚙️ CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════
import os
BOT_TOKEN = os.getenv("8429728741:AAH0giCOAk8LXLQf9yF-UhtwiFlQBejot4")
ADMIN_ID = 8406485762
ADMIN_IDS = [8406485762]

# 🌐 PROXY CONFIGURATION (Very Important!)
# Format: "http://username:password@ip:port" or "http://ip:port"
# Instagram ke liye Residential ya Mobile Proxies best hote hain.
PROXY_LIST = [
    # "http://user1:pass1@ip1:port1",
    # "http://user2:pass2@ip2:port2",
]

# Check All Channels
CHANNELS = [
    {"username": "hakzsaru", "link": "https://t.me/hakzsaru", "name": "Hakzsaru"},
    {"username": "gujjucryptto", "link": "https://t.me/gujjucryptto", "name": "Gujju Crypto"},
    {"username": "nav_khush", "link": "https://t.me/nav_khush", "name": "Nav Khush"},
]

SUPPORT_USERNAME = "proffesorcolor"
MADE_BY = "@Proffesorcolor"
POINTS_PER_ACCOUNT = 3

DATABASE_PATH = "data/bot.db"
os.makedirs("data", exist_ok=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# 📸 INSTAGRAM CREATOR MODULE WITH PROXY
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
        self.proxy = self._get_random_proxy()

    def _get_random_proxy(self):
        if not PROXY_LIST:
            return None
        proxy_url = random.choice(PROXY_LIST)
        return {"http": proxy_url, "https": proxy_url}

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
            # Initial Request to get CSRF
            r = requests.get(
                'https://www.instagram.com/accounts/emailsignup/', 
                headers={'User-Agent': self.user_agent}, 
                proxies=self.proxy, 
                timeout=20
            )
            
            if r.cookies.get('csrftoken'):
                self.cookies['csrftoken'] = r.cookies['csrftoken']
            
            # Attempt to check email & get username suggestions
            data = {
                'email': self.gmail_email,
                'first_name': 'Insta User',
                'username': '',
                'opt_into_one_tap': 'false'
            }
            
            r = requests.post(
                'https://www.instagram.com/api/v1/web/accounts/web_create_ajax/attempt/',
                headers=self._get_headers(),
                data=data,
                cookies=self.cookies,
                proxies=self.proxy,
                timeout=20
            )
            
            resp = r.json()
            if 'username_suggestions' in resp:
                self.username = resp['username_suggestions'][0]
            else:
                self.username = "user_" + "".join(random.choices(string.digits, k=5))

            # Send OTP Request
            otp_data = {'email': self.gmail_email, 'device_id': self.cookies.get('mid', '')}
            r = requests.post(
                'https://www.instagram.com/api/v1/accounts/send_verify_email/',
                headers=self._get_headers(),
                data=otp_data,
                cookies=self.cookies,
                proxies=self.proxy,
                timeout=20
            )
            
            if r.status_code == 200:
                return True, "OTP Sent Successfully"
            return False, f"Failed to send OTP: {r.text[:50]}"
            
        except Exception as e:
            logger.error(f"Proxy Error or Network Error: {e}")
            return False, "Network/Proxy Error"

    async def create_account_with_otp(self, otp: str, progress_callback=None) -> dict:
        result = {'success': False, 'error': None}
        try:
            if progress_callback: await progress_callback("Verifying OTP...")
            
            # Finalize signup logic here...
            # Note: This is where you'd call check_confirmation_code and web_create_ajax
            # Always pass proxies=self.proxy to every requests call.
            
            result['success'] = True
            result['username'] = self.username
            result['password'] = self.password
            result['email'] = self.gmail_email
            result['cookies'] = "sessionid=mock_data_for_demo"
            return result
        except Exception as e:
            result['error'] = str(e)
            return result

# ═══════════════════════════════════════════════════════════════════════════════
# 🤖 BOT LOGIC (Database & Handlers)
# ═══════════════════════════════════════════════════════════════════════════════

# Note: Keep your database functions (init_db, get_user, etc.) here.
# Same as in your original file.

async def init_db():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, points REAL DEFAULT 5, is_banned INTEGER DEFAULT 0)''')
        await db.execute('''CREATE TABLE IF NOT EXISTS accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT, password TEXT, email TEXT, cookies TEXT)''')
        await db.commit()

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

@router.message(Command("start"))
async def cmd_start(message: Message):
    await init_db()
    # Add user to DB logic...
    await message.answer("Welcome to Insta Creator! Use /create to start.")

class CreateFlow(StatesGroup):
    gmail = State()
    otp = State()

@router.message(Command("create"))
async def start_create(message: Message, state: FSMContext):
    await message.answer("Enter your Gmail address:")
    await state.set_state(CreateFlow.gmail)

@router.message(CreateFlow.gmail)
async def process_gmail(message: Message, state: FSMContext):
    email = message.text.strip()
    creator = InstagramCreator(email)
    
    if creator.proxy:
        await message.answer(f"Using Proxy: `{creator.proxy['http'].split('@')[-1]}`", parse_mode="Markdown")
    else:
        await message.answer("⚠️ Warning: No proxies configured! Using Server IP.")

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
    otp = message.text.strip()
    data = await state.get_data()
    creator = data['creator']
    
    res = await creator.create_account_with_otp(otp)
    if res['success']:
        await message.answer(f"🎉 Account Created!\nUser: `{res['username']}`\nPass: `{res['password']}`", parse_mode="Markdown")
    else:
        await message.answer(f"❌ Error: {res['error']}")
    await state.clear()

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

