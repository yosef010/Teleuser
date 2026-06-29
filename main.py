import os
import asyncio
from fastapi import FastAPI, HTTPException, Query
from telethon import TelegramClient
from dotenv import load_dotenv

load_dotenv()

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
PHONE_NUMBER = os.getenv("PHONE_NUMBER")

# حفظ ملف الجلسة في مجلد /tmp لضمان صلاحيات الكتابة على السيرفر
SESSION_PATH = "/tmp/telegram_session"

app = FastAPI()

# تعريف متغيرات عالمية لحفظ حالة تسجيل الدخول مؤقتاً
client = None
phone_code_hash = None

@app.on_event("startup")
async def startup_event():
    global client
    if API_ID and API_HASH:
        client = TelegramClient(SESSION_PATH, int(API_ID), API_HASH)
        await client.connect()

@app.get("/")
def home():
    return {"status": "working", "message": "Telegram API Server is running"}

# 1. رابط طلب إرسال الكود إلى هاتفك
@app.get("/auth/send_code")
async def send_code():
    global phone_code_hash
    if not client:
        raise HTTPException(status_code=500, detail="Client not initialized")
    
    if await client.is_user_authorized():
        return {"status": "already_authorized", "message": "الحساب مسجل دخول بالفعل!"}
    
    try:
        # طلب إرسال الكود من تليجرام
        result = await client.send_code_request(PHONE_NUMBER)
        phone_code_hash = result.phone_code_hash
        return {"status": "code_sent", "message": "تم إرسال الكود إلى حسابك في تليجرام"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# 2. رابط إدخال الكود لتفعيل الحساب
@app.get("/auth/verify")
async def verify_code(code: str = Query(..., description="الكود المكون من 5 أرقام"), password: str = Query(None, description="كلمة مرور التحقق بخطوتين إذا كانت مفعلة")):
    global phone_code_hash
    if not client:
        raise HTTPException(status_code=500, detail="Client not initialized")
    
    try:
        if password:
            await client.sign_in(PHONE_NUMBER, code=code, password=password, phone_code_hash=phone_code_hash)
        else:
            await client.sign_in(PHONE_NUMBER, code=code, phone_code_hash=phone_code_hash)
        
        return {"status": "success", "message": "تم تسجيل الدخول بنجاح على السيرفر!"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# 3. رابط إرسال الرسائل (اللي هتحتاجه في n8n)
@app.post("/send_message/")
async def send_message(group_id: str, message: str):
    if not client or not await client.is_user_authorized():
        raise HTTPException(status_code=401, detail="السيرفر غير مسجل دخول، اذهب إلى /auth/send_code أولاً")
    try:
        await client.send_message(group_id, message)
        return {"status": "success", "target": group_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
