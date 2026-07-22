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

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = "7908449655:AAGVk4HYN98rZkJoeTtPIDHsHdmnr1hPG9w"
GEMINI_API_KEY = "AQ.Ab8RN6I8NtXy-q7H3WQPXGnJrpbTXsXrwLjA1Vs80h9YCxkccw"

try:
    ai_client = genai.Client(api_key=GEMINI_API_KEY)
    logger.info("✅ Gemini Ready")
except Exception as e:
    logger.error(f"❌ AI Setup Error: {e}")

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Active")
    def log_message(self, format, *args): return

async def generate_quiz_from_ai():
    # 20 की जगह 10 सवाल मांगना ज्यादा सुरक्षित है ताकि AI अटके नहीं
    prompt = "Generate 10 Exam GK MCQs in Hindi. Rule: Use 'ड' for 'ड़'. Output ONLY a JSON array: [{\"question\": \"...\", \"options\": [\"A\", \"B\", \"C\", \"D\"], \"answer\": 0}]"
    try:
        response = ai_client.models.generate_content(model='gemini-1.5-flash', contents=prompt)
        text = response.text.strip()
        
        # JSON निकालने का सबसे मजबूत तरीका (Regex)
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return None
    except Exception as e:
        logger.error(f"AI Error: {e}")
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 राम राम भाई! क्विज़ के लिए /test दबाएँ।")

async def start_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("⏳ AI सवाल तैयार कर रहा है (15-20 सेकंड रुकें)...")
    quiz_data = await generate_quiz_from_ai()
    
    if not quiz_data:
        await msg.edit_text("❌ AI अभी बिजी है। कृपया 30 सेकंड बाद फिर कोशिश करें।")
        return

    context.user_data.update({'quiz': quiz_data, 'current_q': 0, 'score': 0})
    await show_question(update, context, msg)

async def show_question(update: Update, context: ContextTypes.DEFAULT_TYPE, message_obj=None):
    idx = context.user_data['current_q']
    quiz = context.user_data['quiz']
    q = quiz[idx]
    buttons = [[InlineKeyboardButton(opt, callback_data=str(i))] for i, opt in enumerate(q['options'])]
    text = f"❓ **सवाल {idx+1}/{len(quiz)}**\n\n{q['question']}"
    reply_markup = InlineKeyboardMarkup(buttons)
    if message_obj: await message_obj.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else: await update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_ans = int(query.data)
    idx = context.user_data['current_q']
    quiz = context.user_data['quiz']
    correct = quiz[idx]['answer']
    
    res = "✅ सही जवाब!" if user_ans == correct else f"❌ गलत! सही: {quiz[idx]['options'][correct]}"
    if user_ans == correct: context.user_data['score'] += 1
    
    context.user_data['current_q'] += 1
    if context.user_data['current_q'] < len(quiz):
        await query.message.edit_text(f"{res}\n\nअगला सवाल आ रहा है...")
        await asyncio.sleep(1.5)
        await show_question(update, context)
    else:
        await query.message.edit_text(f"🏆 क्विज़ पूरा! स्कोर: {context.user_data['score']}/{len(quiz)}\n\nफिर से: /test")

async def run_bot():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("test", start_test))
    app.add_handler(CallbackQueryHandler(handle_answer))
    async with app:
        await app.initialize()
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        while True: await asyncio.sleep(3600)

if __name__ == '__main__':
    threading.Thread(target=lambda: HTTPServer(("0.0.0.0", int(os.environ.get("PORT", 10000))), HealthCheckHandler).serve_forever(), daemon=True).start()
    asyncio.run(run_bot())
