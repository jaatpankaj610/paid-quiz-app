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

# 1. लॉगिंग (गलतियों को पकड़ने के लिए)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 2. टोकन (सुनिश्चित करें कि आपने इसे Environment Variables में सेट किया है)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

# --- 3. डेटाबेस लोड करना ---
def load_database():
    if os.path.exists("quiz_database.json"):
        try:
            with open("quiz_database.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"JSON Error: {e}")
            return {}
    return {}

# --- 4. अगला सवाल भेजने का फंक्शन ---
async def send_next_question(context: ContextTypes.DEFAULT_TYPE, chat_id):
    user_data = context.user_data
    quiz_set = user_data.get('quiz_set', [])
    index = user_data.get('current_index', 0)

    if index >= len(quiz_set):
        await context.bot.send_message(chat_id=chat_id, text="🏆 **क्विज़ पूरा हुआ!**\n\nनया टॉपिक शुरू करने के लिए दोबारा /start दबाएँ।")
        user_data['is_busy'] = False
        return

    q = quiz_set[index]
    # Variations में से रैंडम भाषा चुनना
    question_text = random.choice(q['variations'])
    options = q['options']
    correct_index = q['answer']

    # टेलीग्राम क्विज़ पोल भेजना
    try:
        message = await context.bot.send_poll(
            chat_id=chat_id,
            question=f"[{index+1}/{len(quiz_set)}] {question_text}",
            options=options,
            type=Poll.QUIZ,
            correct_option_id=correct_index,
            is_anonymous=False,
            explanation="कोशिश जारी रखें!"
        )
        # ट्रैक करने के लिए स्टोर करना
        user_data['current_poll_id'] = message.poll.id
        user_data['current_index'] = index + 1
    except Exception as e:
        logger.error(f"Poll Error: {e}")
        await context.bot.send_message(chat_id=chat_id, text="❌ पोल भेजने में दिक्कत हुई।")

# --- 5. बॉट हैंडलर्स ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # फोर्स रिसेट - ताकि /start हमेशा काम करे
    context.user_data['is_busy'] = False
    context.user_data['quiz_set'] = []
    context.user_data['current_index'] = 0

    db = load_database()
    if not db:
        await update.message.reply_text("❌ 'quiz_database.json' फाइल नहीं मिली या खराब है।")
        return

    # टॉपिक्स के बटन बनाना
    keyboard = [[InlineKeyboardButton(topic, callback_data=topic)] for topic in db.keys()]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👋 **राम राम भाई!**\n\nकिस टॉपिक का टेस्ट देना चाहते हैं? नीचे से चुनें:", 
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_topic_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    topic_name = query.data
    await query.answer()

    db = load_database()
    all_qs = db.get(topic_name, [])

    if not all_qs:
        await query.edit_message_text("❌ इस टॉपिक में कोई सवाल नहीं हैं।")
        return

    # 20 रैंडम सवाल सेट करना
    sample_size = min(len(all_qs), 20)
    selected_qs = random.sample(all_qs, sample_size)

    context.user_data['quiz_set'] = selected_qs
    context.user_data['current_index'] = 0
    context.user_data['is_busy'] = True
    context.user_data['chat_id'] = query.message.chat_id

    await query.delete_message()
    await context.bot.send_message(chat_id=query.message.chat_id, text=f"🏁 **{topic_name}** शुरू हो रहा है...")
    
    # पहला सवाल भेजें
    await send_next_question(context, query.message.chat_id)

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    poll_answer = update.poll_answer
    user_data = context.user_data

    # चेक करें कि क्या यह उसी पोल का जवाब है
    if user_data.get('is_busy') and user_data.get('current_poll_id') == poll_answer.poll_id:
        # पटाखे फूटने का समय दें (0.6 सेकंड)
        await asyncio.sleep(0.6)
        await send_next_question(context, user_data.get('chat_id'))

async def run_bot():
    if not TELEGRAM_BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not found!")
        return

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # कमांड्स
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_topic_selection))
    app.add_handler(PollAnswerHandler(handle_answer))

    print("Bot is running...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    
    # बॉट को चालू रखने के लिए
    while True:
        await asyncio.sleep(3600)

if __name__ == '__main__':
    try:
        asyncio.run(run_bot())
    except (KeyboardInterrupt, SystemExit):
        pass
    except Exception as e:
        logger.error(f"Fatal Error: {e}")
