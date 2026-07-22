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

# ग्लोबल मेमोरी (सवालों के लिए)
DB_CACHE = {}

def sync_db():
    """GitHub से बिना किसी देरी के ताज़ा डेटा लोड करने के लिए"""
    global DB_CACHE
    try:
        # '?t=' की मदद से GitHub Cache को बायपास किया गया है ताकि तुरंत अपडेट मिले
        r = requests.get(f"{GITHUB_URL}?t={int(time.time())}", timeout=20)
        if r.status_code == 200:
            DB_CACHE = r.json()
            logger.info(f"सिंक सफल: {len(DB_CACHE)} टॉपिक्स मिले।")
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
    total = len(qs)

    if idx >= total:
        score = ud.get('score', 0)
        await context.bot.send_message(chat_id, f"🎊 **रिवीजन संपन्न!**\n\n📊 आपका स्कोर: `{score}/{total}` सही\n\nनया टॉपिक चुनने के लिए /start दबाएँ।")
        ud['busy'] = False
        return

    q = qs[idx]
    try:
        await context.bot.send_poll(
            chat_id=chat_id,
            question=f"✨ ({idx+1}/{total}) {random.choice(q['variations'])}",
            options=q['options'],
            type=Poll.QUIZ,
            correct_option_id=q['answer'],
            is_anonymous=False,
            explanation="सही उत्तर आपकी मेहनत का परिणाम है! 📚"
        )
        # पोल ID को ट्रैक करना ताकि आंसर हैंडल हो सके
        # नोट: हम यहाँ poll_id स्टोर नहीं कर रहे क्योंकि PollAnswerHandler user_id से जुड़ा है
        ud['idx'] = idx + 1
    except Exception as e:
        logger.error(f"Poll Error: {e}")

# 4. हैंडलर्स
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    context.user_data.clear()
    
    # अगर पहली बार चल रहा है तो सिंक करें
    if not DB_CACHE: sync_db()

    icons = ["🔴", "🔵", "🟢", "🟡", "🟣", "💎", "🔥", "🌈"]
    # बटन बनाना (DB_CACHE की Keys से)
    keyboard = [[InlineKeyboardButton(f"{random.choice(icons)} {t}", callback_data=t)] for t in DB_CACHE.keys()]
    
    if not keyboard:
        await update.message.reply_text("❌ अभी कोई टॉपिक उपलब्ध नहीं है।")
        return

    await update.message.reply_text("🎯 **अपना टॉपिक चुनें और रिवीजन शुरू करें:**", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    
    topic_name = query.data
    # पूरे टॉपिक का डेटा निकालें (चाहे कितने भी सवाल हों)
    topic_qs = list(DB_CACHE.get(topic_name, []))
    
    if not topic_qs:
        await query.message.reply_text("❌ इस टॉपिक में सवाल नहीं मिले।")
        return

    # सारे सवालों को रैंडम क्रम में सेट करें
    random.shuffle(topic_qs)
    
    # यूजर डेटा में पूरे सवाल (Unlimited) डालना
    context.user_data.update({
        'qs': topic_qs, 
        'idx': 0, 
        'score': 0, 
        'busy': True,
        'current_topic': topic_name
    })
    
    await query.delete_message()
    await send_q(context, chat_id)

async def handle_ans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ans = update.poll_answer
    user_id = ans.user.id
    ud = context.application.user_data.get(user_id)
    
    if ud and ud.get('busy'):
        idx = ud['idx'] - 1
        # चेक करें कि यूजर ने सही ऑप्शन चुना है या नहीं
        if ans.option_ids[0] == ud['qs'][idx]['answer']:
            ud['score'] += 1
        
        # छोटे से अंतराल के बाद अगला सवाल
        await asyncio.sleep(0.5)
        await send_q(context, user_id)

async def refresh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """GitHub से तुरंत नया डेटा लोड करने के लिए"""
    msg = await update.message.reply_text("⏳ डेटा सिंक हो रहा है...")
    if sync_db():
        await msg.edit_text(f"✅ सफलता! अब कुल {len(DB_CACHE)} टॉपिक्स और हज़ारों सवाल तैयार हैं।")
    else:
        await msg.edit_text("❌ सिंक फेल हो गया। कृपया GitHub लिंक चेक करें।")

# 5. MAIN (Webhook Mode)
def main():
    # स्टार्ट होते ही सबसे पहले डेटा लोड करें
    sync_db()

    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("refresh", refresh))
    application.add_handler(CallbackQueryHandler(handle_topic))
    application.add_handler(PollAnswerHandler(handle_ans))

    port = int(os.environ.get("PORT", 10000))
    
    # Conflict रोकने के लिए Webhook + drop_pending_updates
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=TOKEN,
        webhook_url=WEBHOOK_URL,
        drop_pending_updates=True 
    )

if __name__ == '__main__':
    main()
