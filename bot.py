import os
import sys
import logging
import asyncio
import json
import re
import random
from google import genai
from google.genai import types # सेफ्टी फिल्टर के लिए
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

# --- 3. AI QUIZ LOGIC ---

def load_facts():
    try:
        if os.path.exists("facts.json"):
            with open("facts.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                # अगर डाटा बहुत बड़ा है, तो रैंडम हिस्सा लें
                facts_str = str(data)
                return facts_str[:4000] # लिमिट ताकि AI कन्फ्यूज न हो
    except: pass
    return "भारत का सामान्य ज्ञान और इतिहास।"

async def get_questions_from_ai(count=10):
    facts = load_facts()
    # प्रॉम्प्ट को और भी सरल कर दिया गया है
    prompt = f"""
    Create {count} MCQs in Hindi based on these facts: {facts}
    Rules:
    - Respond ONLY with a JSON array.
    - No intro, no outro, no markdown code blocks.
    - Format: [{{"question": "Q1", "options": ["A", "B", "C", "D"], "answer": 0}}]
    """

    try:
        # सेफ्टी फिल्टर को डिसेबल करना ताकि जवाब न रुके
        response = ai_client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                top_p=0.95,
            )
        )
        
        # JSON साफ़ करना
        raw_text = response.text.strip()
        raw_text = raw_text.replace("```json", "").replace("```", "").strip()
        
        # JSON ढूंढना
        match = re.search(r'\[.*\]', raw_text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return []
    except Exception as e:
        logger.error(f"AI Error: {e}")
        return []

# --- 4. BOT HANDLERS ---

is_bot_busy = False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_bot_busy
    if is_bot_busy: return 

    is_bot_busy = True
    status_msg = await update.message.reply_text("⏳ AI सवाल तैयार कर रहा है... इसमें थोड़ा समय लग सकता है।")

    # दो बार अलग-अलग कोशिश करना
    all_questions = []
    
    # पहली कोशिश (10 सवाल)
    batch1 = await get_questions_from_ai(10)
    if batch1: all_questions.extend(batch1)
    
    # दूसरी कोशिश (10 सवाल)
    if len(all_questions) < 20:
        batch2 = await get_questions_from_ai(10)
        if batch2: all_questions.extend(batch2)

    # अगर बिल्कुल भी सवाल नहीं बने
    if not all_questions:
        await status_msg.edit_text("❌ AI अभी व्यस्त है। कृपया /start फिर से लिखें।")
        is_bot_busy = False
        return

    await status_msg.delete()

    # सवालों को भेजना
    full_text = f"📖 **GK QUIZ: {len(all_questions)} QUESTIONS**\n\n"
    
    for i, q in enumerate(all_questions, 1):
        try:
            q_text = f"❓ **सवाल {i}:** {q['question']}\n"
            opts = ["A", "B", "C", "D"]
            options = q.get('options', ["N/A", "N/A", "N/A", "N/A"])
            
            for idx, opt in enumerate(options):
                q_text += f"   {opts[idx]}) {opt}\n"
            
            ans_idx = q.get('answer', 0)
            q_text += f"✅ **उत्तर:** {options[ans_idx]}\n\n"

            if len(full_text) + len(q_text) > 3800:
                await context.bot.send_message(chat_id=update.effective_chat.id, text=full_text, parse_mode='Markdown')
                full_text = ""
            full_text += q_text
        except: continue

    if full_text:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=full_text, parse_mode='Markdown')

    await context.bot.send_message(chat_id=update.effective_chat.id, text="🏆 **टेस्ट पूरा हुआ!** अब आप दोबारा /start कर सकते हैं।")
    
    is_bot_busy = False

async def ignore_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_bot_busy: return

async def run_bot():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
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
        sys.exit(1)
