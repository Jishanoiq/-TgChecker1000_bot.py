import asyncio
import logging
import random
import sqlite3
from datetime import datetime, timedelta
from typing import List

import requests
from aiogram import Bot, Dispatcher, types

# === Configuration ===
API_TOKEN = '8178341358:AAG1UEVB-mPlhh-TNks64iVhOm6Avr4DgDg'
NEXMO_API_KEY = "9cbaa3d7"
NEXMO_API_SECRET = "gJ8qCUu0RqxTCnYH"
NEXMO_SENDER = "NEXMO"

ADMINS = [7471439777, 1868731287]

# === Logging setup ===
logging.basicConfig(level=logging.INFO)

# === Bot setup ===
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# === DB setup ===
conn = sqlite3.connect('otp_data.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
CREATE TABLE IF NOT EXISTS otps (
    user_id INTEGER PRIMARY KEY,
    phone TEXT NOT NULL,
    otp TEXT NOT NULL,
    timestamp DATETIME NOT NULL,
    resend_count INTEGER DEFAULT 0,
    last_sent DATETIME
)
''')
conn.commit()

# === Helper functions ===
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
    now = datetime.utcnow()
    cursor.execute('SELECT resend_count, last_sent FROM otps WHERE user_id=?', (user_id,))
    row = cursor.fetchone()
    if row:
        resend_count, last_sent = row
        resend_count += 1
        cursor.execute('UPDATE otps SET phone=?, otp=?, timestamp=?, resend_count=?, last_sent=? WHERE user_id=?',
                       (phone, otp, now, resend_count, now, user_id))
    else:
        cursor.execute('INSERT INTO otps (user_id, phone, otp, timestamp, resend_count, last_sent) VALUES (?, ?, ?, ?, ?, ?)',
                       (user_id, phone, otp, now, 1, now))
    conn.commit()

def get_otp(user_id: int):
    cursor.execute('SELECT otp, timestamp, resend_count, last_sent, phone FROM otps WHERE user_id=?', (user_id,))
    row = cursor.fetchone()
    return row if row else (None, None, 0, None, None)

def delete_otp(user_id: int):
    cursor.execute('DELETE FROM otps WHERE user_id=?', (user_id,))
    conn.commit()

def is_otp_expired(timestamp: datetime) -> bool:
    expire_time = timestamp + timedelta(minutes=5)
    return datetime.utcnow() > expire_time

def can_resend_otp(last_sent: datetime) -> bool:
    if not last_sent:
        return True
    limit_time = last_sent + timedelta(minutes=2)
    return datetime.utcnow() > limit_time

def is_admin(user_id: int) -> bool:
    return user_id in ADMINS

def bulk_verify_numbers(numbers: List[str]) -> dict:
    result = {}
    for number in numbers:
        result[number] = "Valid" if int(number[-1]) % 2 == 0 else "Invalid"
    return result

# === Handlers ===

@dp.message(commands=['start'])
async def start_handler(message: types.Message):
    welcome_text = (
        "👋 হ্যালো! আমি তোমার OTP পাঠানোর বট।\n\n"
        "📲 /sendotp +8801XXXXXXXXX\n"
        "✅ /verify 123456\n"
        "/bulkcheck +8801xxx,+8801yyy\n"
        "/admin"
    )
    await message.answer(welcome_text)

@dp.message(commands=['sendotp'])
async def sendotp_handler(message: types.Message):
    args = message.text.split(' ', 1)
    user_id = message.from_user.id

    if len(args) < 2:
        await message.reply("দয়া করে একটি ফোন নম্বর দিন:\n/sendotp +88017xxxxxxx")
        return

    phone = args[1].strip()
    _, _, resend_count, last_sent, _ = get_otp(user_id)

    if not can_resend_otp(last_sent):
        await message.reply("⏳ দয়া করে ২ মিনিট পরে আবার চেষ্টা করুন।")
        return

    otp = str(random.randint(100000, 999999))
    save_otp(user_id, phone, otp)

    await message.reply(f"⏳ OTP পাঠানো হচ্ছে {phone} নম্বরে...")
    if send_otp_sms(phone, otp):
        await message.reply(f"✅ OTP পাঠানো হয়েছে!\nOTP: {otp}")
    else:
        await message.reply("❌ OTP পাঠাতে সমস্যা হয়েছে।")

@dp.message(commands=['verify'])
async def verify_handler(message: types.Message):
    args = message.text.split(' ', 1)
    user_id = message.from_user.id

    if len(args) < 2:
        await message.reply("OTP দিন:\n/verify 123456")
        return

    entered_otp = args[1].strip()
    saved_otp, timestamp_str, _, _, _ = get_otp(user_id)

    if not saved_otp:
        await message.reply("❌ OTP পাওয়া যায়নি। /sendotp দিয়ে শুরু করুন।")
        return

    timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S.%f')
    if is_otp_expired(timestamp):
        delete_otp(user_id)
        await message.reply("⏰ OTP মেয়াদ শেষ। নতুন OTP নিন।")
        return

    if entered_otp == saved_otp:
        delete_otp(user_id)
        await message.reply("✅ OTP সফলভাবে যাচাই হয়েছে!")
    else:
        await message.reply("❌ OTP ভুল হয়েছে।")

@dp.message(commands=['bulkcheck'])
async def bulkcheck_handler(message: types.Message):
    args = message.text.split(' ', 1)
    if len(args) < 2:
        await message.reply("কমা দিয়ে নাম্বার দিন:\n/bulkcheck +8801..., +8801...")
        return
    numbers = [num.strip() for num in args[1].split(',')]
    result = bulk_verify_numbers(numbers)
    response = "\n".join(f"{n}: {s}" for n, s in result.items())
    await message.reply(response)

@dp.message(commands=['admin'])
async def admin_handler(message: types.Message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        await message.reply("❌ অনুমতি নেই।")
        return
    await message.reply("🔧 /stats\n🔧 /broadcast <msg>\n🔧 /deleteotp <user_id>")

@dp.message(commands=['stats'])
async def stats_handler(message: types.Message):
    if not is_admin(message.from_user.id): return
    cursor.execute('SELECT COUNT(*) FROM otps')
    count = cursor.fetchone()[0]
    await message.reply(f"📊 মোট OTP রেকর্ড: {count}")

@dp.message(commands=['broadcast'])
async def broadcast_handler(message: types.Message):
    if not is_admin(message.from_user.id): return
    text = message.text.replace("/broadcast", "").strip()
    cursor.execute('SELECT user_id FROM otps')
    users = cursor.fetchall()
    sent = 0
    for (uid,) in users:
        try:
            await bot.send_message(uid, text)
            sent += 1
        except:
            pass
    await message.reply(f"✅ ব্রডকাস্ট পাঠানো হয়েছে: {sent} জনকে")

@dp.message(commands=['deleteotp'])
async def delete_handler(message: types.Message):
    if not is_admin(message.from_user.id): return
    try:
        uid = int(message.text.split(' ')[1])
        delete_otp(uid)
        await message.reply(f"✅ OTP ডিলিট হয়েছে: {uid}")
    except:
        await message.reply("❌ সঠিক user_id দিন")

@dp.message()
async def fallback(message: types.Message):
    await message.reply("❓ আমি বুঝিনি। /start দেখুন।")

# === Run the bot ===
async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
