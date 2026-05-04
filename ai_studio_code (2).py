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

# --- Flask Server (Keep Alive) ---
app_web = Flask('')
@app_web.route('/')
def home():
    return "Bot is Alive!"

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

def main_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("🎥 ভিডিও ডাউনলোড"), KeyboardButton("📄 PDF এডিটর")],
        [KeyboardButton("🖼 Image to PDF"), KeyboardButton("🔍 QR Code")],
        [KeyboardButton("🤖 AI Chat (Gemini)"), KeyboardButton("🔗 Link Shorten")],
        [KeyboardButton("🗣 Text to Speech"), KeyboardButton("👤 প্রোফাইল")]
    ], resize_keyboard=True, is_persistent=True)

async def call_gemini(text):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    data = {"contents": [{"parts": [{"text": text}]}]}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=data, headers=headers, timeout=40)
            result = response.json()
            return result['candidates'][0]['content']['parts'][0]['text']
        except: return "❌ এআই উত্তর দিতে পারছে না।"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🔥 স্বাগতম {update.effective_user.first_name}!", reply_markup=main_keyboard())

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
    elif text.startswith("http"):
        context.user_data['url'] = text
        btns = [[InlineKeyboardButton("🎬 Video", callback_data='v'), InlineKeyboardButton("🎵 MP3", callback_data='a')]]
        await update.message.reply_text("🔗 লিংক পাওয়া গেছে!", reply_markup=InlineKeyboardMarkup(btns))
    # ... বাকি ফিচারগুলো আপনার আগের কোড অনুযায়ী কাজ করবে ...

if __name__ == '__main__':
    keep_alive() # Flask স্টার্ট করা
    app = ApplicationBuilder().token(TOKEN).read_timeout(60).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_msg))
    # ... আপনার বাকি হ্যান্ডলারগুলো এখানে দিন ...
    print("🚀 বট সফলভাবে চালু হয়েছে!")
    app.run_polling()