import os, asyncio, httpx, fitz, json, secrets, string, re, urllib.parse
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from flask import Flask
from threading import Thread

# --- কনফিগারেশন ---
TOKEN = "8681613014:AAGhaxmwY5Xv_F1FDDyccUwIqT05WXUAQ3M"
ADMIN_ID = 6365947320  # আপনার আইডি
GEMINI_KEY = "AIzaSyBLMcfkOSvW1s-6dEQ14p_T__on6ZmlXWY"

# --- ডাটাবেজ (Fake DB using JSON for Render compatibility) ---
DB_FILE = "database.json"
def load_db():
    if not os.path.exists(DB_FILE): return {"users": {}, "vip": [], "stats": {"total_files": 0}}
    with open(DB_FILE, "r") as f: return json.load(f)

def save_db(data):
    with open(DB_FILE, "w") as f: json.dump(data, f, indent=4)

# --- কিবোর্ড মেনুসমূহ ---
def main_menu(user_id):
    db = load_db()
    status = "🌟 VIP Member" if str(user_id) in db['vip'] else "🆓 Free User"
    
    keyboard = [
        [KeyboardButton("🤖 AI Assistant"), KeyboardButton("🎬 Media Downloader")],
        [KeyboardButton("📄 Office & PDF"), KeyboardButton("🖼 Image Tools")],
        [KeyboardButton("🛠 Utility Tools"), KeyboardButton("💰 VIP & Earn")],
        [KeyboardButton("📊 My Stats"), KeyboardButton("⚙️ Admin Panel") if user_id == ADMIN_ID else KeyboardButton("👤 Profile")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# --- এডমিন প্যানেল কিবোর্ড ---
def admin_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Broadcast", callback_data='adm_bc'), InlineKeyboardButton("📈 Total Stats", callback_data='adm_stats')],
        [InlineKeyboardButton("🔑 Add VIP", callback_data='adm_vip'), InlineKeyboardButton("🛠 Maintenance", callback_data='adm_mt')]
    ])

# --- এআই ফাংশন (Gemini Flash - Fast & Smart) ---
async def ai_chat(prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    async with httpx.AsyncClient() as client:
        try:
            res = await client.post(url, json=payload, timeout=30)
            return res.json()['candidates'][0]['content']['parts'][0]['text']
        except: return "❌ AI বর্তমানে ব্যস্ত আছে।"

# --- কমান্ড হ্যান্ডলার ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db = load_db()
    if str(user_id) not in db['users']:
        db['users'][str(user_id)] = {"name": update.effective_user.first_name, "date": str(datetime.now())}
        save_db(db)
    
    await update.message.reply_text(
        f"🔥 **Welcome to Super All-in-One Bot V4.0!**\n\nআপনার ডিজিটাল লাইফের সব সমাধান এখন এক জায়গায়।",
        reply_markup=main_menu(user_id), parse_mode="Markdown"
    )

# --- টেক্সট মেসেজ হ্যান্ডলার (Router) ---
async def handle_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    state = context.user_data.get('state')

    # মেইন মেনু রাউটিং
    if text == "🤖 AI Assistant":
        context.user_data['state'] = 'AI_CHAT'
        await update.message.reply_text("🤖 আমি এখন সক্রিয়। আমাকে যেকোনো প্রশ্ন করুন বা কাজ দিন:")
    
    elif text == "🎬 Media Downloader":
        await update.message.reply_text("🎬 YouTube, FB, Insta বা TikTok লিংক দিন।\n(VIP মেম্বাররা প্লেলিস্ট ডাউনলোড করতে পারবেন)।")

    elif text == "🖼 Image Tools":
        btns = [[InlineKeyboardButton("🎨 AI Image Gen", callback_data='it_ai'), InlineKeyboardButton("✂️ Remove BG", callback_data='it_rbg')],
                [InlineKeyboardButton("🖼 Resize / Crop", callback_data='it_rs'), InlineKeyboardButton("🔍 OCR (Text Extractor)", callback_data='it_ocr')]]
        await update.message.reply_text("🖼 ইমেজ টুলস বেছে নিন:", reply_markup=InlineKeyboardMarkup(btns))

    elif text == "📄 Office & PDF":
        btns = [[InlineKeyboardButton("📝 Word Maker", callback_data='of_word'), InlineKeyboardButton("📊 Excel Sheet", callback_data='of_excel')],
                [InlineKeyboardButton("📄 PDF to Word", callback_data='of_pdf2doc'), InlineKeyboardButton("🧾 Invoice Maker", callback_data='of_inv')]]
        await update.message.reply_text("📑 অফিস ও ডকুমেন্ট টুলস:", reply_markup=InlineKeyboardMarkup(btns))

    elif text == "⚙️ Admin Panel" and user_id == ADMIN_ID:
        await update.message.reply_text("⚙️ **Welcome Admin!**\nবট ম্যানেজমেন্ট শুরু করুন:", reply_markup=admin_menu())

    # --- স্টেট হ্যান্ডলিং ---
    elif state == 'AI_CHAT':
        msg = await update.message.reply_text("🤔")
        response = await ai_chat(text)
        await msg.edit_text(response)

    # --- লিংক ডিটেক্টর ---
    elif text.startswith("http"):
        context.user_data['url'] = text
        btns = [[InlineKeyboardButton("🎬 Video", callback_data='dl_v'), InlineKeyboardButton("🎵 MP3", callback_data='dl_a')],
                [InlineKeyboardButton("🎞 GIF (Short)", callback_data='dl_gif'), InlineKeyboardButton("🖼 Thumbnail", callback_data='dl_th')]]
        await update.message.reply_text("🔗 লিংক পাওয়া গেছে! কি করতে চান?", reply_markup=InlineKeyboardMarkup(btns))

# --- বাটন ক্লিক একশন (Callbacks) ---
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    await query.answer()

    if data == 'adm_stats':
        db = load_db()
        await query.message.reply_text(f"📊 **Bot Stats:**\nTotal Users: {len(db['users'])}\nVIPs: {len(db['vip'])}\nProcessed: {db['stats']['total_files']}")

    elif data == 'it_ai':
        context.user_data['state'] = 'AI_IMG'
        await query.message.reply_text("🎨 কেমন ছবি চান? বর্ণনা দিন (English):")

    elif data == 'of_word':
        context.user_data['state'] = 'WAIT_WORD'
        await query.message.reply_text("📝 ডকুমেন্টের লেখাটি পাঠান:")

# --- Flask Server ---
app_web = Flask('')
@app_web.route('/')
def home(): return "Super Bot V4.0 Online"
def keep_alive(): Thread(target=lambda: app_web.run(host='0.0.0.0', port=8080)).start()

if __name__ == '__main__':
    keep_alive()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_all))
    app.add_handler(CallbackQueryHandler(callback_handler))
    print("🚀 Super Bot V4.0 LIVE!")
    app.run_polling()
