import os
import sys
import logging
import threading
import asyncio
import json
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
from google import genai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# 1. लॉगिंग
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

# 2. क्रेडेंशियल्स (Environment Variables से)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

try:
    ai_client = genai.Client(api_key=GEMINI_API_KEY)
except Exception as e:
    logger.error(f"AI Setup Error: {e}")

# 3. हेल्थ सर्वर (Render के लिए)
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Quiz Bot is Online")
    def log_message(self, format, *args): return

def run_health_server():
    httpd = HTTPServer(("0.0.0.0", int(os.environ.get("PORT", 10000))), HealthCheckHandler)
    httpd.serve_forever()

# --- 4. AI QUIZ GENERATION FROM FACTS ---

def load_user_facts():
    """facts.json फाइल से डेटा लोड करना"""
    try:
        with open("facts.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            # अगर फाइल में लिस्ट है तो उसे टेक्स्ट बना लें
            if isinstance(data, list):
                return "\n".join(data)
            return str(data)
    except Exception as e:
        logger.warning(f"facts.json नहीं मिली, डिफ़ॉल्ट GK इस्तेमाल होगा।")
        return "General Knowledge facts about India."

async def generate_quiz_ai():
    user_facts = load_user_facts()
    prompt = f"""
    तुम्हें नीचे दिए गए तथ्यों (Facts) का उपयोग करके 10 बेहतरीन GK MCQs तैयार करने हैं।
    तथ्य: {user_facts}
    
    नियम:
    1. 'ड़' की जगह हमेशा 'ड' का प्रयोग करें।
    2. आउटपुट केवल एक शुद्ध JSON Array होना चाहिए।
    Format: [{"question": "...", "options": ["A", "B", "C", "D"], "answer": 0}]
    """
    try:
        response = ai_client.models.generate_content(model='gemini-1.5-flash', contents=prompt)
        match = re.search(r'\[.*\]', response.text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return None
    except Exception as e:
        logger.error(f"AI Generation Error: {e}")
        return None

# --- 5. BOT HANDLERS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # अगर बोट बिजी है तो कुछ न करें
    if context.user_data.get('is_generating'): return
    
    await update.message.reply_text(
        "👋 राम राम भाई! मैं तैयार हूँ।\n"
        "🚀 आपके फैक्ट्स से 10 सवाल बनवाने के लिए यहाँ क्लिक करें: /test"
    )

async def start_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # LOCK SYSTEM: अगर बोट पहले से सवाल बना रहा है, तो दूसरी कमांड इग्नोर करें
    if context.user_data.get('is_generating'):
        return 

    context.user_data['is_generating'] = True
    msg = await update.message.reply_text("⏳ मैं आपके फैक्ट्स पढ़ रहा हूँ और सवाल तैयार कर रहा हूँ... कृपया प्रतीक्षा करें।")
    
    quiz_data = await generate_quiz_ai()
    
    if not quiz_data:
        context.user_data['is_generating'] = False
        await msg.edit_text("❌ अभी AI से संपर्क नहीं हो पाया। कृपया 30 सेकंड बाद फिर से /test दबाएँ।")
        return

    context.user_data.update({
        'quiz': quiz_data,
        'current_q': 0,
        'score': 0,
        'is_generating': False # UNLOCK: अब बोट जवाब सुनेगा
    })
    
    await show_question(update, context, msg)

async def show_question(update: Update, context: ContextTypes.DEFAULT_TYPE, message_obj=None):
    idx = context.user_data['current_q']
    q = context.user_data['quiz'][idx]
    
    buttons = [[InlineKeyboardButton(opt, callback_data=str(i))] for i, opt in enumerate(q['options'])]
    reply_markup = InlineKeyboardMarkup(buttons)
    text = f"❓ **सवाल {idx+1}/10**\n\n{q['question']}"

    if message_obj:
        await message_obj.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    # अगर नया टेस्ट शुरू हो रहा है, तो पुराने बटन्स को इग्नोर करें
    if context.user_data.get('is_generating') or 'quiz' not in context.user_data:
        await query.answer("कृपया टेस्ट तैयार होने का इंतज़ार करें।")
        return

    await query.answer()
    user_ans = int(query.data)
    idx = context.user_data['current_q']
    quiz = context.user_data['quiz']
    correct = quiz[idx]['answer']

    if user_ans == correct:
        context.user_data['score'] += 1
        res = "✅ सही!"
    else:
        res = f"❌ गलत! सही: {quiz[idx]['options'][correct]}"

    context.user_data['current_q'] += 1
    if context.user_data['current_q'] < len(quiz):
        await query.message.edit_text(f"{res}\n\nअगला सवाल आ रहा है...")
        await asyncio.sleep(1)
        await show_question(update, context)
    else:
        await query.message.edit_text(
            f"🏆 **टेस्ट पूरा हुआ!**\nआपका स्कोर: {context.user_data['score']}/10\n\nनया टेस्ट: /test"
        )

async def run_bot():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("test", start_test))
    app.add_handler(CallbackQueryHandler(handle_answer))
    
    async with app:
        await app.initialize()
        await app.start()
        logger.info("🤖 Bot Started")
        await app.updater.start_polling(drop_pending_updates=True)
        while True: await asyncio.sleep(3600)

if __name__ == '__main__':
    threading.Thread(target=run_health_server, daemon=True).start()
    try:
        asyncio.run(run_bot())
    except Exception as e:
        sys.exit(1)
