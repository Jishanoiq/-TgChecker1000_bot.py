# TgChecker1000_bot

একটি Telegram বট যা ব্যবহারকারীর ফোনে Nexmo API ব্যবহার করে OTP পাঠায় এবং নম্বর যাচাই করার সুবিধা দেয়।

---

## বৈশিষ্ট্যসমূহ

- `/start` - বট সম্পর্কে তথ্য দেখায়  
- `/sendotp <phone_number>` - নির্দিষ্ট ফোন নম্বরে OTP পাঠায়  
- OTP পাঠানোর সফলতা ও ত্রুটি হ্যান্ডেলিং  
- লগিং সাপোর্ট  
- সহজ ডিপ্লয়মেন্টের জন্য প্রয়োজনীয় ফাইল

---

## প্রয়োজনীয়তা

- Python 3.10+  
- Telegram Bot Token  
- Nexmo (Vonage) API Key এবং Secret

---

## সেটআপ ও ডিপ্লয়মেন্ট

### ১. রেপো ক্লোন করো

```bash
git clone https://github.com/তোমার-username/তোমার-রেপো.git
cd তোমার-রেপো

২. ভার্চুয়াল এনভায়রনমেন্ট তৈরি এবং dependencies ইন্সটল করো

python -m venv venv
source venv/bin/activate   # Linux/MacOS
venv\Scripts\activate      # Windows

pip install -r requirements.txt

৩. API credentials সেট করো

TgChecker1000_bot.py ফাইলে নিচের জায়গাগুলো তোমার তথ্য দিয়ে আপডেট করো:

API_TOKEN = 'তোমার-টেলিগ্রাম-বট-টোকেন'
NEXMO_API_KEY = 'তোমার-nexmo-api-key'
NEXMO_API_SECRET = 'তোমার-nexmo-api-secret'
NEXMO_SENDER = 'তোমার-sender-id'  # (ঐচ্ছিক)

অথবা উন্নত ব্যবস্থার জন্য .env ফাইল ব্যবহার করতে পারো (এই ক্ষেত্রে কোড আপডেট করতে হবে)।

৪. বট চালানো

python TgChecker1000_bot.py


---

কমান্ডসমূহ

/start
বট শুরু এবং নির্দেশিকা দেখায়।

/sendotp <phone_number>
উদাহরণ: /sendotp +8801712345678
নির্দিষ্ট ফোন নম্বরে OTP পাঠায়।



---

ডিপ্লয়মেন্ট (Render, Heroku, ইত্যাদি)

requirements.txt ফাইল থাকা বাধ্যতামূলক।

Environment variables (API_TOKEN, NEXMO_API_KEY, NEXMO_API_SECRET) প্ল্যাটফর্ম সেটিংসে যুক্ত করো।

স্টার্ট কমান্ডে python TgChecker1000_bot.py ব্যবহার করো।



---

ভবিষ্যৎ আপডেট

Admin-only commands যোগ করা

Bulk number verification

OTP resend limit

Dashboard interface



---

লাইসেন্স

MIT License (প্রয়োজনে পরিবর্তন করো)


---

যোগাযোগ

যদি কোনো সমস্যা বা প্রশ্ন থাকে, আমার সাথে যোগাযোগ করো:
Email: [তোমার ইমেইল]
Telegram: [তোমার টেলিগ্রাম ইউজারনেম]


---

ধন্যবাদ!

---

যদি কোনো অংশে সাহায্য লাগে বা নিজের মতো করতে চাও, আমাকে বলো।
