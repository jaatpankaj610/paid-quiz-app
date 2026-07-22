import os
import json
import random
import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

# 1. लॉगिंग
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 2. टोकन
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

# --- 3. फाइल से सवाल उठाना ---

def load_questions():
    """GitHub वाली questions.json फाइल लोड करना"""
    try:
        if os.path.exists("questions.json"):
            with open("questions.json", "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading questions.json: {e}")
    return []

# --- 4. बोट हैंडलर ---

is_bot_busy = False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_bot_busy
    
    # अगर एक बार टेस्ट शुरू हो गया, तो दूसरी कोई कमांड न सुने
    if is_bot_busy:
        return 

    is_bot_busy = True
    
    all_qs = load_questions()
    
    if not all_qs:
        await update.message.reply_text("❌ 'questions.json' फाइल नहीं मिली या खाली है।")
        is_bot_busy = False
        return

    await update.message.reply_text("🔎 आपके लिए 20 रैंडम सवाल तैयार किए जा रहे हैं...")

    # 20 रैंडम सवाल चुनना (अगर बैंक में 20 से कम हैं तो सब चुन लेना)
    sample_size = min(len(all_qs), 20)
    selected_qs = random.sample(all_qs, sample_size)

    full_quiz_text = f"📝 **GK QUIZ - {sample_size} QUESTIONS**\n\n"
    
    for i, q in enumerate(selected_qs, 1):
        # मुख्य जादू: variations में से कोई एक रैंडम भाषा चुनना
        question_text = random.choice(q['variations'])
        
        q_block = f"❓ **सवाल {i}:** {question_text}\n"
        opts_labels = ["A", "B", "C", "D"]
        for idx, opt in enumerate(q['options']):
            q_block += f"   {opts_labels[idx]}) {opt}\n"
        
        correct_ans = opts_labels[q['answer']]
        q_block += f"✅ **उत्तर:** {correct_ans}\n\n"

        # टेलीग्राम की 4096 लिमिट चेक करना
        if len(full_quiz_text) + len(q_block) > 3900:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=full_quiz_text, parse_mode='Markdown')
            full_quiz_text = ""
        
        full_text_to_add = q_block
        full_quiz_text += full_text_to_add

    if full_quiz_text:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=full_quiz_text, parse_mode='Markdown')

    await context.bot.send_message(
        chat_id=update.effective_chat.id, 
        text="🏆 **टेस्ट पूरा हुआ!**\n\nभाषा बदल-बदल कर नए टेस्ट के लिए फिर से /start भेजें।"
    )
    
    is_bot_busy = False # अब बोट दोबारा फ्री है

async def ignore_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """जब बोट टेस्ट दे रहा हो, तो बाकी सब इग्नोर करे"""
    if is_bot_busy:
        return

async def run_bot():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    
    # सब कुछ इग्नोर करने के लिए
    app.add_handler(MessageHandler(filters.ALL, ignore_all), group=1)

    async with app:
        await app.initialize()
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        while True: await asyncio.sleep(3600)

if __name__ == '__main__':
    try:
        asyncio.run(run_bot())
    except:
        pass
