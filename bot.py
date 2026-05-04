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

# --- Flask Server (বটকে সচল রাখতে) ---
app_web = Flask('')
@app_web.route('/')
def home(): return "Super Ultimate Bot V3.0 is Online!"
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
        [KeyboardButton("⛅ আবহাওয়া"), KeyboardButton("🌐 স্ক্রিনশট")],
        [KeyboardButton("🔍 QR & Link"), KeyboardButton("🛠 এক্সট্রা টুলস")]
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
        f"🚀 **Ultimate Super Bot V3.0**\nস্বাগতম {update.effective_user.first_name}!\nসব সমাধান এখন এক জায়গায়।",
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

    # বাটন ক্লিকে স্টেট রিসেট
    buttons = ["📱 ভিডিও ডাউনলোড", "📂 Office টুলস", "📄 PDF টুলস", "🖼 ইমেজ এডিটর", "🤖 AI Chat", "🎨 AI ছবি তৈরি", "🌍 অনুবাদক ও উইকি", "🕋 নামাজের সময়", "⛅ আবহাওয়া", "🌐 স্ক্রিনশট", "🔍 QR & Link", "🛠 এক্সট্রা টুলস"]
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
        await update.message.reply_text("📍 জেলার নাম ইংরেজিতে লিখুন (Dhaka):")
    elif state == 'PRAYER':
        url = f"https://api.aladhan.com/v1/timingsByCity?city={text}&country=Bangladesh&method=2"
        async with httpx.AsyncClient() as client:
            res = await client.get(url)
            if res.status_code == 200:
                d = res.json()['data']['timings']
                msg = f"🕋 **{text} এর সময়:**\n\nFajr: {d['Fajr']}\nDhuhr: {d['Dhuhr']}\nAsr: {d['Asr']}\nMaghrib: {d['Maghrib']}\nIsha: {d['Isha']}"
                await update.message.reply_text(msg)
            else: await update.message.reply_text("❌ ভুল নাম।")
        context.user_data.clear()

    # ৪. আবহাওয়া
    elif text == "⛅ আবহাওয়া":
        context.user_data['state'] = 'WEATHER'
        await update.message.reply_text("🏙 শহরের নাম ইংরেজিতে লিখুন:")
    elif state == 'WEATHER':
        url = f"https://wttr.in/{text}?format=%C+%t"
        async with httpx.AsyncClient() as client:
            res = await client.get(url)
            await update.message.reply_text(f"⛅ {text}: {res.text}")
        context.user_data.clear()

    # ৫. অনুবাদক ও উইকি
    elif text == "🌍 অনুবাদক ও উইকি":
        btns = [[InlineKeyboardButton("🌍 অনুবাদক (Bn)", callback_data='m_trans'), InlineKeyboardButton("📖 উইকিপিডিয়া", callback_data='m_wiki')]]
        await update.message.reply_text("বেছে নিন:", reply_markup=InlineKeyboardMarkup(btns))

    # ৬. অফিস টুলস
    elif text == "📂 Office টুলস":
        btns = [[InlineKeyboardButton("📝 Word", callback_data='off_word'), InlineKeyboardButton("📊 Excel", callback_data='off_excel'), InlineKeyboardButton("📽 PPT", callback_data='off_ppt')]]
        await update.message.reply_text("কি ফাইল তৈরি করবেন?", reply_markup=InlineKeyboardMarkup(btns))

    elif state == 'WAIT_WORD':
        doc = Document(); doc.add_paragraph(text); path = f"d_{user_id}.docx"; doc.save(path)
        await update.message.reply_document(document=open(path, 'rb'), caption="✅ Word Done!"); os.remove(path); context.user_data.clear()

    # ৭. ওয়েবসাইট স্ক্রিনশট
    elif text == "🌐 স্ক্রিনশট":
        context.user_data['state'] = 'WAIT_SS'
        await update.message.reply_text("🔗 ওয়েবসাইট লিংক দিন:")
    elif state == 'WAIT_SS':
        if text.startswith("http"):
            url = f"https://api.screenshotmachine.com/?key=4f9584&url={text}&dimension=1024x768"
            await update.message.reply_photo(photo=url, caption=f"✅ {text}")
        context.user_data.clear()

    # ৮. লিংক এবং কিউআর
    elif text == "🔍 QR & Link":
        btns = [[InlineKeyboardButton("🔍 QR Code", callback_data='m_qr'), InlineKeyboardButton("🔗 Link Short", callback_data='m_short')]]
        await update.message.reply_text("অপশন:", reply_markup=InlineKeyboardMarkup(btns))

    elif text == "📱 ভিডিও ডাউনলোড":
        await update.message.reply_text("🎬 ভিডিও লিংক দিন।")

    elif text.startswith("http"):
        context.user_data['url'] = text
        btns = [[InlineKeyboardButton("🎬 Video", callback_data='dl_v'), InlineKeyboardButton("🎵 MP3", callback_data='dl_a')]]
        await update.message.reply_text("🔗 লিংক পাওয়া গেছে!", reply_markup=InlineKeyboardMarkup(btns))

# --- ফাইল হ্যান্ডলার (Images & PDF) ---
async def handle_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    file = update.message.document or (update.message.photo[-1] if update.message.photo else None)
    if not file: return

    if update.message.photo or (hasattr(file, 'file_name') and file.file_name.lower().endswith(('.jpg', '.png', '.webp'))):
        f = await (update.message.photo[-1].get_file() if update.message.photo else file.get_file())
        path = f"img_{user_id}_{int(time.time())}.jpg"; await f.download_to_drive(path)
        if user_id not in user_images: user_images[user_id] = []
        user_images[user_id].append(path); context.user_data['img_path'] = path
        btns = [[InlineKeyboardButton("🔄 Format Change", callback_data='img_format'), InlineKeyboardButton("🖼 Image to PDF", callback_data='convert_img_pdf')]]
        await update.message.reply_text("📸 ছবি পাওয়া গেছে!", reply_markup=InlineKeyboardMarkup(btns))

    elif hasattr(file, 'file_name') and file.file_name.lower().endswith('.pdf'):
        f = await file.get_file(); path = f"e_{user_id}.pdf"; await f.download_to_drive(path)
        pdf_edit_files[user_id] = path
        btns = [[InlineKeyboardButton("🔄 Rotate PDF", callback_data='pdf_rotate'), InlineKeyboardButton("🖼 PDF to Image", callback_data='pdf_to_img')]]
        await update.message.reply_text("📄 PDF পাওয়া গেছে!", reply_markup=InlineKeyboardMarkup(btns))

# --- বাটন অ্যাকশন (Callbacks) ---
async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user_id = query.from_user.id; await query.answer()
    data = query.data

    if data == 'off_word': context.user_data['state'] = 'WAIT_WORD'; await query.message.reply_text("📝 টেক্সট দিন:")
    elif data == 'dl_v' or data == 'dl_a':
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
            await context.bot.send_document(chat_id=user_id, document=open(path, 'rb')); os.remove(path)
        except: await query.message.reply_text("❌ ব্যর্থ!")

    elif data == 'convert_img_pdf':
        imgs = [Image.open(f).convert('RGB') for f in user_images[user_id]]
        out = f"d_{user_id}.pdf"; imgs[0].save(out, save_all=True, append_images=imgs[1:])
        await context.bot.send_document(chat_id=user_id, document=open(out, 'rb'))
        for f in user_images[user_id]: os.remove(f); del user_images[user_id]

    elif data == 'm_wiki':
        await query.message.reply_text("🔍 কি সম্পর্কে জানতে চান?")
        context.user_data['state'] = 'WAIT_WIKI'

# --- রান করা ---
if __name__ == '__main__':
    keep_alive()
    app = ApplicationBuilder().token(TOKEN).read_timeout(150).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_msg))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, handle_files))
    app.add_handler(CallbackQueryHandler(callback))
    print("🚀 বট সার্ভারে লাইভ হয়েছে!")
    app.run_polling()
