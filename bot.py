import os
import json
import random
import logging
import asyncio
import re
from google import genai
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

# 1. लॉगिंग
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 2. क्रेडेंशियल्स
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

try:
    ai_client = genai.Client(api_key=GEMINI_API_KEY)
except Exception as e:
    logger.error(f"AI Setup Error: {e}")

# --- 3. बैकएंड लॉजिक (सवाल जमा करना और निकालना) ---

def load_from_json(filename):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_to_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

async def generate_questions_to_bank():
    """AI से सवाल बनवाकर बैंक में सेव करना"""
    try:
        facts_data = load_from_json("facts.json")
        prompt = f"""
        तथ्यों का उपयोग करके 50 अलग-अलग प्रकार के GK MCQs तैयार करें।
        तथ्य: {str(facts_data)[:3000]}
        नियम:
        - भाषा: हिंदी (सरल और कठिन दोनों का मिश्रण)।
        - फॉर्मेट: केवल शुद्ध JSON Array।
        - Format: [{{"question": "..", "options": ["A", "B", "C", "D"], "answer": 0}}]
        """
        response = ai_client.models.generate_content(model='gemini-1.5-flash', contents=prompt)
        match = re.search(r'\[.*\]', response.text, re.DOTALL)
        if match:
            new_questions = json.loads(match.group())
            # पुराने सवालों के साथ जोड़ना
            old_bank = load_from_json("quiz_bank.json")
            combined = old_bank + new_questions
            save_to_json("quiz_bank.json", combined)
            return len(new_questions)
    except Exception as e:
        logger.error(f"Bank Update Error: {e}")
    return 0

# --- 4. BOT HANDLERS ---

is_bot_busy = False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_bot_busy
    if is_bot_busy: return

    is_bot_busy = True
    
    # बैंक से सवाल उठाना
    bank = load_from_json("quiz_bank.json")
    
    if len(bank) < 20:
        await update.message.reply_text("⚠️ बैंक में सवाल कम हैं! पहले /update_bank कमांड चलायें (सिर्फ एडमिन)।")
        is_bot_busy = False
        return

    # रैंडम 20 सवाल चुनना
    quiz_data = random.sample(bank, 20)
    
    full_text = "🚀 **INSTANT GK QUIZ (20 QUESTIONS)** 🚀\n\n"
    
    for i, q in enumerate(quiz_data, 1):
        q_text = f"❓ **सवाल {i}:** {q['question']}\n"
        opts = ["A", "B", "C", "D"]
        for idx, opt in enumerate(q['options']):
            q_text += f"   {opts[idx]}) {opt}\n"
        
        correct_opt = opts[q['answer']]
        q_text += f"✅ **उत्तर:** {correct_opt}\n\n"

        if len(full_text) + len(q_text) > 3900:
            await update.message.reply_text(full_text, parse_mode='Markdown')
            full_text = ""
        full_text += q_text

    if full_text:
        await update.message.reply_text(full_text, parse_mode='Markdown')

    await update.message.reply_text("🏆 **टेस्ट पूरा हुआ!**\n\nअगले नए 20 सवालों के लिए /start भेजें।")
    is_bot_busy = False

async def update_bank_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """यह कमांड आप (Admin) चलाएंगे ताकि बैंक में नए सवाल भर जाएं"""
    await update.message.reply_text("⏳ AI आपके facts.json से 50 नए सवाल बनाकर बैंक में डाल रहा है... कृपया रुकें।")
    count = await generate_questions_to_bank()
    if count > 0:
        await update.message.reply_text(f"✅ सफलता! बैंक में {count} नए सवाल जोड़ दिए गए हैं।")
    else:
        await update.message.reply_text("❌ एरर! AI सवाल नहीं बना पाया।")

async def ignore_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_bot_busy: return

async def run_bot():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # यूजर के लिए कमांड
    app.add_handler(CommandHandler("start", start))
    
    # आपके लिए बैंक अपडेट करने की कमांड
    app.add_handler(CommandHandler("update_bank", update_bank_command))
    
    # बाकी सब इग्नोर
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
        exit(1)
