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

# --- 4. AI से छोटे बैच में सवाल मांगना ---

async def fetch_mini_batch(count=5):
    """AI से सिर्फ 5 सवाल मांगना (सबसे सुरक्षित तरीका)"""
    try:
        facts = str(load_json("facts.json"))[:3000]
        prompt = f"""
        Generate {count} GK questions in Hindi based on these facts: {facts}
        Return ONLY a JSON array. 
        Format: [{{"question": "..", "options": ["A", "B", "C", "D"], "answer": 0}}]
        """
        response = ai_client.models.generate_content(model='gemini-1.5-flash', contents=prompt)
        text = response.text.replace("```json", "").replace("```", "").strip()
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception as e:
        logger.error(f"Mini Batch Error: {e}")
    return []

# --- 5. BOT HANDLERS ---

is_bot_busy = False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_bot_busy
    if is_bot_busy: return

    bank = load_json("quiz_bank.json")
    if len(bank) < 20:
        await update.message.reply_text("⚠️ बैंक खाली है! पहले /update_bank चलायें।")
        return

    is_bot_busy = True
    quiz_data = random.sample(bank, 20)
    
    full_text = "🚀 **GK QUIZ (20 QUESTIONS)** 🚀\n\n"
    for i, q in enumerate(quiz_data, 1):
        q_text = f"❓ **Q{i}:** {q['question']}\n"
        opts = ["A", "B", "C", "D"]
        for idx, opt in enumerate(q['options']):
            q_text += f"   {opts[idx]}) {opt}\n"
        q_text += f"✅ **Ans:** {opts[q['answer']]}\n\n"
        
        if len(full_text) + len(q_text) > 3800:
            await update.message.reply_text(full_text, parse_mode='Markdown')
            full_text = ""
        full_text += q_text

    if full_text: await update.message.reply_text(full_text, parse_mode='Markdown')
    await update.message.reply_text("🏆 टेस्ट पूरा हुआ! नए सवालों के लिए /start भेजें।")
    is_bot_busy = False

async def update_bank_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to populate the bank in small steps"""
    msg = await update.message.reply_text("⏳ बैंक अपडेट हो रहा है (4 चरणों में)...")
    
    total_added = 0
    for i in range(1, 5): # 4 बार 5-5 सवाल मांगेगा = कुल 20 सवाल
        await msg.edit_text(f"⏳ चरण {i}/4: AI सवाल बना रहा है...")
        new_qs = await fetch_mini_batch(5)
        if new_qs:
            current_bank = load_json("quiz_bank.json")
            save_json("quiz_bank.json", current_bank + new_qs)
            total_added += len(new_qs)
        await asyncio.sleep(1) # AI को आराम देने के लिए

    await msg.edit_text(f"✅ बैंक अपडेट पूरा! {total_added} नए सवाल जोड़े गए। अब /start चलायें।")

async def ignore_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_bot_busy: return

async def run_bot():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("update_bank", update_bank_command))
    app.add_handler(MessageHandler(filters.ALL, ignore_all), group=1)
    
    async with app:
        await app.initialize()
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        while True: await asyncio.sleep(3600)

if __name__ == '__main__':
    try: asyncio.run(run_bot())
    except: exit(1)
