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

# 1. लॉगिंग सेटअप
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# 2. क्रेडेंशियल्स (Environment Variables से)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# 3. Gemini AI Setup
try:
    ai_client = genai.Client(api_key=GEMINI_API_KEY)
    logger.info("✅ Gemini AI Client Ready!")
except Exception as e:
    logger.error(f"❌ Gemini Setup Error: {e}")

# 4. Render Health Server (24/7 चालू रखने के लिए)
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"AI Quiz Bot is 24/7 Active and Running!")
    def log_message(self, format, *args): return

def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    httpd = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    logger.info(f"🚀 Health Server live on port {port}")
    httpd.serve_forever()

# 5. AI Quiz Logic
async def generate_quiz_from_ai():
    """AI से 10 GK सवाल जेनरेट करना"""
    prompt = """
    Generate 10 Exam-Oriented General Knowledge MCQs in Hindi.
    Strict Rules:
    1. Output MUST be ONLY a valid JSON Array. No conversational text.
    2. Use 'ड' instead of 'ड़'.
    3. JSON Format: [{"question": "आपका सवाल?", "options": ["A", "B", "C", "D"], "answer": 0}]
    """
    try:
        response = ai_client.models.generate_content(model='gemini-1.5-flash', contents=prompt)
        text = response.text.strip()
        
        # JSON निकालने के लिए Regex का उपयोग (सबसे सुरक्षित तरीका)
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            clean_json = match.group()
            return json.loads(clean_json)
        return None
    except Exception as e:
        logger.error(f"AI Generation Error: {e}")
        return None

# 6. Bot Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    await update.message.reply_text(
        f"👋 राम राम {user_name} भाई!\n\n"
        "आपका AI आधारित क्विज़ बोट तैयार है।\n"
        "🚀 10 नए सवाल शुरू करने के लिए /test दबाएँ।"
    )

async def start_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("🔄 AI आपके लिए सवाल तैयार कर रहा है, कृपया 15-20 सेकंड प्रतीक्षा करें...")
    
    quiz_data = await generate_quiz_from_ai()
    
    if not quiz_data:
        await msg.edit_text("❌ AI अभी बिजी है। कृपया 30 सेकंड बाद फिर से /test लिखें।")
        return

    # यूजर का डेटा स्टोर करना
    context.user_data.update({
        'quiz': quiz_data,
        'current_q': 0,
        'score': 0
    })
    
    await show_question(update, context, msg)

async def show_question(update: Update, context: ContextTypes.DEFAULT_TYPE, message_obj=None):
    idx = context.user_data['current_q']
    quiz = context.user_data['quiz']
    q = quiz[idx]

    buttons = []
    for i, opt in enumerate(q['options']):
        buttons.append([InlineKeyboardButton(opt, callback_data=str(i))])

    reply_markup = InlineKeyboardMarkup(buttons)
    text = f"❓ **सवाल {idx+1}/{len(quiz)}**\n\n{q['question']}"

    if message_obj:
        await message_obj.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_ans = int(query.data)
    idx = context.user_data['current_q']
    quiz = context.user_data['quiz']
    correct = quiz[idx]['answer']

    if user_ans == correct:
        context.user_data['score'] += 1
        result_text = "✅ **सही जवाब!**"
    else:
        result_text = f"❌ **गलत जवाब!**\nसही जवाब था: {quiz[idx]['options'][correct]}"

    context.user_data['current_q'] += 1
    
    if context.user_data['current_q'] < len(quiz):
        await query.message.edit_text(f"{result_text}\n\nअगला सवाल आ रहा है...")
        await asyncio.sleep(1.5)
        await show_question(update, context)
    else:
        score = context.user_data['score']
        await query.message.edit_text(
            f"{result_text}\n\n🏆 **क्विज़ पूरा हुआ!**\nआपका स्कोर: {score}/{len(quiz)}\n\nनया टेस्ट शुरू करें: /test"
        )

# 7. Main Function
async def run_bot():
    if not TELEGRAM_BOT_TOKEN:
        logger.critical("❌ टेलीग्राम टोकन नहीं मिला! Environment Variables चेक करें।")
        return

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # कमांड्स जोड़ना
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("test", start_test))
    application.add_handler(CallbackQueryHandler(handle_answer))
    
    # बोट स्टार्ट करना (स्थिर तरीका)
    async with application:
        await application.initialize()
        await application.start()
        logger.info("🤖 Bot is now polling for messages...")
        await application.updater.start_polling(drop_pending_updates=True)
        
        while True:
            await asyncio.sleep(3600)

if __name__ == '__main__':
    # हेल्थ सर्वर को थ्रेड में चलाएँ
    threading.Thread(target=run_health_server, daemon=True).start()
    
    # बोट रन करें
    try:
        asyncio.run(run_bot())
    except Exception as e:
        logger.critical(f"💥 Fatal Crash: {e}")
        sys.exit(1)
