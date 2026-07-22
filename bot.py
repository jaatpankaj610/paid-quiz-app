import os
import json
import random
import logging
import asyncio
import re
from google import genai
from google.genai import types # सेफ्टी के लिए
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

# --- 4. AI से सवाल मँगाने का सुपर-स्टेबल फंक्शन ---

async def fetch_questions_safe(count=5):
    """AI से सवाल माँगना - 3 बार ऑटो-रिट्राय के साथ"""
    facts = str(load_json("facts.json"))[:2000]
    
    prompt = f"""
    Facts: {facts}
    Task: Create {count} unique GK MCQs in Hindi.
    Rules: Return ONLY a valid JSON array. No text before or after.
    Format: [{{"question": "..", "options": ["A", "B", "C", "D"], "answer": 0}}]
    """

    for attempt in range(3): # 3 बार कोशिश
        try:
            response = ai_client.models.generate_content(
                model='gemini-1.5-flash', 
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.8)
            )
            
            text = response.text.replace("```json", "").replace("```", "").strip()
            match = re.search(r'\[.*\]', text, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception as e:
            logger.warning(f"Attempt {attempt+1} failed: {e}")
            await asyncio.sleep(2) # 2 सेकंड रुककर दोबारा कोशिश
    return []

# --- 5. BOT HANDLERS ---

is_bot_busy = False

async def add_to_bank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """कमांड: /gen - AI से सवाल बनवाकर बैंक भरता है"""
    msg = await update.message.reply_text("🔄 AI सवाल बना रहा है (कोशिश 1/2)...")
    
    total_new = []
    
    # राउंड 1
    res1 = await fetch_questions_safe(5)
    if res1: total_new.extend(res1)
    
    await msg.edit_text("🔄 AI सवाल बना रहा है (कोशिश 2/2)...")
    await asyncio.sleep(1) # AI को थोड़ा गैप देना जरूरी है
    
    # राउंड 2
    res2 = await fetch_questions_safe(5)
    if res2: total_new.extend(res2)

    if not total_new:
        await msg.edit_text("❌ AI अभी भी रिस्पॉन्स नहीं दे रहा है। कृपया अपनी API Key चेक करें या 1 मिनट बाद कोशिश करें।")
        return

    # बैंक में सेव करें
    current_bank = load_json("quiz_bank.json")
    save_json("quiz_bank.json", current_bank + total_new)
    
    await msg.edit_text(f"✅ सफलता! {len(total_new)} नए सवाल बैंक में जोड़ दिए गए।\nकुल सवाल: {len(current_bank) + len(total_new)}")

async def start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_bot_busy
    if is_bot_busy: return

    bank = load_json("quiz_bank.json")
    if len(bank) < 5:
        await update.message.reply_text("⚠️ बैंक खाली है! पहले /gen चलायें।")
        return

    is_bot_busy = True
    
    # जितने सवाल बैंक में हैं (अधिकतम 20) उतने उठा लो
    take_count = min(len(bank), 20)
    quiz_data = random.sample(bank, take_count)
    
    full_text = f"🚀 **GK QUIZ ({take_count} QUESTIONS)** 🚀\n\n"
    for i, q in enumerate(quiz_data, 1):
        q_text = f"❓ **Q{i}:** {q['question']}\n"
        opts = ["A", "B", "C", "D"]
        for idx, opt in enumerate(q['options']):
            q_text += f"   {opts[idx]}) {opt}\n"
        q_text += f"✅ **उत्तर:** {opts[q['answer']]}\n\n"

        if len(full_text) + len(q_text) > 3800:
            await update.message.reply_text(full_text, parse_mode='Markdown')
            full_text = ""
        full_text += q_text

    if full_text: await update.message.reply_text(full_text, parse_mode='Markdown')
    await update.message.reply_text("🏆 टेस्ट पूरा हुआ! नए रैंडम सवालों के लिए /start भेजें।")
    is_bot_busy = False

async def reset_bank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_json("quiz_bank.json", [])
    await update.message.reply_text("🗑️ बैंक खाली कर दिया गया है।")

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
