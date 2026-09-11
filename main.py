from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
import json
import base64
import requests

app = FastAPI(title="ECG Clinical Assistant - Dr. Nedal Alkhibbi")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

ACCESS_TOKEN = os.getenv("GEMINI_API_KEY", "")

@app.get("/", response_class=HTMLResponse)
@app.head("/")
async def home():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/api/ecg/analyze")
async def analyze_ecg(file: UploadFile = File(...)):
    if not ACCESS_TOKEN:
        return JSONResponse({
            "ok": True,
            "alert_type": "Warning",
            "alert_level": "Configuration Error",
            "interpretation_ar": "مفتاح الوصول غير مُعرّف في إعدادات المنصة.",
            "interpretation_en": "Access token is missing.",
            "recommendation_ar": "يرجى التحقق من متغيرات البيئة GEMINI_API_KEY في Render.",
            "recommendation_en": "Please check environment variables.",
            "summary_ar": "⚠️ خطأ في الإعدادات.",
            "summary_en": "⚠️ Configuration error."
        })
    
    try:
        image_bytes = await file.read()
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        
        # الاتصال المباشر بنقطة النهاية الرسمية لـ Gemini
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
        
        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": """You are an expert cardiologist assistant. Analyze this ECG image professionally. 
Provide the response strictly in JSON format with the following keys:
- "alert_type": "Critical", "Warning", or "Stable"
- "alert_level": Short priority description in Arabic and English
- "interpretation_ar": Detailed clinical interpretation in Arabic (including ST segments, rhythm, electrolytes if visible)
- "interpretation_en": Detailed clinical interpretation in English
- "recommendation_ar": Immediate clinical recommendations in Arabic
- "recommendation_en": Immediate clinical recommendations in English
- "summary_ar": Brief urgent warning or status in Arabic
- "summary_en": Brief urgent warning or status in English"""
                        },
                        {
                            "inline_data": {
                                "mime_type": file.content_type or "image/jpeg",
                                "data": image_b64
                            }
                        }
                    ]
                }
            ]
        }
        
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code != 200:
            return JSONResponse({
                "ok": True,
                "alert_type": "Warning",
                "alert_level": "API Auth Error",
                "interpretation_ar": f"رفض التصريح من خادم جوجل: {response.text}",
                "interpretation_en": f"Google Auth Error: {response.text}",
                "recommendation_ar": "تأكد من صلاحيات مفتاح الـ AQ في حسابك السحابي.",
                "recommendation_en": "Check AQ token permissions.",
                "summary_ar": "⚠️ خطأ في المصادقة.",
                "summary_en": "⚠️ Auth error."
            })
            
        res_json = response.json()
        text_response = res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
        
        if text_response.startswith("```json"):
            text_response = text_response[7:-3].strip()
        elif text_response.startswith("```"):
            text_response = text_response[3:-3].strip()
            
        result_data = json.loads(text_response)
        result_data["ok"] = True
        return JSONResponse(result_data)

    except Exception as e:
        return JSONResponse({
            "ok": True,
            "alert_type": "Warning",
            "alert_level": "Analysis Error",
            "interpretation_ar": f"تعذر تحليل الصورة بدقة: {str(e)}",
            "interpretation_en": f"Failed to analyze image: {str(e)}",
            "recommendation_ar": "تأكد من وضوح صورة تخطيط القلب ومحاولتها مجدداً.",
            "recommendation_en": "Ensure image clarity and try again.",
            "summary_ar": "⚠️ خطأ في معالجة الصورة.",
            "summary_en": "⚠️ Error processing image."
        })