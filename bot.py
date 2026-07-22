import os
import sys
import logging
import asyncio
import json
import re
import random
from google import genai
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

# 1. लॉगिंग (गलतियों को ट्रैक करने के लिए)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 2. क्रेडेंशियल्स
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

try:
    ai_client = genai.Client(api_key=GEMINI_API_KEY)
except Exception as e:
    logger.error(f"AI Setup Error: {e}")

# --- 3. FACTS से सवाल बनाने का फंक्शन ---

def load_facts():
    """facts.json से डाटा पढ़ना"""
    try:
        if os.path.exists("facts.json"):
            with open("facts.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                return str(data)
    except: pass
    return "भारत का इतिहास और सामान्य ज्ञान।"

async def get_questions_ai_robust(count=10):
    """AI से सवाल माँगना - फेल होने पर दोबारा कोशिश करना"""
    facts = load_facts()
    # भाषा और स्टाइल को अलग रखने के लिए रैंडम निर्देश
    styles = ["सरल भाषा", "कठिन भाषा", "रोचक तरीका", "प्रतियोगी परीक्षा स्तर"]
    selected_style = random.choice(styles)
    
    prompt = f"""
    तुम्हें इन तथ्यों का उपयोग करके {count} MCQs तैयार करने हैं: {facts}
    निर्देश:
    1. भाषा: हिंदी ({selected_style})।
    2. आउटपुट केवल एक शुद्ध JSON Array होना चाहिए।
    3. 'ड़' की जगह 'ड' का प्रयोग करें।
    Format: [{{"question": "...", "options": ["A", "B", "C", "D"], "answer": 0}}]
    """

    for attempt in range(3): # 3 बार कोशिश करेगा
        try:
            response = ai_client.models.generate_content(model='gemini-1.5-flash', contents=prompt)
            match = re.search(r'\[.*\]', response.text, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception as e:
            logger.warning(f"Attempt {attempt+1} failed: {e}")
            await asyncio.sleep(2) # 2 सेकंड रुककर दोबारा कोशिश
    return []

# --- 4. BOT HANDLERS ---

is_bot_busy = False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_bot_busy
    
    # अगर बोट पहले से काम कर रहा है तो कोई भी कमांड न सुनें
    if is_bot_busy:
        return 

    is_bot_busy = True
    status_msg = await update.message.reply_text("🔄 AI आपकी फाइल से नए सवाल तैयार कर रहा है...\n\n(इस दौरान कोई और कमांड काम नहीं करेगी)")

    # 10-10 के दो बैच में सवाल मँगाना ताकि एरर न आए
    batch1 = await get_questions_ai_robust(10)
    await status_msg.edit_text("⏳ आधे सवाल तैयार हैं, बाकी बन रहे हैं...")
    batch2 = await get_questions_ai_robust(10)

    final_quiz = batch1 + batch2

    if len(final_quiz) == 0:
        await status_msg.edit_text("❌ माफ़ी चाहता हूँ, AI अभी जवाब नहीं दे पा रहा है। कृपया 1 मिनट बाद /start करें।")
        is_bot_busy = False
        return

    await status_msg.delete()

    # 20 सवाल एक साथ भेजना
    full_text = f"📖 **आपका नया टेस्ट (कुल {len(final_quiz)} सवाल)**\n\n"
    
    for i, q in enumerate(final_quiz, 1):
        q_text = f"❓ **सवाल {i}:** {q['question']}\n"
        opts = ["A", "B", "C", "D"]
        for idx, opt in enumerate(q.get('options', [])):
            q_text += f"   {opts[idx]}) {opt}\n"
        
        correct_idx = q.get('answer', 0)
        q_text += f"✅ **उत्तर:** {q['options'][correct_idx]}\n\n"

        # मैसेज की सीमा चेक करना (4096 characters)
        if len(full_text) + len(q_text) > 3800:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=full_text, parse_mode='Markdown')
            full_text = ""
        
        full_text += q_text

    if full_text:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=full_text, parse_mode='Markdown')

    await context.bot.send_message(chat_id=update.effective_chat.id, text="🏆 **टेस्ट खत्म!**\n\nअगले नए टेस्ट के लिए /start भेजें।")
    
    is_bot_busy = False # अब बोट दोबारा कमांड सुनने के लिए तैयार है

async def ignore_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """जब बोट बिजी हो तो सब कुछ इग्नोर करे"""
    if is_bot_busy:
        return

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
