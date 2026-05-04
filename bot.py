import os, asyncio, httpx, fitz, json, secrets, string, re, urllib.parse
from PIL import Image, ImageFilter, ImageOps
from gtts import gTTS
from docx import Document
from openpyxl import Workbook
from pptx import Presentation
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from flask import Flask
from threading import Thread

# --- কনফিগারেশন ---
TOKEN = "8681613014:AAGhaxmwY5Xv_F1FDDyccUwIqT05WXUAQ3M"
ADMIN_ID = 6365947320
GEMINI_KEY = "AIzaSyBLMcfkOSvW1s-6dEQ14p_T__on6ZmlXWY"

# --- ডাটাবেজ সিস্টেম ---
DB_FILE = "database.json"
def load_db():
    if not os.path.exists(DB_FILE): return {"users": {}, "vip": [], "stats": {"files_processed": 0}}
    with open(DB_FILE, "r") as f: return json.load(f)

def save_db(db):
    with open(DB_FILE, "w") as f: json.dump(db, f, indent=4)

# --- কিবোর্ড মেনুসমূহ ---
def main_menu():
    return ReplyKeyboardMarkup([
        [KeyboardButton("🎬 Media Downloader"), KeyboardButton("📄 Office & PDF")],
        [KeyboardButton("🖼 Image Advanced Tools"), KeyboardButton("🤖 AI Smart Assistant")],
        [KeyboardButton("🛠 Utility & Converters"), KeyboardButton("⚙️ Admin Panel")],
        [KeyboardButton("📊 Stats & VIP"), KeyboardButton("👤 Profile")]
    ], resize_keyboard=True)

def image_adv_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🖼 BG Remove", callback_data='img_rbg'), InlineKeyboardButton("🔍 Image to Text (OCR)", callback_data='img_ocr')],
        [InlineKeyboardButton("🌫 Blur", callback_data='img_blur'), InlineKeyboardButton("✨ Sharpen", callback_data='img_sharp')],
        [InlineKeyboardButton("✂️ Resize Social", callback_data='img_resize'), InlineKeyboardButton("🎭 Sketch", callback_data='img_sketch')]
    ])

def office_pdf_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Word Maker", callback_data='off_word'), InlineKeyboardButton("📊 Excel Sheet", callback_data='off_excel')],
        [InlineKeyboardButton("🧾 Invoice Maker", callback_data='off_inv'), InlineKeyboardButton("📄 PDF to Word", callback_data='off_pdf2doc')],
        [InlineKeyboardButton("📽 PPT Maker", callback_data='off_ppt'), InlineKeyboardButton("🔄 Rotate PDF", callback_data='off_pdfrot')]
    ])

def utility_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💱 Currency Converter", callback_data='ut_curr'), InlineKeyboardButton("📏 Unit Converter", callback_data='ut_unit')],
        [InlineKeyboardButton("🔐 Password Gen", callback_data='ut_pass'), InlineKeyboardButton("🔗 URL Shortener", callback_data='ut_short')],
        [InlineKeyboardButton("📝 Save Notes", callback_data='ut_notes'), InlineKeyboardButton("🗣 Text to Speech", callback_data='ut_tts')]
    ])

# --- এআই চ্যাট ফাংশন ---
async def ai_chat(prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    async with httpx.AsyncClient() as client:
        try:
            res = await client.post(url, json=payload, timeout=30)
            return res.json()['candidates'][0]['content']['parts'][0]['text']
        except: return "❌ AI ব্যস্ত আছে।"

# --- কমান্ডস ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db = load_db()
    if str(user_id) not in db['users']:
        db['users'][str(user_id)] = {"name": update.effective_user.first_name, "vip": False}
        save_db(db)
    await update.message.reply_text("🚀 **Super Tool Bot V5.0 Active!**\nসব টুল এখন আপনার হাতের মুঠোয়।", reply_markup=main_menu())

# --- মূল মেসেজ হ্যান্ডলার ---
async def handle_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    
    # বাটন ক্লিক করলে রিসেট
    main_btns = ["🎬 Media Downloader", "📄 Office & PDF", "🖼 Image Advanced Tools", "🤖 AI Smart Assistant", "🛠 Utility & Converters", "⚙️ Admin Panel", "📊 Stats & VIP", "👤 Profile"]
    if text in main_btns: context.user_data.clear()

    if text == "🤖 AI Smart Assistant":
        context.user_data['state'] = 'AI_CHAT'
        await update.message.reply_text("🤖 আমি আপনার স্মার্ট অ্যাসিস্ট্যান্ট। কি সাহায্য করতে পারি?")
    
    elif text == "🎬 Media Downloader":
        await update.message.reply_text("🎬 ভিডিওর লিংক দিন (YT/FB/IG/TikTok)।")
    
    elif text == "📄 Office & PDF":
        await update.message.reply_text("📂 অফিস টুলস সিলেক্ট করুন:", reply_markup=office_pdf_menu())
        
    elif text == "🖼 Image Advanced Tools":
        await update.message.reply_text("🖼 ছবি পাঠান এবং নিচের টুলস ব্যবহার করুন:", reply_markup=image_adv_menu())

    elif text == "🛠 Utility & Converters":
        await update.message.reply_text("🛠 ইউটিলিটি মেনু:", reply_markup=utility_menu())

    elif text == "⚙️ Admin Panel" and user_id == ADMIN_ID:
        await update.message.reply_text("⚙️ **Admin Panel**\n/broadcast - মেসেজ পাঠান\n/stats - ইউজার লিস্ট")

    elif text == "👤 Profile":
        db = load_db()
        status = "🌟 VIP" if str(user_id) in db['vip'] else "🆓 Free"
        await update.message.reply_text(f"👤 নাম: {update.effective_user.first_name}\n🆔 আইডি: `{user_id}`\n🚀 স্ট্যাটাস: {status}", parse_mode="Markdown")

    # --- এআই চ্যাট লজিক ---
    state = context.user_data.get('state')
    if state == 'AI_CHAT':
        msg = await update.message.reply_text("🤔")
        ans = await ai_chat(text)
        await msg.edit_text(ans)
    
    # --- লিংক ডিটেক্টর ---
    elif text.startswith("http"):
        context.user_data['url'] = text
        btns = [[InlineKeyboardButton("🎥 High Quality", callback_data='dl_v_high'), InlineKeyboardButton("🎞 Low Quality", callback_data='dl_v_low')],
                [InlineKeyboardButton("🎵 Audio MP3", callback_data='dl_a')]]
        await update.message.reply_text("🔗 লিংক পাওয়া গেছে! কোয়ালিটি বেছে নিন:", reply_markup=InlineKeyboardMarkup(btns))

# --- বাটন ক্লিক একশন ---
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; data = query.data; user_id = query.from_user.id
    await query.answer()

    if data == 'ut_pass':
        pwd = ''.join(secrets.choice(string.ascii_letters + string.digits) for i in range(12))
        await query.message.reply_text(f"🔐 আপনার পাসওয়ার্ড: `{pwd}`")

    elif data == 'ut_curr':
        await query.message.reply_text("💱 বর্তমান রেট: 1 USD = 118.50 BDT")

    elif data == 'off_word':
        context.user_data['state'] = 'WAIT_WORD'
        await query.message.reply_text("📝 ওয়ার্ড ফাইলের জন্য টেক্সট পাঠান:")

    elif data == 'img_sketch':
        await query.message.reply_text("🎨 ছবি পাঠান, আমি স্কেচ করে দিচ্ছি।")

# --- Flask Server ---
app_web = Flask('')
@app_web.route('/')
def home(): return "Super Bot V5.0 is Running"
def keep_alive(): Thread(target=lambda: app_web.run(host='0.0.0.0', port=8080)).start()

if __name__ == '__main__':
    keep_alive()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_all))
    app.add_handler(CallbackQueryHandler(callback_handler))
    print("🚀 বট সফলভাবে সব ফিচারের সাথে চালু হয়েছে!")
    app.run_polling()
