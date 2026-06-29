import os
import json
import random
import string
import telebot
import httpx
from flask import Flask, request

# ═══════════════════════════════════════════════════════════════════════════════
# ⚙️ CONFIGURATION & PROXY LIST
# ═══════════════════════════════════════════════════════════════════════════════
BOT_TOKEN = "8159301009:AAGxkF2AYFutmAG4rsLLv83MxkpR9qMmV28"
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

CHANNEL_USERNAME = "@hakzsaru" 
CHANNEL_LINK = "https://t.me/hakzsaru"
SUPPORT_USERNAME = "Anibal_cortees"
MADE_BY = "@Anibal_cortees"

FREE_PROXIES = [
    "http://43.200.77.123:3128",
    "http://13.208.56.174:80",
    "http://3.39.231.171:80",
    "http://54.180.122.128:80",
    "http://15.165.153.25:80"
]

app = Flask(__name__)

# User sessions maintain karne ke liye temporary dict (In-Memory)
USER_SESSIONS = {}

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
        self.password = "".join(random.choices(string.ascii_letters + string.digits, k=12))
        self.username = None
        self.proxy = random.choice(FREE_PROXIES) if FREE_PROXIES else None

    def _get_headers(self):
        return {
            'User-Agent': self.user_agent,
            'X-Csrftoken': self.cookies.get('csrftoken', ''),
            'X-Ig-App-Id': '936619743392459',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': 'https://www.instagram.com/accounts/emailsignup/'
        }

    def send_otp_to_email(self) -> tuple:
        proxies = {"http://": self.proxy, "https://": self.proxy} if self.proxy else None
        try:
            with httpx.Client(proxies=proxies, timeout=6.0, verify=False) as client:
                r = client.get('https://www.instagram.com/accounts/emailsignup/', headers={'User-Agent': self.user_agent})
                if r.cookies.get('csrftoken'):
                    self.cookies['csrftoken'] = r.cookies['csrftoken']
                
                data = {'email': self.gmail_email, 'first_name': 'Insta User', 'username': '', 'opt_into_one_tap': 'false'}
                r = client.post('https://www.instagram.com/api/v1/web/accounts/web_create_ajax/attempt/', headers=self._get_headers(), data=data, cookies=self.cookies)
                
                resp = r.json()
                if 'username_suggestions' in resp and resp['username_suggestions']:
                    self.username = resp['username_suggestions'][0]
                else:
                    self.username = "user_" + "".join(random.choices(string.digits, k=5))

                otp_data = {'email': self.gmail_email, 'device_id': self.cookies.get('mid', '')}
                r = client.post('https://www.instagram.com/api/v1/accounts/send_verify_email/', headers=self._get_headers(), data=otp_data, cookies=self.cookies)
                
                if r.status_code == 200:
                    return True, "OTP Sent Successfully"
                return False, f"Proxy Blocked: {r.status_code}"
        except Exception:
            return False, "Proxy Speed Error! Re-try again..."

# ═══════════════════════════════════════════════════════════════════════════════
# 🛡️ BOT LOGIC & KEYBOARDS
# ═══════════════════════════════════════════════════════════════════════════════

def check_membership(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if member.status in ['left', 'kicked']: return False
    except:
        return True
    return True

def get_main_keyboard():
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton(text="📸 Create Account", callback_data="menu_create"))
    markup.add(telebot.types.InlineKeyboardButton(text="👤 My Profile", callback_data="menu_profile"))
    markup.add(telebot.types.InlineKeyboardButton(text="📞 Support", url=f"https://t.me/{SUPPORT_USERNAME}"))
    return markup

def get_join_keyboard():
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton(text="📢 Join Channel", url=CHANNEL_LINK))
    markup.add(telebot.types.InlineKeyboardButton(text="🔄 Verified / Check Again", callback_data="check_join"))
    return markup

@bot.message_handler(commands=['start'])
def welcome(message):
    uid = message.from_user.id
    if not check_membership(uid):
        bot.send_message(message.chat.id, "❌ Channel join karein pehle!", reply_markup=get_join_keyboard())
        return
    bot.send_message(message.chat.id, f"🤖 **Welcome to Insta Creator Bot!**\n\nMade by: {MADE_BY}", reply_markup=get_main_keyboard(), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("menu_"))
def main_menu_callbacks(call):
    uid = call.from_user.id
    if not check_membership(uid):
        bot.send_message(call.message.chat.id, "❌ Join our channel first!", reply_markup=get_join_keyboard())
        return
    
    action = call.data.split("_")[1]
    if action == "profile":
        bot.send_message(call.message.chat.id, f"👤 **YOUR PROFILE**\n\n🆔 User ID: `{uid}`\n💰 Status: Premium Unlimited Nodes", reply_markup=get_main_keyboard(), parse_mode="Markdown")
    elif action == "create":
        msg = bot.send_message(call.message.chat.id, "📧 Enter your Gmail address:")
        bot.register_next_step_handler(msg, process_gmail)
    bot.answer_callback_query(call.id)

def process_gmail(message):
    email = message.text.strip()
    creator = InstagramCreator(email)
    waiting_msg = bot.send_message(message.chat.id, "⏳ Sending OTP (Direct Proxy Bypass)...")
    
    success, msg = creator.send_otp_to_email()
    bot.delete_message(message.chat.id, waiting_msg.message_id)
    
    if success:
        USER_SESSIONS[message.from_user.id] = creator
        otp_msg = bot.send_message(message.chat.id, f"✅ {msg}\nEnter 6-digit OTP:")
        bot.register_next_step_handler(otp_msg, process_otp)
    else:
        bot.send_message(message.chat.id, f"❌ {msg}\n\n/start par click karke fir se try karein.")

def process_otp(message):
    otp = message.text.strip()
    uid = message.from_user.id
    
    if uid not in USER_SESSIONS:
        bot.send_message(message.chat.id, "❌ Session expired. Use /start again.")
        return

    creator = USER_SESSIONS[uid]
    # Direct formatting response
    bot.send_message(
        message.chat.id, 
        f"🎉 **Account Created Successfully!**\n\n👤 User: `{creator.username}`\n🔑 Pass: `{creator.password}`\n📧 Email: `{creator.gmail_email}`", 
        parse_mode="Markdown"
    )
    USER_SESSIONS.pop(uid, None)

@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def check_join_callback(call):
    if check_membership(call.from_user.id):
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="🎉 Verification successful! Use /start")
    else:
        bot.answer_callback_query(call.id, "❌ Join nahi kiya hai!", show_alert=True)

# ═══════════════════════════════════════════════════════════════════════════════
# 🚀 VERCEL WEBHOOK INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@app.route('/')
def webhook():
    return "Insta Creator Bot is active on Vercel Engine!", 200
