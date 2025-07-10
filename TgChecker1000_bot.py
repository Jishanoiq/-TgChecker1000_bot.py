import asyncio
import logging
import random
import sqlite3
from datetime import datetime, timedelta
from typing import List

import requests
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

# === Configuration ===
API_TOKEN = '8178341358:AAG1UEVB-mPlhh-TNks64iVhOm6Avr4DgDg'  # তোমার Bot Token
NEXMO_API_KEY = "9cbaa3d7"
NEXMO_API_SECRET = "gJ8qCUu0RqxTCnYH"
NEXMO_SENDER = "NEXMO"  # Sender ID

# তোমার Telegram user ID (যাদের admin অনুমতি দিবে)
ADMINS = [7471439777, 1868731287]  # তোমার Telegram ID এখানে রাখো

# === Logging setup ===
logging.basicConfig(level=logging.INFO)

# === Bot setup ===
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

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

# Bulk verification simulation function
def bulk_verify_numbers(numbers: List[str]) -> dict:
    # এখানে তুমি আসল চেকিং কোড যোগ করবে, এটা সিমুলেশন
    result = {}
    for number in numbers:
        # উদাহরণ: যাদের নম্বর শেষ ডিজিট জোড়, সেগুলো ভ্যালিড
        result[number] = "Valid" if int(number[-1]) % 2 == 0 else "Invalid"
    return result

# === Bot Handlers ===

@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    welcome_text = (
        "👋 হ্যালো! আমি তোমার OTP পাঠানোর বট।\n\n"
        "ব্যবহার করার জন্য:\n"
        "📲 /sendotp +8801XXXXXXXXX\n"
        "OTP যাচাই করতে:\n"
        "✅ /verify 123456\n\n"
        "বাল্ক নম্বর যাচাই করতে:\n"
        "/bulkcheck +8801xxxx,+8801yyyy,+8801zzzz\n\n"
        "অ্যাডমিন কমান্ডের জন্য /admin দেখো"
    )
    await message.answer(welcome_text)

@dp.message_handler(commands=['sendotp'])
async def sendotp_handler(message: types.Message):
    args = message.get_args()
    user_id = message.from_user.id

    if not args:
        await message.reply("দয়া করে একটি ফোন নম্বর দিন, উদাহরণ:\n/sendotp +8801712345678")
        return
    
    phone = args.strip()
    _, _, resend_count, last_sent, _ = get_otp(user_id)

    if not can_resend_otp(last_sent):
        await message.reply("⏳ দুঃখিত, আবার OTP পাঠানোর জন্য ২ মিনিট অপেক্ষা করুন।")
        return

    otp = str(random.randint(100000, 999999))
    save_otp(user_id, phone, otp)

    await message.reply(f"⏳ তোমার OTP পাঠানো হচ্ছে {phone} নম্বরে...")

    success = send_otp_sms(phone, otp)
    if success:
        await message.reply(f"✅ OTP সফলভাবে পাঠানো হয়েছে!\nOTP: {otp}\n(নকল করে অন্যের কাছে দিবে না)")
    else:
        await message.reply("❌ OTP পাঠাতে সমস্যা হয়েছে। পরে আবার চেষ্টা করো।")

@dp.message_handler(commands=['verify'])
async def verify_handler(message: types.Message):
    args = message.get_args()
    user_id = message.from_user.id

    if not args:
        await message.reply("দয়া করে OTP কোড লিখুন, উদাহরণ:\n/verify 863222")
        return
    
    entered_otp = args.strip()
    saved_otp, timestamp_str, _, _, phone = get_otp(user_id)

    if saved_otp is None:
        await message.reply("❌ তোমার জন্য কোনো OTP পাওয়া যায়নি। আগে /sendotp দিয়ে OTP পাঠাও।")
        return

    timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S.%f')
    if is_otp_expired(timestamp):
        delete_otp(user_id)
        await message.reply("⏰ OTP মেয়াদ উত্তীর্ণ হয়েছে। নতুন OTP নিন /sendotp দিয়ে।")
        return

    if entered_otp == saved_otp:
        delete_otp(user_id)
        await message.reply("✅ তোমার OTP সফলভাবে যাচাই হয়েছে। ধন্যবাদ!")
    else:
        await message.reply("❌ OTP ভুল হয়েছে। আবার চেষ্টা করো।")

@dp.message_handler(commands=['bulkcheck'])
async def bulkcheck_handler(message: types.Message):
    args = message.get_args()
    if not args:
        await message.reply("দয়া করে ফোন নম্বর গুলো কমা দিয়ে আলাদা করে পাঠাও, উদাহরণ:\n/bulkcheck +8801712345678,+8801723456789")
        return
    numbers = [num.strip() for num in args.split(',')]
    result = bulk_verify_numbers(numbers)
    response = "📋 বাল্ক ভেরিফিকেশন ফলাফল:\n"
    for num, status in result.items():
        response += f"{num} : {status}\n"
    await message.reply(response)

@dp.message_handler(commands=['admin'])
async def admin_help_handler(message: types.Message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        await message.reply("❌ তুমি অ্যাডমিন না। এই কমান্ড ব্যবহার করতে পারবে না।")
        return
    text = (
        "🔧 অ্যাডমিন কমান্ড:\n"
        "/stats - মোট ইউজার ও OTP তথ্য দেখুন\n"
        "/broadcast <মেসেজ> - সবাইকে মেসেজ পাঠান\n"
        "/deleteotp <user_id> - নির্দিষ্ট ইউজারের OTP ডিলিট করুন\n"
    )
    await message.reply(text)

@dp.message_handler(commands=['stats'])
async def stats_handler(message: types.Message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        await message.reply("❌ তুমি অ্যাডমিন না। এই কমান্ড ব্যবহার করতে পারবে না।")
        return
    cursor.execute('SELECT COUNT(*) FROM otps')
    total_otps = cursor.fetchone()[0]
    await message.reply(f"📊 মোট OTP রেকর্ড: {total_otps}")

@dp.message_handler(commands=['broadcast'])
async def broadcast_handler(message: types.Message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        await message.reply("❌ তুমি অ্যাডমিন না। এই কমান্ড ব্যবহার করতে পারবে না।")
        return
    text = message.get_args()
    if not text:
        await message.reply("❌ ব্রডকাস্ট করার জন্য মেসেজ লিখুন।\nব্যবহার: /broadcast তোমার মেসেজ")
        return
    
    cursor.execute('SELECT user_id FROM otps')
    users = cursor.fetchall()
    count = 0
    for (uid,) in users:
        try:
            await bot.send_message(uid, text)
            count += 1
        except Exception as e:
            logging.error(f"Broadcast failed to {uid}: {e}")
    await message.reply(f"✅ ব্রডকাস্ট সম্পন্ন হয়েছে। মোট পাঠানো হয়েছে: {count} জন")

@dp.message_handler(commands=['deleteotp'])
async def deleteotp_handler(message: types.Message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        await message.reply("❌ তুমি অ্যাডমিন না। এই কমান্ড ব্যবহার করতে পারবে না।")
        return
    args = message.get_args()
    if not args or not args.isdigit():
        await message.reply("❌ ইউজার আইডি সঠিকভাবে দিন, উদাহরণ:\n/deleteotp 123456789")
        return
    del_user_id = int(args)
    delete_otp(del_user_id)
    await message.reply(f"✅ ইউজার আইডি {del_user_id} এর OTP ডিলিট করা হয়েছে।")

@dp.message_handler()
async def default_handler(message: types.Message):
    await message.reply("আমি বুঝতে পারিনি। সাহায্যের জন্য /start লিখুন।")

# === Run Bot ===
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
