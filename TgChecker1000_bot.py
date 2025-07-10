import requests
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
import logging
import random

# === Configuration ===
API_TOKEN = '8178341358:AAG1UEVB-mPlhh-TNks64iVhOm6Avr4DgDg'  # এখানে তোমার টেলিগ্রাম বট টোকেন দিবে
NEXMO_API_KEY = "9cbaa3d7"
NEXMO_API_SECRET = "gJ8qCUu0RqxTCnYH"
NEXMO_SENDER = "NEXMO"  # চাইলে তোমার Sender ID দিবে

# === Logging setup ===
logging.basicConfig(level=logging.INFO)

# === Bot and Dispatcher ===
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# === Helper function to send SMS via Nexmo ===
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

# === Bot command handlers ===

@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    welcome_text = (
        "👋 হ্যালো! আমি তোমার OTP পাঠানোর বট।\n\n"
        "ব্যবহার করার জন্য:\n"
        "📲 /sendotp +8801XXXXXXXXX\n"
        "এই কমান্ড দিয়ে তোমার নম্বরে OTP পাঠাও।\n\n"
        "উদাহরণ: /sendotp +8801712345678"
    )
    await message.answer(welcome_text)

@dp.message_handler(commands=['sendotp'])
async def sendotp_handler(message: types.Message):
    args = message.get_args()
    if not args:
        await message.reply("দয়া করে একটি ফোন নম্বর দিন, উদাহরণ:\n/sendotp +8801712345678")
        return
    
    phone = args.strip()
    # OTP জেনারেট করা (৬ ডিজিট)
    otp = str(random.randint(100000, 999999))
    
    await message.reply(f"⏳ তোমার OTP পাঠানো হচ্ছে {phone} নম্বরে...")
    
    success = send_otp_sms(phone, otp)
    
    if success:
        await message.reply(f"✅ OTP সফলভাবে পাঠানো হয়েছে!\nOTP: {otp}\n(নকল করে অন্যের কাছে দিবে না)")
    else:
        await message.reply("❌ OTP পাঠাতে সমস্যা হয়েছে। পরে আবার চেষ্টা করো।")

@dp.message_handler()
async def default_handler(message: types.Message):
    await message.reply("আমি বুঝতে পারিনি। সাহায্যের জন্য /start লিখুন।")

# === Run bot ===
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
