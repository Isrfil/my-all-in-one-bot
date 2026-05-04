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
    try:
        with open(DB_FILE, "r") as f: return json.load(f)
    except: return {"users": {}, "vip": [], "stats": {"total_files": 0}}

def save_db(data):
    with open(DB_FILE, "w") as f: json.dump(data, f, indent=4)

# --- কিবোর্ড মেনু ---
def main_menu():
    keyboard = [
        [KeyboardButton("🎬 Media Downloader"), KeyboardButton("📄 Office & PDF")],
        [KeyboardButton("🖼 Image Tools"), KeyboardButton("🤖 AI Assistant")],
        [KeyboardButton("🛠 Utility Tools"), KeyboardButton("📊 My Stats")],
        [KeyboardButton("💰 VIP & Earn"), KeyboardButton("👤 Profile")]
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
        except: return "❌ AI বর্তমানে ব্যস্ত আছে।"

# --- কমান্ড হ্যান্ডলার ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db = load_db()
    if str(user_id) not in db['users']:
        db['users'][str(user_id)] = {"name": update.effective_user.first_name, "date": str(datetime.now())}
        save_db(db)
    
    context.user_data.clear()
    await update.message.reply_text(
        f"🔥 **Super All-in-One Bot V4.0**\nস্বাগতম {update.effective_user.first_name}!",
        reply_markup=main_menu(), parse_mode="Markdown"
    )

# --- মূল মেসেজ হ্যান্ডলার (Fix: AI মোড ওভারল্যাপ সমাধান) ---
async def handle_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    
    # ১. সব বাটনের লিস্ট (যাতে এগুলো ক্লিক করলে AI মোড বন্ধ হয়)
    all_buttons = [
        "🎬 Media Downloader", "📄 Office & PDF", "🖼 Image Tools", 
        "🤖 AI Assistant", "🛠 Utility Tools", "📊 My Stats", 
        "💰 VIP & Earn", "👤 Profile"
    ]
    
    if text in all_buttons:
        context.user_data.clear() # স্টেট রিসেট

    # ২. বাটন অনুযায়ী আলাদা ফাংশন
    if text == "🤖 AI Assistant":
        context.user_data['state'] = 'AI_CHAT'
        await update.message.reply_text("🤖 এআই মোড সক্রিয়। এখন আমাকে যেকোনো প্রশ্ন করুন:")
        return

    elif text == "🎬 Media Downloader":
        await update.message.reply_text("🎬 ভিডিওর লিংক এখানে পাঠান (FB/IG/YT/TikTok)।")
        return

    elif text == "🛠 Utility Tools":
        btns = [[InlineKeyboardButton("🔐 Password Generator", callback_data='ut_pass')],
                [InlineKeyboardButton("💱 Currency Converter", callback_data='ut_curr')]]
        await update.message.reply_text("🛠 ইউটিলিটি টুলস বেছে নিন:", reply_markup=InlineKeyboardMarkup(btns))
        return

    elif text == "📊 My Stats":
        db = load_db()
        total_users = len(db['users'])
        await update.message.reply_text(f"📊 **Bot Statistics:**\n\n👥 Total Users: {total_users}\n🌟 VIP Members: {len(db['vip'])}\n✅ Your Status: Free User")
        return

    elif text == "💰 VIP & Earn":
        await update.message.reply_text("💰 **VIP & Earn System:**\n\n১. বন্ধুদের ইনভাইট করে VIP হতে পারেন।\n২. প্রিমিয়াম ফিচারের জন্য এডমিনকে মেসেজ দিন।\n(শীঘ্রই আসছে...)")
        return

    elif text == "👤 Profile":
        await update.message.reply_text(f"👤 **নাম:** {update.effective_user.first_name}\n🆔 **আইডি:** `{user_id}`", parse_mode="Markdown")
        return

    # ৩. লিংক ডিটেকশন (ডাউনলোডার)
    if text.startswith("http"):
        context.user_data['url'] = text
        btns = [[InlineKeyboardButton("🎥 Video", callback_data='dl_v'), InlineKeyboardButton("🎵 MP3", callback_data='dl_a')]]
        await update.message.reply_text("🔗 লিংক পাওয়া গেছে! কি করতে চান?", reply_markup=InlineKeyboardMarkup(btns))
        return

    # ৪. এআই চ্যাট প্রসেসিং (শুধুমাত্র স্টেট সক্রিয় থাকলে)
    state = context.user_data.get('state')
    if state == 'AI_CHAT':
        msg = await update.message.reply_text("🤔")
        response = await ai_chat(text)
        await msg.edit_text(response)
        return

# --- বাটন ক্লিক একশন ---
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == 'ut_pass':
        pwd = ''.join(secrets.choice(string.ascii_letters + string.digits) for i in range(12))
        await query.message.reply_text(f"🔐 আপনার সিকিউর পাসওয়ার্ড: `{pwd}`")

# --- Flask Server ---
app_web = Flask('')
@app_web.route('/')
def home(): return "Bot is Alive"
def keep_alive(): Thread(target=lambda: app_web.run(host='0.0.0.0', port=8080)).start()

if __name__ == '__main__':
    keep_alive()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_all))
    app.add_handler(CallbackQueryHandler(callback_handler))
    print("🚀 বট সফলভাবে আপডেট করা হয়েছে!")
    app.run_polling()
