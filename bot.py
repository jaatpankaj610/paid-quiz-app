import os
import json
import random
import logging
import asyncio
import requests
import time
from telegram import Update, Poll, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, PollAnswerHandler, ContextTypes

# 1. लॉगिंग
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# 2. कॉन्फ़िगरेशन
TOKEN = "7908449655:AAGVk4HYN98rZkJoeTtPIdHsHdmnrlhPG9w"
GITHUB_URL = "https://raw.githubusercontent.com/jaatpankaj610/paid-quiz-app/main/quiz_database.json"
WEBHOOK_URL = f"https://bankerbot-mdzw.onrender.com/{TOKEN}"

# ग्लोबल मेमोरी
DB_CACHE = {}
LAST_SYNC_TIME = 0

def sync_db(force=False):
    """GitHub से ताज़ा डेटा लाने के लिए। force=True करने पर तुरंत लाएगा।"""
    global DB_CACHE, LAST_SYNC_TIME
    # अगर 10 मिनट बीत चुके हैं या जबरदस्ती (force) बुलाया गया है
    if force or (time.time() - LAST_SYNC_TIME > 600):
        try:
            # ?cb= टाइमस्टैम्प ताकि GitHub पुरानी फाइल न भेजे
            r = requests.get(f"{GITHUB_URL}?cb={int(time.time())}", timeout=15)
            if r.status_code == 200:
                DB_CACHE = r.json()
                LAST_SYNC_TIME = time.time()
                logger.info(f"Database Updated: {len(DB_CACHE)} topics found.")
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
    total = len(qs) # यह ऑटोमैटिक आपकी फाइल के सारे सवाल गिनेगा

    if idx >= total:
        score = ud.get('score', 0)
        await context.bot.send_message(chat_id, f"🎊 **रिवीजन संपन्न!**\n\n📊 स्कोर: `{score}/{total}` सही\n\nनया टॉपिक चुनने के लिए /start दबाएँ।")
        ud['busy'] = False
        return

    q = qs[idx]
    try:
        # यहाँ Counter (1/Total) अब आपकी फाइल के हिसाब से चलेगा
        await context.bot.send_poll(
            chat_id=chat_id,
            question=f"✨ ({idx+1}/{total}) {random.choice(q['variations'])}",
            options=q['options'],
            type=Poll.QUIZ,
            correct_option_id=q['answer'],
            is_anonymous=False,
            explanation="मेहनत का फल मीठा होता है! 📚"
        )
        ud['idx'] = idx + 1
    except Exception as e:
        logger.error(f"Poll Error: {e}")

# 4. हैंडलर्स
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    context.user_data.clear()
    
    # स्टार्ट दबाते ही चेक करेगा कि डेटा नया है या नहीं
    sync_db() 

    if not DB_CACHE:
        await update.message.reply_text("❌ डेटाबेस लोड हो रहा है, कृपया 5 सेकंड बाद दोबारा /start दबाएँ।")
        sync_db(force=True)
        return

    icons = ["🔴", "🔵", "🟢", "🟡", "🟣", "💎", "🔥", "🌈"]
    keyboard = [[InlineKeyboardButton(f"{random.choice(icons)} {t}", callback_data=t)] for t in DB_CACHE.keys()]
    
    await update.message.reply_text("🎯 **रिवीजन शुरू करें! अपना टॉपिक चुनें:**", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    
    topic_qs = list(DB_CACHE.get(query.data, []))
    if not topic_qs:
        await query.message.reply_text("❌ सवाल नहीं मिले।")
        return

    random.shuffle(topic_qs) # सारे सवालों को शफल करें
    
    # यहाँ 'qs' में अब 20 नहीं, बल्कि टॉपिक के ALL (सारे) सवाल होंगे
    context.user_data.update({
        'qs': topic_qs, 
        'idx': 0, 
        'score': 0, 
        'busy': True
    })
    
    await query.delete_message()
    await context.bot.send_message(chat_id, f"📝 इस टॉपिक में कुल {len(topic_qs)} सवाल मिले हैं।")
    await send_q(context, chat_id)

async def handle_ans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ans = update.poll_answer
    user_id = ans.user.id
    ud = context.application.user_data.get(user_id)
    
    if ud and ud.get('busy'):
        idx = ud['idx'] - 1
        if ans.option_ids[0] == ud['qs'][idx]['answer']:
            ud['score'] += 1
        await asyncio.sleep(0.5)
        await send_q(context, user_id)

async def refresh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """अगर तुरंत अपडेट चाहिए तो यह कमांड चलायें"""
    if sync_db(force=True):
        total_q = sum(len(v) for v in DB_CACHE.values())
        await update.message.reply_text(f"✅ डेटाबेस सिंक हो गया!\n📂 टॉपिक्स: {len(DB_CACHE)}\n📚 कुल सवाल: {total_q}")
    else:
        await update.message.reply_text("❌ सिंक फेल हो गया।")

# 5. MAIN
def main():
    sync_db(force=True)
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("refresh", refresh))
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
