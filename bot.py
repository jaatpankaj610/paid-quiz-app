import os
import json
import random
import logging
import asyncio
import threading
import requests
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Poll
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, PollAnswerHandler, ContextTypes

# 1. लॉगिंग
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# 2. टोकन और डाटा लिंक
TOKEN = "7467353478:AAH9kSAgaEbz3oXjFMbY6w53bqoq4Z2Ssyk"
GITHUB_URL = "https://raw.githubusercontent.com/jaatpankaj610/paid-quiz-app/main/quiz_database.json"

# --- 3. HEALTH SERVER (Render को जगाये रखने के लिए) ---
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is Running 24/7!")
    def log_message(self, format, *args): return

def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    httpd = HTTPServer(("0.0.0.0", port), HealthHandler)
    httpd.serve_forever()

# --- 4. डाटाबेस लोडर ---
def load_db():
    try:
        r = requests.get(GITHUB_URL)
        return r.json()
    except Exception as e:
        logger.error(f"DB Load Error: {e}")
        return {}

# --- 5. क्विज़ लॉजिक ---
async def send_q(context, chat_id):
    ud = context.user_data
    qs = ud.get('qs', [])
    idx = ud.get('idx', 0)

    if idx >= len(qs):
        score = ud.get('score', 0)
        await context.bot.send_message(chat_id, f"🎊 **रिवीजन संपन्न!**\n\n📊 स्कोर: `{score}/{len(qs)}` सही\n\nनया टॉपिक चुनने के लिए /start दबाएँ।")
        ud['busy'] = False
        return

    q = qs[idx]
    msg = await context.bot.send_poll(
        chat_id=chat_id,
        question=f"✨ ({idx+1}/{len(qs)}) {random.choice(q['variations'])}",
        options=q['options'],
        type=Poll.QUIZ,
        correct_option_id=q['answer'],
        is_anonymous=False,
        explanation="मेहनत का फल मीठा होता है! 📚"
    )
    ud['poll_id'] = msg.poll.id
    ud['idx'] = idx + 1

# --- 6. हैंडलर्स ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    db = load_db()
    if not db:
        await update.message.reply_text("❌ डेटाबेस फाइल नहीं मिली!")
        return

    # रंगीन बटन (Emoji based)
    icons = ["🔴", "🔵", "🟢", "🟡", "🟣", "💎", "🔥", "🌈"]
    keyboard = []
    for t in db.keys():
        keyboard.append([InlineKeyboardButton(f"{random.choice(icons)} {t}", callback_data=t)])
    
    await update.message.reply_text("🎯 **रिवीजन शुरू करें! अपना टॉपिक चुनें:**", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    db = load_db()
    topic_data = db.get(query.data, [])
    
    # रैंडम 20 सवाल चुनना
    qs = random.sample(topic_data, min(len(topic_data), 20))
    context.user_data.update({'qs': qs, 'idx': 0, 'score': 0, 'busy': True, 'chat_id': query.message.chat_id})
    
    await query.delete_message()
    await send_q(context, query.message.chat_id)

async def handle_ans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ans = update.poll_answer
    ud = context.user_data
    if ud.get('busy') and ud.get('poll_id') == ans.poll_id:
        idx = ud['idx'] - 1
        if ans.option_ids[0] == ud['qs'][idx]['answer']:
            ud['score'] += 1
        await asyncio.sleep(1.2) # पटाखे फूटने का समय
        await send_q(context, ud.get('chat_id') or update.effective_user.id)

# --- 7. MAIN ---
def main():
    # Health Server को बैकग्राउंड में चलायें
    threading.Thread(target=run_health_server, daemon=True).start()

    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_topic))
    app.add_handler(PollAnswerHandler(handle_ans))

    print("Bot is starting on Render...")
    # drop_pending_updates=True पुराने झगड़ों (Conflict) को खत्म कर देगा
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
