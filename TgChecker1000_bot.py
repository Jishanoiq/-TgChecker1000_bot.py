import asyncio
import logging
import random
import sqlite3
from datetime import datetime, timedelta
from typing import List

import requests
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message

from telethon import TelegramClient
from telethon.errors.rpcerrorlist import PhoneNumberInvalidError

# ==== CONFIGURATION ====

API_TOKEN = '8178341358:AAG1UEVB-mPlhh-TNks64iVhOm6Avr4DgDg'

# Telegram API credentials (telethon)
API_ID = 29688700            # তোমার api_id
API_HASH = 'edc5c355c1fb49ed6101b0fcd30531ad'  # তোমার api_hash

# Nexmo SMS config
NEXMO_API_KEY = "9cbaa3d7"
NEXMO_API_SECRET = "gJ8qCUu0RqxTCnYH"
NEXMO_SENDER = "NEXMO"

ADMINS = [7471439777, 1868731287]

# ==== SETUP LOGGING ====

logging.basicConfig(level=logging.INFO)

# ==== DATABASE ====

conn = sqlite3.connect('otp_data.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
CREATE TABLE IF NOT EXISTS otps (
    user_id INTEGER PRIMARY KEY,
    phone TEXT NOT NULL,
    otp TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    resend_count INTEGER DEFAULT 0,
    last_sent TEXT
)
''')
conn.commit()

# ==== BOT SETUP ====

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# ==== TELETHON CLIENT SETUP ====

# Telethon client (Session name can be anything, e.g. 'session')
tele_client = TelegramClient('session', API_ID, API_HASH)

# ==== HELPERS ====

def send_otp_sms(phone_number: str, otp_code: str) -> bool:
    url = "https://rest.nexmo.com/sms/json"
    payload = {
        "api_key": NEXMO_API_KEY,
        "api_secret": NEXMO_API_SECRET,
        "to": phone_number,
        "from": NEXMO_SENDER,
        "text": f"Your OTP code is {otp_code}"
    }
    try:
        response = requests.post(url, data=payload)
        result = response.json()
        if response.status_code == 200 and result["messages"][0]["status"] == "0":
            return True
        else:
            logging.error(f"Failed to send SMS: {result}")
            return False
    except Exception as e:
        logging.error(f"Exception in sending SMS: {e}")
        return False

def save_otp(user_id: int, phone: str, otp: str):
    now_str = datetime.utcnow().isoformat()
    cursor.execute('SELECT resend_count, last_sent FROM otps WHERE user_id=?', (user_id,))
    row = cursor.fetchone()
    if row:
        resend_count, last_sent = row
        resend_count = resend_count + 1 if resend_count else 1
        cursor.execute('UPDATE otps SET phone=?, otp=?, timestamp=?, resend_count=?, last_sent=? WHERE user_id=?',
                       (phone, otp, now_str, resend_count, now_str, user_id))
    else:
        cursor.execute('INSERT INTO otps (user_id, phone, otp, timestamp, resend_count, last_sent) VALUES (?, ?, ?, ?, ?, ?)',
                       (user_id, phone, otp, now_str, 1, now_str))
    conn.commit()

def get_otp(user_id: int):
    cursor.execute('SELECT otp, timestamp, resend_count, last_sent, phone FROM otps WHERE user_id=?', (user_id,))
    row = cursor.fetchone()
    if row:
        otp, timestamp, resend_count, last_sent, phone = row
        return otp, timestamp, resend_count, last_sent, phone
    return None, None, 0, None, None

def delete_otp(user_id: int):
    cursor.execute('DELETE FROM otps WHERE user_id=?', (user_id,))
    conn.commit()

def is_otp_expired(timestamp_str: str) -> bool:
    try:
        timestamp = datetime.fromisoformat(timestamp_str)
        expire_time = timestamp + timedelta(minutes=5)
        return datetime.utcnow() > expire_time
    except:
        return True

def can_resend_otp(last_sent_str: str) -> bool:
    if not last_sent_str:
        return True
    try:
        last_sent = datetime.fromisoformat(last_sent_str)
        limit_time = last_sent + timedelta(minutes=2)
        return datetime.utcnow() > limit_time
    except:
        return True

def is_admin(user_id: int) -> bool:
    return user_id in ADMINS

# ==== TELETHON NUMBER CHECKING FUNCTION ====

async def check_number_telethon(phone_number: str) -> str:
    # এই ফাংশনটি চেষ্টা করবে নাম্বারটি Telegram এ রেজিস্টার আছে কিনা চেক করতে
    try:
        # Telethon এর check_username_available ফাংশন নাম্বার চেক করতে নেই, তাই
        # এখানে আমরা Try/Except দিয়ে ফোন নম্বরের ভ্যালিডিটি ও টেলিগ্রাম একাউন্ট আছে কিনা যাচাই করব
        await tele_client.connect()
        # Telethon এর sign_in বা অন্য method এ সরাসরি নাম্বার যাচাই সহজ নয়
        # তাই আমরা এখানে শুধু ফোন নাম্বার ফরম্যাট বা ভ্যালিড কিনা পরীক্ষা করব (সিম্পল) 
        # — নাম্বার সঠিক ফরম্যাট না হলে PhoneNumberInvalidError আসবে
        # এক্ষেত্রে আমরা নাম্বার ভ্যালিড বলব, কিন্তু Telegram এ রেজিস্টার কিনা আলাদা API দিয়ে চেক করতে হবে
        # এজন্য এটি সিমুলেশন - আসল Telegram registration চেক করা হলে আলাদা code লাগবে
        if len(phone_number) < 10 or not phone_number.startswith('+'):
            return "Invalid Format"
        return "Valid"  # সিমুলেশন হিসেবে
    except PhoneNumberInvalidError:
        return "Invalid Number"
    except Exception as e:
        logging.error(f"Telethon check error for {phone_number}: {e}")
        return "Error"

async def bulk_verify_numbers(numbers: List[str]) -> dict:
    results = {}
    for number in numbers:
        result = await check_number_telethon(number)
        results[number] = result
    return results

# ==== HANDLERS ====

@dp.message(Command("start"))
async def start_handler(message: Message):
    welcome_text = (
        "👋 হ্যালো! আমি তোমার OTP পাঠানোর বট।\n\n"
        "ব্যবহার:\n"
        "📲 /sendotp +8801XXXXXXXXX\n"
        "✅ /verify 123456\n"
        "📋 /bulkcheck +8801xxx,+8801yyy\n\n"
        "অ্যাডমিন কমান্ডের জন্য /admin"
    )
    await message.answer(welcome_text)

@dp.message(Command("sendotp"))
async def sendotp_handler(message: Message):
    args = message.text.split(maxsplit=1)
    user_id = message.from_user.id

    if len(args) < 2:
        await message.reply("দয়া করে ফোন নম্বর দিন, যেমন:\n/sendotp +8801712345678")
        return

    phone = args[1].strip()
    _, _, _, last_sent, _ = get_otp(user_id)

    if not can_resend_otp(last_sent):
        await message.reply("⏳ আবার OTP পাঠাতে ২ মিনিট অপেক্ষা করুন।")
        return

    otp = str(random.randint(100000, 999999))
    save_otp(user_id, phone, otp)

    await message.reply(f"⏳ OTP পাঠানো হচ্ছে {phone} নম্বরে...")
    success = send_otp_sms(phone, otp)
    if success:
        await message.reply(f"✅ OTP পাঠানো হয়েছে! কোড: {otp}\nঅনুগ্রহ করে শেয়ার করবেন না।")
    else:
        await message.reply("❌ OTP পাঠাতে সমস্যা হয়েছে। পরে আবার চেষ্টা করুন।")

@dp.message(Command("verify"))
async def verify_handler(message: Message):
    args = message.text.split(maxsplit=1)
    user_id = message.from_user.id

    if len(args) < 2:
        await message.reply("OTP দিন, যেমন:\n/verify 123456")
        return

    entered_otp = args[1].strip()
    saved_otp, timestamp_str, _, _, _ = get_otp(user_id)

    if not saved_otp:
        await message.reply("❌ তোমার জন্য OTP পাওয়া যায়নি। প্রথমে /sendotp ব্যবহার করো।")
        return

    if is_otp_expired(timestamp_str):
        delete_otp(user_id)
        await message.reply("⏰ OTP এর মেয়াদ শেষ। নতুন OTP নিতে /sendotp ব্যবহার করুন।")
        return

    if entered_otp == saved_otp:
        delete_otp(user_id)
        await message.reply("✅ OTP সফলভাবে যাচাই হয়েছে!")
    else:
        await message.reply("❌ OTP ভুল হয়েছে। আবার চেষ্টা করুন।")

@dp.message(Command("bulkcheck"))
async def bulkcheck_handler(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("কমা দিয়ে ফোন নম্বর দিন:\n/bulkcheck +8801xxxx,+8801yyyy")
        return
    numbers = [num.strip() for num in args[1].split(',')]
    await message.reply("⏳ নাম্বার যাচাই শুরু হচ্ছে, অপেক্ষা করুন...")
    results = await bulk_verify_numbers(numbers)
    response = "📋 বাল্ক ভেরিফিকেশন ফলাফল:\n"
    for num, status in results.items():
        response += f"{num} : {status}\n"
    await message.reply(response)

@dp.message(Command("admin"))
async def admin_handler(message: Message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        await message.reply("❌ তুমি অ্যাডমিন নও।")
        return
    admin_text = (
        "🔧 অ্যাডমিন কমান্ড:\n"
        "/stats - মোট OTP রেকর্ড দেখুন\n"
        "/broadcast <মেসেজ> - সবাইকে মেসেজ পাঠান\n"
        "/deleteotp <user_id> - ইউজারের OTP ডিলিট করুন"
    )
    await message.reply(admin_text)

@dp.message(Command("stats"))
async def stats_handler(message: Message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        await message.reply("❌ অনুমতি নেই।")
        return
    cursor.execute('SELECT COUNT(*) FROM otps')
    count = cursor.fetchone()[0]
    await message.reply(f"📊 মোট OTP রেকর্ড: {count}")

@dp.message(Command("broadcast"))
async def broadcast_handler(message: Message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        await message.reply("❌ অনুমতি নেই।")
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("❌ ব্রডকাস্ট মেসেজ দিন, যেমন:\n/broadcast সবাইকে শুভেচ্ছা!")
        return
    text = args[1]
    cursor.execute('SELECT user_id FROM otps')
    users = cursor.fetchall()
    sent = 0
    for (uid,) in users:
        try:
            await bot.send_message(uid, text)
            sent += 1
        except Exception as e:
            logging.error(f"Broadcast failed to {uid}: {e}")
    await message.reply(f"✅ ব্রডকাস্ট পাঠানো হয়েছে: {sent} জনকে।")

@dp.message(Command("deleteotp"))
async def deleteotp_handler(message: Message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        await message.reply("❌ অনুমতি নেই।")
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].isdigit():
        await message.reply("❌ সঠিক user_id দিন, যেমন:\n/deleteotp 123456789")
        return
    del_user_id = int(args[1])
    delete_otp(del_user_id)
    await message.reply(f"✅ user_id {del_user_id} এর OTP ডিলিট করা হয়েছে।")

@dp.message()
async def fallback_handler(message: Message):
    await message.reply("❓ আমি বুঝতে পারিনি। সাহায্যের জন্য /start লিখুন।")

# ==== RUN BOT AND TELETHON CLIENT ====

async def main():
    await tele_client.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
