import os
import json
import random
import logging
import asyncio
import requests
from telegram import Update, Poll, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, PollAnswerHandler, ContextTypes

# 1. लॉगिंग सेटअप
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# 2. कॉन्फ़िगरेशन
TOKEN = "7467353478:AAH9kSAgaEbz3oXjFMbY6w53bqoq4Z2Ssyk"
GITHUB_URL = "https://raw.githubusercontent.com/jaatpankaj610/paid-quiz-app/main/quiz_database.json"
WEBHOOK_URL = f"https://bankerbot-mdzw.onrender.com/{TOKEN}"

# 3. डाटाबेस लोडर
def load_db():
    try:
        r = requests.get(GITHUB_URL)
        return r.json()
    except Exception as e:
        logger.error(f"DB Load Error: {e}")
        return {}

# 4. क्विज़ लॉजिक
async def send_q(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    ud = context.user_data
    if not ud or 'qs' not in ud:
        return

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
        logger.error(f"Error sending poll: {e}")

# 5. हैंडलर्स
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 'mappingproxy' एरर को ठीक करने के लिए context.user_data का उपयोग
    context.user_data.clear()
    context.user_data.update({'busy': False, 'score': 0, 'idx': 0})
    
    db = load_db()
    if not db:
        await update.message.reply_text("❌ डेटाबेस लोड नहीं हो सका!")
        return

    icons = ["🔴", "🔵", "🟢", "🟡", "🟣", "💎", "🔥", "🌈"]
    keyboard = [[InlineKeyboardButton(f"{random.choice(icons)} {t}", callback_data=t)] for t in db.keys()]
    
    await update.message.reply_text("🎯 **रिवीजन शुरू करें! अपना टॉपिक चुनें:**", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    
    db = load_db()
    topic_data = db.get(query.data, [])
    if not topic_data: 
        return

    qs = random.sample(topic_data, min(len(topic_data), 20))
    
    # डेटा अपडेट करें
    context.user_data.update({
        'qs': qs, 
        'idx': 0, 
        'score': 0, 
        'busy': True, 
        'chat_id': chat_id
    })
    
    await query.delete_message()
    await send_q(context, chat_id)

async def handle_ans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ans = update.poll_answer
    ud = context.user_data
    
    # चेक करें कि क्या यह सही पोल है
    if ud and ud.get('busy') and ud.get('poll_id') == ans.poll_id:
        idx = ud['idx'] - 1
        if ans.option_ids[0] == ud['qs'][idx]['answer']:
            ud['score'] += 1
        
        await asyncio.sleep(1)
        await send_q(context, update.effective_user.id)

# 6. MAIN
def main():
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_topic))
    application.add_handler(PollAnswerHandler(handle_ans))

    port = int(os.environ.get("PORT", 10000))

    # Webhook का उपयोग Conflict खत्म करने के लिए
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=TOKEN,
        webhook_url=WEBHOOK_URL,
        drop_pending_updates=True
    )

if __name__ == '__main__':
    main()
