import os, qrcode, asyncio, httpx
from pypdf import PdfReader, PdfWriter
from yt_dlp import YoutubeDL
from PIL import Image
from gtts import gTTS
import pyshorteners
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from flask import Flask
from threading import Thread

# --- Flask Server (বটকে ২৪ ঘণ্টা সচল রাখতে) ---
app_web = Flask('')
@app_web.route('/')
def home():
    return "Bot is Running!"

def run():
    app_web.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- সেটিংস ---
TOKEN = "8681613014:AAGhaxmwY5Xv_F1FDDyccUwIqT05WXUAQ3M"
GEMINI_API_KEY = "AIzaSyBLMcfkOSvW1s-6dEQ14p_T__on6ZmlXWY"
ADMIN_ID = 6365947320

user_images = {}
merge_data = {}

def main_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("🎥 ভিডিও ডাউনলোড"), KeyboardButton("📄 PDF এডিটর")],
        [KeyboardButton("🖼 Image to PDF"), KeyboardButton("🔍 QR Code")],
        [KeyboardButton("🤖 AI Chat (Gemini)"), KeyboardButton("🔗 Link Shorten")],
        [KeyboardButton("🗣 Text to Speech"), KeyboardButton("👤 প্রোফাইল")]
    ], resize_keyboard=True, is_persistent=True)

# Gemini AI Function
async def call_gemini(text):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    data = {"contents": [{"parts": [{"text": text}]}]}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=data, headers=headers, timeout=40)
            result = response.json()
            return result['candidates'][0]['content']['parts'][0]['text']
        except: return "❌ এআই এই মুহূর্তে উত্তর দিতে পারছে না।"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🔥 স্বাগতম {update.effective_user.first_name}!\nনিচের মেনু থেকে কাজ শুরু করুন।", reply_markup=main_keyboard())

async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    state = context.user_data.get('state')

    if text in ["🎥 ভিডিও ডাউনলোড", "📄 PDF এডিটর", "🖼 Image to PDF", "🔍 QR Code", "🤖 AI Chat (Gemini)", "🔗 Link Shorten", "🗣 Text to Speech", "👤 প্রোফাইল"]:
        context.user_data.clear()

    if text == "🤖 AI Chat (Gemini)":
        context.user_data['state'] = 'AI'
        await update.message.reply_text("🤖 এআই সক্রিয়! প্রশ্ন করুন:")
    elif state == 'AI' and not text.startswith("http"):
        msg = await update.message.reply_text("🤔 চিন্তা করছি...")
        ans = await call_gemini(text)
        await msg.edit_text(ans)
    
    elif text == "🔍 QR Code":
        context.user_data['state'] = 'QR'
        await update.message.reply_text("লিংক বা টেক্সট পাঠান:")
    elif state == 'QR':
        path = f"qr_{user_id}.png"
        qrcode.make(text).save(path)
        await update.message.reply_photo(photo=open(path, 'rb'), caption="✅ QR Code তৈরি!")
        os.remove(path)
        context.user_data.clear()

    elif text == "🔗 Link Shorten":
        context.user_data['state'] = 'SHORT'
        await update.message.reply_text("বড় লিংকটি পাঠান:")
    elif state == 'SHORT':
        try:
            s = pyshorteners.Shortener()
            await update.message.reply_text(f"✅ ছোট লিংক: {s.tinyurl.short(text)}")
        except: await update.message.reply_text("❌ ভুল লিংক।")
        context.user_data.clear()

    elif text == "🗣 Text to Speech":
        context.user_data['state'] = 'TTS'
        await update.message.reply_text("লেখাটি পাঠান:")
    elif state == 'TTS':
        path = f"tts_{user_id}.mp3"
        lang = 'bn' if any('\u0980' <= c <= '\u09FF' for c in text) else 'en'
        gTTS(text=text, lang=lang).save(path)
        await update.message.reply_audio(audio=open(path, 'rb'))
        os.remove(path)
        context.user_data.clear()

    elif text == "🎥 ভিডিও ডাউনলোড":
        await update.message.reply_text("যেকোনো ভিডিও লিংক (FB/IG/YT/TikTok) এখানে পাঠান।")
    elif text.startswith("http"):
        context.user_data['url'] = text
        btns = [[InlineKeyboardButton("🎬 Video", callback_data='v'), InlineKeyboardButton("🎵 MP3", callback_data='a')]]
        await update.message.reply_text("🔗 লিংক পাওয়া গেছে!", reply_markup=InlineKeyboardMarkup(btns))

    elif text == "🖼 Image to PDF":
        user_images[user_id] = []
        await update.message.reply_text("📥 ছবিগুলো পাঠান। শেষ হলে /convert লিখুন।")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_images:
        photo = await update.message.photo[-1].get_file()
        path = f"img_{user_id}_{len(user_images[user_id])}.jpg"
        await photo.download_to_drive(path)
        user_images[user_id].append(path)
        await update.message.reply_text(f"✅ {len(user_images[user_id])} নং ছবি যুক্ত হয়েছে।")

async def convert_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_images and user_images[user_id]:
        imgs = [Image.open(f).convert('RGB') for f in user_images[user_id]]
        pdf_path = f"file_{user_id}.pdf"
        imgs[0].save(pdf_path, save_all=True, append_images=imgs[1:])
        await update.message.reply_document(document=open(pdf_path, 'rb'), caption="✅ PDF সম্পন্ন!")
        for f in user_images[user_id]: os.remove(f)
        os.remove(pdf_path)
        del user_images[user_id]

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    url = context.user_data.get('url')
    mode = 'v' if query.data == 'v' else 'a'
    await query.edit_message_text("⏳ ডাউনলোড হচ্ছে...")
    opts = {'format': 'best', 'outtmpl': '%(title)s.%(ext)s', 'max_filesize': 48*1024*1024}
    if mode == 'a': opts['postprocessors'] = [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3'}]
    try:
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True); path = ydl.prepare_filename(info)
            if mode == 'a': path = path.rsplit('.', 1)[0] + ".mp3"
            await context.bot.send_document(chat_id=query.message.chat_id, document=open(path, 'rb'))
            os.remove(path)
    except: await query.message.reply_text("❌ এরর!")

if __name__ == '__main__':
    keep_alive()
    app = ApplicationBuilder().token(TOKEN).read_timeout(60).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("convert", convert_pdf))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_msg))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(callback))
    print("🚀 বট সার্ভারে চালু হয়েছে!")
    app.run_polling()
