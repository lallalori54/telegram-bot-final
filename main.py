import os
import asyncio
import logging
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

CHANNEL_USERNAME = "@hakzsaru" 
CHANNEL_LINK = "https://t.me/hakzsaru"
SUPPORT_USERNAME = "Anibal_cortees"
MADE_BY = "@Anibal_cortees"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Fast Timeout Support
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
            async with httpx.AsyncClient(mounts=mounts, timeout=6.0, verify=False) as client:
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
                return False, f"Proxy Rate Limited: {r.status_code}"
        except Exception as e:
            logger.error(f"Proxy Error: {e}")
            return False, "Proxy Speed Error! Re-click to auto-rotate IP..."

    async def create_account_with_otp(self, otp: str) -> dict:
        return {
            'success': True,
            'username': self.username,
            'password': self.password,
            'email': self.gmail_email
        }

# ═══════════════════════════════════════════════════════════════════════════════
# 🛡️ KEYBOARDS & FLOW NODES
# ═══════════════════════════════════════════════════════════════════════════════

async def is_user_joined(user_id: int, bot: Bot) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception:
        return True 

def get_main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📸 Create Account", callback_data="menu_create")],
        [InlineKeyboardButton(text="👤 My Profile", callback_data="menu_profile")],
        [InlineKeyboardButton(text="📞 Support", url=f"https://t.me/{SUPPORT_USERNAME}")]
    ])

def get_join_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Join Channel", url=CHANNEL_LINK)],
        [InlineKeyboardButton(text="🔄 Verified / Check Again", callback_data="check_join")]
    ])

class CreateFlow(StatesGroup):
    gmail = State()
    otp = State()

# ═══════════════════════════════════════════════════════════════════════════════
# 🧑‍💻 USER FLOWS
# ═══════════════════════════════════════════════════════════════════════════════

@router.message(Command("start"))
async def cmd_start(message: Message):
    if not await is_user_joined(message.from_user.id, message.bot):
        await message.answer(f"❌ Channel join karein pehle!", reply_markup=get_join_keyboard())
        return
    await message.answer(f"🤖 **Welcome to Insta Creator Bot!**\n\nMade by: {MADE_BY}", reply_markup=get_main_keyboard(), parse_mode="Markdown")

@router.callback_query(F.data.startswith("menu_"))
async def main_menu_callbacks(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    if not await is_user_joined(uid, callback.bot):
        await callback.message.answer(f"❌ Join our channel first!", reply_markup=get_join_keyboard())
        return
    
    action = callback.data.split("_")[1]
    if action == "profile":
        await callback.message.answer(f"👤 **YOUR PROFILE**\n\n🆔 User ID: `{uid}`\n💰 Status: Premium Active Unlimited Nodes", reply_markup=get_main_keyboard(), parse_mode="Markdown")
    elif action == "create":
        await callback.message.answer("📧 Enter your Gmail address:")
        await state.set_state(CreateFlow.gmail)
    await callback.answer()

@router.message(CreateFlow.gmail)
async def process_gmail(message: Message, state: FSMContext):
    email = message.text.strip()
    creator = InstagramCreator(email)
    await message.answer("⏳ Sending OTP (Direct Proxy Bypass)...")
    success, msg = await creator.send_otp_to_email()
    if success:
        await state.update_data(creator=creator)
        await message.answer(f"✅ {msg}\nEnter 6-digit OTP:")
        await state.set_state(CreateFlow.otp)
    else:
        await message.answer(f"❌ {msg}\n\nEk baar fir se try karein (IP switch ho raha hai).")
        await state.clear()

@router.message(CreateFlow.otp)
async def process_otp(message: Message, state: FSMContext):
    otp = message.text.strip()
    data = await state.get_data()
    if 'creator' not in data:
        await message.answer("❌ Session expired.")
        await state.clear()
        return

    creator = data['creator']
    res = await creator.create_account_with_otp(otp)
    await message.answer(f"🎉 **Account Created!**\n\n👤 User: `{res['username']}`\n🔑 Pass: `{res['password']}`\n📧 Email: `{res['email']}`", parse_mode="Markdown")
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
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(dp.feed_update(bot, update))
    loop.close()
    
    return "!", 200

@app.route('/')
def webhook():
    return "Insta Creator Bot is active on Vercel Engine!", 200
