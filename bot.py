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

# --- 3. फाइल मैनेजमेंट ---

def load_json(filename):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            try: return json.load(f)
            except: return []
    return []

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# --- 4. AI से सवाल बनवाकर बैंक में डालना ---

async def add_to_bank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """कमांड: /gen - AI से 10 नए सवाल बनवाकर बैंक में जोड़ता है"""
    msg = await update.message.reply_text("⏳ AI आपके Facts से 10 नए सवाल बना रहा है... कृपया रुकें।")
    
    facts = str(load_json("facts.json"))
    
    # अलग-अलग भाषा और स्टाइल के लिए निर्देश
    styles = [
        "कठिन और उलझाने वाली हिंदी", 
        "सरल और आसान भाषा", 
        "प्रतियोगी परीक्षा (UPSC/SSC) लेवल", 
        "मज़ेदार और रोचक तरीका"
    ]
    chosen_style = random.choice(styles)

    prompt = f"""
    तथ्य: {facts}
    निर्देश: इन तथ्यों से 10 नए MCQs बनाओ। 
    भाषा शैली: {chosen_style}।
    नियम: हर बार अलग शब्दों का प्रयोग करें। आउटपुट सिर्फ शुद्ध JSON Array हो।
    Format: [{{"question": "..", "options": ["A", "B", "C", "D"], "answer": 0}}]
    """

    try:
        response = ai_client.models.generate_content(model='gemini-1.5-flash', contents=prompt)
        text = response.text.replace("```json", "").replace("```", "").strip()
        match = re.search(r'\[.*\]', text, re.DOTALL)
        
        if match:
            new_qs = json.loads(match.group())
            current_bank = load_json("quiz_bank.json")
            save_json("quiz_bank.json", current_bank + new_qs)
            await msg.edit_text(f"✅ सफलता! {len(new_qs)} नए सवाल '{chosen_style}' में बैंक में जोड़ दिए गए।\nकुल सवाल: {len(current_bank) + len(new_qs)}")
        else:
            await msg.edit_text("❌ AI ने सही फॉर्मेट में जवाब नहीं दिया। दोबारा कोशिश करें।")
    except Exception as e:
        await msg.edit_text(f"❌ एरर: AI अभी बिजी है।")

# --- 5. बैंक से सवाल निकालकर टेस्ट शुरू करना ---

is_bot_busy = False

async def start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """कमांड: /start - बैंक से तुरंत 20 सवाल निकालता है"""
    global is_bot_busy
    if is_bot_busy: return

    bank = load_json("quiz_bank.json")
    
    if len(bank) < 10:
        await update.message.reply_text("⚠️ बैंक में सवाल कम हैं! पहले /gen चलाकर सवाल भरें।")
        return

    is_bot_busy = True
    
    # अगर बैंक में 20 से कम हैं, तो जितने हैं उतने उठा लो
    count = 20 if len(bank) >= 20 else len(bank)
    quiz_data = random.sample(bank, count)
    
    full_text = f"🚀 **GK QUIZ ({count} QUESTIONS)** 🚀\n\n"
    for i, q in enumerate(quiz_data, 1):
        q_text = f"❓ **Q{i}:** {q['question']}\n"
        opts = ["A", "B", "C", "D"]
        for idx, opt in enumerate(q['options']):
            q_text += f"   {opts[idx]}) {opt}\n"
        
        ans = opts[q['answer']]
        q_text += f"✅ **Ans:** {ans}\n\n"

        if len(full_text) + len(q_text) > 3800:
            await update.message.reply_text(full_text, parse_mode='Markdown')
            full_text = ""
        full_text += q_text

    if full_text:
        await update.message.reply_text(full_text, parse_mode='Markdown')

    await update.message.reply_text("🏆 टेस्ट पूरा हुआ! नए रैंडम सवालों के लिए फिर से /start भेजें।")
    is_bot_busy = False

async def reset_bank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """कमांड: /reset - बैंक को पूरी तरह खाली कर देता है"""
    save_json("quiz_bank.json", [])
    await update.message.reply_text("🗑️ बैंक खाली कर दिया गया है। अब नए सवाल /gen से बनायें।")

async def ignore_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_bot_busy: return

async def run_bot():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_quiz))
    app.add_handler(CommandHandler("gen", add_to_bank))
    app.add_handler(CommandHandler("reset", reset_bank))
    app.add_handler(MessageHandler(filters.ALL, ignore_all), group=1)
    
    async with app:
        await app.initialize()
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        while True: await asyncio.sleep(3600)

if __name__ == '__main__':
    try: asyncio.run(run_bot())
    except: exit(1)
