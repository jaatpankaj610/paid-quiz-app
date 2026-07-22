import os
import sys
import logging
import asyncio
import json
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

# --- 3. FACTS लोड करने का फंक्शन ---

def load_user_facts():
    try:
        if os.path.exists("facts.json"):
            with open("facts.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                # आपकी फाइल एक लिस्ट है, इसे एक पैराग्राफ में बदल रहे हैं
                if isinstance(data, list):
                    return " ".join(data)
                return str(data)
    except Exception as e:
        logger.error(f"File Load Error: {e}")
    return "भारत का सामान्य ज्ञान।"

# --- 4. AI से सवाल मँगवाने का पक्का तरीका ---

async def get_questions_ai_retry(count=10):
    user_facts = load_user_facts()
    
    prompt = f"""
    तुम्हें इन तथ्यों का उपयोग करके {count} GK MCQs तैयार करने हैं: {user_facts}
    नियम:
    1. भाषा: हिंदी।
    2. 'ड़' की जगह 'ड' का प्रयोग करें।
    3. आउटपुट सिर्फ एक शुद्ध JSON Array होना चाहिए।
    Format: [{{"question": "...", "options": ["A", "B", "C", "D"], "answer": 0}}]
    """

    for attempt in range(3): # 3 बार कोशिश करेगा
        try:
            response = ai_client.models.generate_content(model='gemini-1.5-flash', contents=prompt)
            raw_text = response.text.replace("```json", "").replace("```", "").strip()
            match = re.search(r'\[.*\]', raw_text, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception as e:
            logger.warning(f"Attempt {attempt+1} failed. Retrying...")
            await asyncio.sleep(2)
    return []

# --- 5. BOT HANDLERS ---

is_bot_busy = False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_bot_busy
    
    if is_bot_busy:
        return # जब तक काम चल रहा है, कुछ न करें

    is_bot_busy = True
    status_msg = await update.message.reply_text("🚀 AI आपकी फाइल से 20 सवाल तैयार कर रहा है... कृपया प्रतीक्षा करें।")

    # 20 सवाल (10-10 के दो छोटे बैच में ताकि एरर न आए)
    all_questions = []
    
    batch1 = await get_questions_ai_retry(10)
    if batch1: all_questions.extend(batch1)
    
    # थोडा सा गैप AI को शांति देने के लिए
    await asyncio.sleep(1)
    
    batch2 = await get_questions_ai_retry(10)
    if batch2: all_questions.extend(batch2)

    if not all_questions:
        await status_msg.edit_text("❌ AI अभी व्यस्त है, कृपया 1 मिनट बाद फिर से /start करें।")
        is_bot_busy = False
        return

    await status_msg.delete()

    # सवालों को सजाकर भेजना
    full_text = "📝 **GK QUIZ - 20 QUESTIONS** 📝\n\n"
    
    for i, q in enumerate(all_questions, 1):
        try:
            q_block = f"❓ **सवाल {i}:** {q['question']}\n"
            opts = ["A", "B", "C", "D"]
            for idx, opt in enumerate(q['options']):
                q_block += f"   {opts[idx]}) {opt}\n"
            
            correct_ans = opts[q['answer']]
            q_block += f"✅ **सही उत्तर:** {correct_ans}\n\n"

            # अगर मैसेज बहुत लम्बा हो रहा है तो भेज दें
            if len(full_text) + len(q_block) > 3900:
                await context.bot.send_message(chat_id=update.effective_chat.id, text=full_text, parse_mode='Markdown')
                full_text = ""
            
            full_text += q_block
        except: continue

    if full_text:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=full_text, parse_mode='Markdown')

    # आखिरी स्क्रीन
    await context.bot.send_message(
        chat_id=update.effective_chat.id, 
        text="🏆 **टेस्ट पूरा हुआ!**\n\nसभी 20 सवाल ऊपर दे दिए गए हैं। अब आप दोबारा /start कर सकते हैं।"
    )
    
    is_bot_busy = False # अब बोट अगली कमांड के लिए तैयार है

async def ignore_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_bot_busy:
        return # प्रोसेसिंग के दौरान कुछ भी न सुनें

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
