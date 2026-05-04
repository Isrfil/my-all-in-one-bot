import os, qrcode, asyncio, httpx, fitz, time, re, secrets, string, urllib.parse, wikipedia
from pypdf import PdfReader, PdfWriter
from yt_dlp import YoutubeDL
from PIL import Image, ImageOps, ImageFilter
from gtts import gTTS
import pyshorteners
from docx import Document
from openpyxl import Workbook
from pptx import Presentation
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from flask import Flask
from threading import Thread

# --- Flask Server (বটকে ২৪ ঘণ্টা সচল রাখতে) ---
app_web = Flask('')
@app_web.route('/')
def home(): return "Super Bot V3.0 Ultimate is Online!"
def run(): app_web.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- কনফিগারেশন ---
TOKEN = "8681613014:AAGhaxmwY5Xv_F1FDDyccUwIqT05WXUAQ3M"
GEMINI_API_KEY = "AIzaSyBLMcfkOSvW1s-6dEQ14p_T__on6ZmlXWY"
ADMIN_ID = 6365947320
USER_FILE = "users.txt"

# ডেটা স্টোর
user_images = {}
pdf_edit_files = {}

# ইউজার লগ করার ফাংশন
def log_user(user_id):
    if not os.path.exists(USER_FILE): open(USER_FILE, "w").close()
    with open(USER_FILE, "r+") as f:
        users = f.read().splitlines()
        if str(user_id) not in users: f.write(str(user_id) + "\n")

# --- কিবোর্ড মেনুসমূহ ---
def main_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("📱 ভিডিও ডাউনলোড"), KeyboardButton("📂 Office টুলস")],
        [KeyboardButton("📄 PDF টুলস"), KeyboardButton("🖼 ইমেজ এডিটর")],
        [KeyboardButton("🤖 AI Chat"), KeyboardButton("🎨 AI ছবি তৈরি")],
        [KeyboardButton("🌍 অনুবাদক ও উইকি"), KeyboardButton("🕋 নামাজের সময়")],
        [KeyboardButton("⛅ আবহাওয়া"), KeyboardButton("🔍 QR & Link")],
        [KeyboardButton("🛠 এক্সট্রা টুলস"), KeyboardButton("👤 প্রোফাইল")]
    ], resize_keyboard=True, is_persistent=True)

# --- এআই চ্যাট ফাংশন (Gemini) ---
async def call_gemini(text):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {"contents": [{"parts": [{"text": text}]}]}
    async with httpx.AsyncClient() as client:
        try:
            res = await client.post(url, json=payload, timeout=40)
            return res.json()['candidates'][0]['content']['parts'][0]['text']
        except: return "❌ এআই এখন উত্তর দিতে পারছে না।"

# --- কমান্ড হ্যান্ডলার ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log_user(update.effective_user.id)
    await update.message.reply_text(
        f"🚀 **Ultimate Super Bot V3.0**\nস্বাগতম {update.effective_user.first_name}! আমি আপনার সব কাজের স্মার্ট অ্যাসিস্ট্যান্ট।",
        reply_markup=main_keyboard(), parse_mode="Markdown"
    )

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    msg = " ".join(context.args)
    if os.path.exists(USER_FILE):
        with open(USER_FILE, "r") as f:
            for user in f.read().splitlines():
                try: await context.bot.send_message(chat_id=int(user), text=f"📢 **নোটিশ:**\n\n{msg}", parse_mode="Markdown")
                except: continue

# --- মূল মেসেজ হ্যান্ডলার ---
async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    state = context.user_data.get('state')

    # বাটন ক্লিকে স্টেট ক্লিয়ার
    buttons = ["📱 ভিডিও ডাউনলোড", "📂 Office টুলস", "📄 PDF টুলস", "🖼 ইমেজ এডিটর", "🤖 AI Chat", "🎨 AI ছবি তৈরি", "🌍 অনুবাদক ও উইকি", "🕋 নামাজের সময়", "⛅ আবহাওয়া", "🔍 QR & Link", "🛠 এক্সট্রা টুলস", "👤 প্রোফাইল"]
    if text in buttons: context.user_data.clear()

    # ১. এআই চ্যাট
    if text == "🤖 AI Chat":
        context.user_data['state'] = 'AI'
        await update.message.reply_text("🤖 এআই সক্রিয়! প্রশ্ন করুন:")
    elif state == 'AI' and not text.startswith("http"):
        ans = await call_gemini(text)
        await update.message.reply_text(ans)

    # ২. এআই ছবি তৈরি
    elif text == "🎨 AI ছবি তৈরি":
        context.user_data['state'] = 'AI_IMG'
        await update.message.reply_text("🎨 ছবির বর্ণনা দিন (English):")
    elif state == 'AI_IMG':
        prompt = urllib.parse.quote(text)
        await update.message.reply_photo(photo=f"https://image.pollinations.ai/prompt/{prompt}", caption=f"✅ {text}")
        context.user_data.clear()

    # ৩. নামাজের সময়
    elif text == "🕋 নামাজের সময়":
        context.user_data['state'] = 'PRAYER'
        await update.message.reply_text("📍 জেলার নাম ইংরেজিতে লিখুন (যেমন: Dhaka):")
    elif state == 'PRAYER':
        url = f"https://api.aladhan.com/v1/timingsByCity?city={text}&country=Bangladesh&method=2"
        async with httpx.AsyncClient() as client:
            res = await client.get(url)
            if res.status_code == 200:
                d = res.json()['data']['timings']
                msg = f"🕋 **{text} এর সময়:**\n\nFajr: {d['Fajr']}\nDhuhr: {d['Dhuhr']}\nAsr: {d['Asr']}\nMaghrib: {d['Maghrib']}\nIsha: {d['Isha']}"
                await update.message.reply_text(msg)
            else: await update.message.reply_text("❌ নাম ভুল।")
        context.user_data.clear()

    # ৪. আবহাওয়া
    elif text == "⛅ আবহাওয়া":
        context.user_data['state'] = 'WEATHER'
        await update.message.reply_text("🏙 শহরের নাম ইংরেজিতে লিখুন:")
    elif state == 'WEATHER':
        url = f"https://wttr.in/{text}?format=%C+%t+%h"
        async with httpx.AsyncClient() as client:
            res = await client.get(url)
            await update.message.reply_text(f"⛅ {text}: {res.text}")
        context.user_data.clear()

    # ৫. অনুবাদক ও উইকি
    elif text == "🌍 অনুবাদক ও উইকি":
        btns = [[InlineKeyboardButton("🌍 অনুবাদক (Bn)", callback_data='m_trans'), InlineKeyboardButton("📖 উইকিপিডিয়া", callback_data='m_wiki')]]
        await update.message.reply_text("অপশন বেছে নিন:", reply_markup=InlineKeyboardMarkup(btns))

    # বাকি আগের সব ফিচার (ভিডিও, অফিস, কিউআর)
    elif text == "📱 ভিডিও ডাউনলোড":
        await update.message.reply_text("🎬 ভিডিও লিংক দিন।")
    elif text.startswith("http"):
        context.user_data['url'] = text
        btns = [[InlineKeyboardButton("🎬 Video", callback_data='dl_v'), InlineKeyboardButton("🎵 MP3", callback_data='dl_a')]]
        await update.message.reply_text("🔗 লিংক পাওয়া গেছে!", reply_markup=InlineKeyboardMarkup(btns))

# --- বাটন অ্যাকশন (Callbacks) ---
async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user_id = query.from_user.id; await query.answer()
    data = query.data

    if data == 'dl_v' or data == 'dl_a':
        url = context.user_data.get('url'); mode = 'v' if data == 'dl_v' else 'a'
        await query.edit_message_text("⏳ ডাউনলোড হচ্ছে...")
        def dl():
            opts = {'format': 'best', 'outtmpl': '%(title)s.%(ext)s', 'max_filesize': 48*1024*1024}
            if mode == 'a': opts['postprocessors'] = [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3'}]
            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True); p = ydl.prepare_filename(info)
                return p.rsplit('.', 1)[0] + ".mp3" if mode == 'a' else p
        try:
            path = await asyncio.to_thread(dl)
            await context.bot.send_document(chat_id=user_id, document=open(path, 'rb'))
            os.remove(path)
        except: await query.message.reply_text("❌ ব্যর্থ!")

# --- রান করা ---
if __name__ == '__main__':
    keep_alive()
    app = ApplicationBuilder().token(TOKEN).read_timeout(150).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_msg))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, handle_files)) # handle_files ফাংশন আগের মতো
    app.add_handler(CallbackQueryHandler(callback))
    app.run_polling()
