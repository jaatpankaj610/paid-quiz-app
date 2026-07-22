import os
import json
import random
import logging
import asyncio
import requests
import time
from telegram import Update, Poll, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, PollAnswerHandler, ContextTypes

# 1. लॉगिंग सेटअप
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# 2. कॉन्फ़िगरेशन
TOKEN = "7908449655:AAGVk4HYN98rZkJoeTtPIdHsHdmnrlhPG9w"
GITHUB_URL = "https://raw.githubusercontent.com/jaatpankaj610/paid-quiz-app/main/quiz_database.json"
WEBHOOK_URL = f"https://bankerbot-mdzw.onrender.com/{TOKEN}"

# --- ग्लोबल मेमोरी (सवालों को लोड करने के लिए) ---
DB_CACHE = {}

def sync_db():
    """GitHub से डेटा खींचकर याददाश्त (Memory) में डालता है"""
    global DB_CACHE
    try:
        r = requests.get(GITHUB_URL, timeout=15)
        if r.status_code == 200:
            DB_CACHE = r.json()
            logger.info(f"डेटाबेस सिंक सफल! {len(DB_CACHE)} टॉपिक्स लोड हुए।")
            return True
    except Exception as e:
        logger.error(f"Sync Error: {e}")
        return False

# 3. क्विज़ लॉजिक
async def send_q(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    ud = context.user_data
    if not ud or 'qs' not in ud: return

    idx = ud.get('idx', 0)
    qs = ud['qs']

    if idx >= len(qs):
        score = ud.get('score', 0)
        await context.bot.send_message(chat_id, f"🎊 **रिवीजन संपन्न!**\n\n📊 स्कोर: `{score}/{len(qs)}` सही\n\nनया टॉपिक चुनने के लिए /start दबाएँ।")
        ud['busy'] = False
        return

    q = qs[idx]
    try:
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
    except Exception as e:
        logger.error(f"Error: {e}")

# 4. हैंडलर्स
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    context.user_data.clear()
    
    # अगर मेमोरी खाली है, तो लोड करें
    if not DB_CACHE:
        sync_db()

    if not DB_CACHE:
        await update.message.reply_text("❌ डेटाबेस लोड नहीं हो सका।")
        return

    icons = ["🔴", "🔵", "🟢", "🟡", "🟣", "💎", "🔥", "🌈"]
    keyboard = [[InlineKeyboardButton(f"{random.choice(icons)} {t}", callback_data=t)] for t in DB_CACHE.keys()]
    
    await update.message.reply_text("🎯 **अपना टॉपिक चुनें:**", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    
    topic_data = DB_CACHE.get(query.data, [])
    if not topic_data: return

    # जितने सवाल PDF में हैं, सब पूछें (Unlimited)
    qs = random.sample(topic_data, len(topic_data))
    
    context.user_data.update({
        'qs': qs, 
        'idx': 0, 
        'score': 0, 
        'busy': True
    })
    
    await query.delete_message()
    await send_q(context, chat_id)

async def handle_ans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ans = update.poll_answer
    ud = context.user_data
    if ud and ud.get('busy') and ud.get('poll_id') == ans.poll_id:
        idx = ud['idx'] - 1
        if ans.option_ids[0] == ud['qs'][idx]['answer']:
            ud['score'] += 1
        await asyncio.sleep(1)
        await send_q(context, update.effective_user.id)

async def refresh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """नया डेटा GitHub से तुरंत खींचने के लिए कमांड"""
    await update.message.reply_text("⏳ नए सवालों को लोड किया जा रहा है...")
    if sync_db():
        await update.message.reply_text(f"✅ सफलता! अब कुल {len(DB_CACHE)} टॉपिक्स उपलब्ध हैं।")
    else:
        await update.message.reply_text("❌ सिंक फेल हो गया।")

# 5. MAIN
def main():
    # शुरुआत में ही एक बार डेटा लोड कर लें
    sync_db()

    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("refresh", refresh)) # नई कमांड
    application.add_handler(CallbackQueryHandler(handle_topic))
    application.add_handler(PollAnswerHandler(handle_ans))

    port = int(os.environ.get("PORT", 10000))
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=TOKEN,
        webhook_url=WEBHOOK_URL,
        drop_pending_updates=True
    )

if __name__ == '__main__':
    main()
