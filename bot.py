import os
import json
import random
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Poll
from telegram.ext import (
    Application, 
    CommandHandler, 
    CallbackQueryHandler, 
    PollAnswerHandler, 
    ContextTypes, 
    MessageHandler, 
    filters
)

# 1. लॉगिंग
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 2. टोकन (Environment Variable से उठाएगा)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

# --- 3. डेटाबेस लोड करने का फंक्शन ---
def load_database():
    try:
        if os.path.exists("quiz_database.json"):
            with open("quiz_database.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                return data
        else:
            logger.error("Error: quiz_database.json file not found!")
            return {}
    except Exception as e:
        logger.error(f"JSON Error: {e}")
        return {}

# --- 4. अगला सवाल (Poll) भेजने का फंक्शन ---
async def send_next_question(context: ContextTypes.DEFAULT_TYPE, chat_id):
    user_data = context.user_data
    quiz_set = user_data.get('quiz_set', [])
    index = user_data.get('current_index', 0)

    # अगर सारे सवाल खत्म हो गए
    if index >= len(quiz_set):
        await context.bot.send_message(chat_id=chat_id, text="🏆 **बधाई हो! आपका रिवीजन पूरा हुआ।**\n\nनया टॉपिक चुनने के लिए फिर से /start दबाएँ।")
        user_data['is_busy'] = False
        return

    q = quiz_set[index]
    # Variations में से रैंडम एक भाषा चुनना
    question_text = random.choice(q['variations'])
    options = q['options']
    correct_index = q['answer']

    try:
        message = await context.bot.send_poll(
            chat_id=chat_id,
            question=f"[{index+1}/{len(quiz_set)}] {question_text}",
            options=options,
            type=Poll.QUIZ,
            correct_option_id=correct_index,
            is_anonymous=False, # ताकि जवाब ट्रैक हो सके
            explanation="रिवीजन जारी रखें!"
        )
        # ट्रैक करने के लिए
        user_data['current_poll_id'] = message.poll.id
        user_data['current_index'] = index + 1
    except Exception as e:
        logger.error(f"Poll Send Error: {e}")
        user_data['is_busy'] = False

# --- 5. बॉट कमांड्स और इवेंट्स ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start दबाते ही सब कुछ रिसेट होगा और मेनू आएगा"""
    # रिसेट यूजर डेटा
    context.user_data['is_busy'] = False
    context.user_data['quiz_set'] = []
    context.user_data['current_index'] = 0

    db = load_database()
    if not db:
        await update.message.reply_text("❌ डेटाबेस फाइल (quiz_database.json) नहीं मिली या खाली है।")
        return

    # टॉपिक के बटन्स बनाना
    keyboard = []
    for topic in db.keys():
        keyboard.append([InlineKeyboardButton(topic, callback_data=topic)])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👋 **राम राम भाई! स्वागत है रिवीजन में।**\n\nकिस टॉपिक का टेस्ट देना चाहते हैं? नीचे से चुनें:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_topic_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """बटन दबाने पर यह चलता है"""
    query = update.callback_query
    topic_name = query.data
    
    # बटन का स्पिनर (loading icon) बंद करना
    await query.answer()

    db = load_database()
    all_qs = db.get(topic_name, [])

    if not all_qs:
        await query.edit_message_text(f"❌ '{topic_name}' में कोई सवाल नहीं मिले।")
        return

    # 20 रैंडम सवाल सेट करना
    sample_size = min(len(all_qs), 20)
    selected_qs = random.sample(all_qs, sample_size)

    context.user_data['quiz_set'] = selected_qs
    context.user_data['current_index'] = 0
    context.user_data['is_busy'] = True
    context.user_data['chat_id'] = query.message.chat_id

    # टॉपिक चुनने वाला मैसेज डिलीट करना और क्विज़ शुरू करना
    try:
        await query.delete_message()
    except:
        pass

    await context.bot.send_message(chat_id=query.message.chat_id, text=f"🏁 **{topic_name}** शुरू हो रहा है...")
    
    # पहला सवाल भेजें
    await send_next_question(context, query.message.chat_id)

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """जैसे ही पोल पर जवाब दिया जाए"""
    poll_answer = update.poll_answer
    user_data = context.user_data

    # चेक करें कि क्या क्विज़ चालू है और ये वही पोल है
    if user_data.get('is_busy') and user_data.get('current_poll_id') == poll_answer.poll_id:
        # पटाखे फूटने का टाइम (0.6 सेकंड)
        await asyncio.sleep(0.6)
        # अगला सवाल
        await send_next_question(context, user_data.get('chat_id'))

async def run_bot():
    if not TELEGRAM_BOT_TOKEN:
        print("❌ Error: TELEGRAM_BOT_TOKEN environment variable not set!")
        return

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # हैंडलर्स जोड़ना
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_topic_selection))
    app.add_handler(PollAnswerHandler(handle_answer))

    print("✅ Bot is running WITHOUT AI...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    
    while True:
        await asyncio.sleep(3600)

if __name__ == '__main__':
    try:
        asyncio.run(run_bot())
    except Exception as e:
        logger.error(f"Fatal Error: {e}")
