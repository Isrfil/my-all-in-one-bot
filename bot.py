import os, asyncio, httpx, fitz, json, secrets, string, re, urllib.parse
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from flask import Flask
from threading import Thread

# --- কনফিগারেশন ---
TOKEN = "8681613014:AAGhaxmwY5Xv_F1FDDyccUwIqT05WXUAQ3M"
ADMIN_ID = 6365947320
GEMINI_KEY = "AIzaSyBLMcfkOSvW1s-6dEQ14p_T__on6ZmlXWY"

# --- ডাটাবেজ ---
DB_FILE = "database.json"
def load_db():
    if not os.path.exists(DB_FILE): return {"users": {}, "vip": [], "stats": {"total_files": 0}}
    with open(DB_FILE, "r") as f: return json.load(f)

def save_db(data):
    with open(DB_FILE, "w") as f: json.dump(data, f, indent=4)

# --- কিবোর্ড মেনুসমূহ ---
def main_menu():
    keyboard = [
        [KeyboardButton("🎬 Media Downloader"), KeyboardButton("📄 Office & PDF")],
        [KeyboardButton("🖼 Image Tools"), KeyboardButton("🤖 AI Assistant")],
        [KeyboardButton("🛠 Utility Tools"), KeyboardButton("👤 Profile")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)

# --- এআই ফাংশন ---
async def ai_chat(prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    async with httpx.AsyncClient() as client:
        try:
            res = await client.post(url, json=payload, timeout=30)
            return res.json()['candidates'][0]['content']['parts'][0]['text']
        except: return "❌ AI বর্তমানে উত্তর দিতে পারছে না। পরে চেষ্টা করুন।"

# --- কমান্ড হ্যান্ডলার ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear() # রিসেট
    await update.message.reply_text(
        f"🔥 **Super All-in-One Bot V4.0**\nস্বাগতম {update.effective_user.first_name}!\nনিচের মেনু থেকে সার্ভিস বেছে নিন।",
        reply_markup=main_menu(), parse_mode="Markdown"
    )

# --- মূল মেসেজ হ্যান্ডলার (ফিক্সড রাউটিং) ---
async def handle_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    
    # ১. যদি কোনো বাটনে ক্লিক করা হয়, তবে আগের সব স্টেট (যেমন AI মোড) বন্ধ করে দাও
    all_buttons = ["🎬 Media Downloader", "📄 Office & PDF", "🖼 Image Tools", "🤖 AI Assistant", "🛠 Utility Tools", "👤 Profile"]
    
    if text in all_buttons:
        context.user_data.clear() # এটি সবকিছুর আগে কাজ করবে

    # ২. বাটন অনুযায়ী কাজ শুরু
    if text == "🤖 AI Assistant":
        context.user_data['state'] = 'AI_CHAT'
        await update.message.reply_text("🤖 এআই মোড সক্রিয়। এখন আমাকে যেকোনো প্রশ্ন করুন:")
        return

    elif text == "🎬 Media Downloader":
        await update.message.reply_text("🎬 ভিডিওর লিংক এখানে পাঠান (FB/IG/YT/TikTok)।")
        return

    elif text == "📄 Office & PDF":
        btns = [[InlineKeyboardButton("📝 Word Maker", callback_data='of_word'), InlineKeyboardButton("📄 PDF Rotate", callback_data='of_pdfrot')]]
        await update.message.reply_text("📑 অফিস ও পিডিএফ টুলস:", reply_markup=InlineKeyboardMarkup(btns))
        return

    elif text == "🖼 Image Tools":
        btns = [[InlineKeyboardButton("🎨 AI Image", callback_data='it_ai'), InlineKeyboardButton("🔍 QR Code", callback_data='it_qr')]]
        await update.message.reply_text("🖼 ইমেজ টুলস বেছে নিন:", reply_markup=InlineKeyboardMarkup(btns))
        return

    elif text == "🛠 Utility Tools":
        await update.message.reply_text("🛠 ইউটিলিটি টুলস শীঘ্রই আসছে।")
        return

    elif text == "👤 Profile":
        await update.message.reply_text(f"👤 নাম: {update.effective_user.first_name}\n🆔 আইডি: `{user_id}`", parse_mode="Markdown")
        return

    # ৩. যদি ইউজার কোনো লিংক পাঠায় (ডাউনলোডার আগে চেক হবে)
    if text.startswith("http"):
        context.user_data['url'] = text
        btns = [[InlineKeyboardButton("🎥 Video", callback_data='dl_v'), InlineKeyboardButton("🎵 MP3", callback_data='dl_a')]]
        await update.message.reply_text("🔗 লিংক পাওয়া গেছে! কি করতে চান?", reply_markup=InlineKeyboardMarkup(btns))
        return

    # ৪. সবশেষে চেক করা হবে কোনো স্টেট (যেমন AI Chat) সচল আছে কি না
    state = context.user_data.get('state')
    
    if state == 'AI_CHAT':
        msg = await update.message.reply_text("🤔")
        response = await ai_chat(text)
        await msg.edit_text(response)
    
    elif state == 'WAIT_WORD':
        # (এখানে ওয়ার্ড ফাইল তৈরির লজিক থাকবে)
        await update.message.reply_text("📝 ওয়ার্ড ফাইল প্রসেসিং...")
        context.user_data.clear()

# --- বাটন ক্লিক একশন (Callbacks) ---
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    # (বাকি সব ডাউনলোড এবং টুলস লজিক এখানে থাকবে)

# --- Flask Server ---
app_web = Flask('')
@app_web.route('/')
def home(): return "Super Bot is Active!"
def keep_alive(): Thread(target=lambda: app_web.run(host='0.0.0.0', port=8080)).start()

if __name__ == '__main__':
    keep_alive()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_all))
    app.add_handler(CallbackQueryHandler(callback_handler))
    print("🚀 বট সার্ভারে ফিক্স করা হয়েছে!")
    app.run_polling()
