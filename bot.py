import os, qrcode, asyncio, httpx, fitz, time, re, secrets, string, urllib.parse
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
def home(): return "Ultimate Super Multi-Tasker Bot is Online!"
def run(): app_web.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- কনফিগারেশন ---
TOKEN = "8681613014:AAGhaxmwY5Xv_F1FDDyccUwIqT05WXUAQ3M"
ADMIN_ID = 6365947320

# ডেটা স্টোর
user_images = {}
pdf_edit_files = {}

# --- কিবোর্ড মেনুসমূহ ---
def main_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("📱 ভিডিও ডাউনলোড"), KeyboardButton("📂 Office টুলস")],
        [KeyboardButton("📄 PDF টুলস"), KeyboardButton("🖼 ইমেজ এডিটর")],
        [KeyboardButton("🎨 AI ছবি তৈরি"), KeyboardButton("🗣 ভয়েস মেসেজ")],
        [KeyboardButton("🔍 QR & Link"), KeyboardButton("🛠 এক্সট্রা টুলস")],
        [KeyboardButton("👤 প্রোফাইল")]
    ], resize_keyboard=True, is_persistent=True)

def image_tools_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Format Change", callback_data='img_format'), InlineKeyboardButton("🎨 সাদাকালো", callback_data='img_bw')],
        [InlineKeyboardButton("🌫 স্কেচ (Sketch)", callback_data='img_sketch'), InlineKeyboardButton("🖼 ছবি থেকে PDF", callback_data='convert_img_pdf')]
    ])

def office_tools_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Word (.docx)", callback_data='off_word')],
        [InlineKeyboardButton("📊 Excel (.xlsx)", callback_data='off_excel')],
        [InlineKeyboardButton("📽 PPT (.pptx)", callback_data='off_ppt')]
    ])

def extra_tools_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎥 YouTube Thumbnail", callback_data='ex_thumb')],
        [InlineKeyboardButton("💵 কারেন্সি রেট", callback_data='ex_rate')],
        [InlineKeyboardButton("🔐 পাসওয়ার্ড জেনারেটর", callback_data='ex_pass')]
    ])

# --- কমান্ড হ্যান্ডলার ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        f"🚀 **Ultimate Super Bot-এ স্বাগতম!**\nআপনার সব ডিজিটাল সমস্যার সমাধান এখন এক জায়গায়।",
        reply_markup=main_keyboard(), parse_mode="Markdown"
    )

# --- মূল টেক্সট হ্যান্ডলার ---
async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    state = context.user_data.get('state')

    # বাটন ক্লিকে স্টেট রিসেট
    if text in ["📱 ভিডিও ডাউনলোড", "📂 Office টুলস", "📄 PDF টুলস", "🖼 ইমেজ এডিটর", "🎨 AI ছবি তৈরি", "🗣 ভয়েস মেসেজ", "🔍 QR & Link", "🛠 এক্সট্রা টুলস"]:
        context.user_data.clear()

    if text == "🎨 AI ছবি তৈরি":
        context.user_data['state'] = 'WAIT_AI_IMG'
        await update.message.reply_text("✨ **AI Image Generator সক্রিয়!**\nকেমন ছবি চান তার বর্ণনা লিখুন (English):")
    
    elif state == 'WAIT_AI_IMG':
        msg = await update.message.reply_text("⏳ AI ছবি তৈরি করছে... একটু অপেক্ষা করুন।")
        try:
            prompt = urllib.parse.quote(text)
            img_url = f"https://image.pollinations.ai/prompt/{prompt}?width=1024&height=1024&nologo=true"
            await update.message.reply_photo(photo=img_url, caption=f"✅ বর্ণনা: {text}")
        except: await update.message.reply_text("❌ সার্ভার সমস্যা।")
        await msg.delete(); context.user_data.clear()

    elif text == "📱 ভিডিও ডাউনলোড":
        await update.message.reply_text("🎬 ভিডিওর লিংক (FB/IG/YT/TikTok) এখানে পাঠান।")
    
    elif text == "📂 Office টুলস":
        await update.message.reply_text("📑 কি ফাইল তৈরি করতে চান?", reply_markup=office_tools_menu())

    elif text == "🖼 ইমেজ এডিটর":
        user_images[user_id] = []
        await update.message.reply_text("📸 ছবি পাঠান (এডিট করতে বা PDF বানাতে)।")

    elif text == "📄 PDF টুলস":
        await update.message.reply_text("📂 একটি PDF ফাইল পাঠান এডিট করার জন্য।")

    elif text == "🗣 ভয়েস মেসেজ":
        context.user_data['state'] = 'TTS'
        await update.message.reply_text("📝 ভয়েস করার জন্য টেক্সট লিখুন:")

    elif state == 'TTS':
        context.user_data['tts_t'] = text
        btns = [[InlineKeyboardButton("👨 Male", callback_data='tts_m'), InlineKeyboardButton("👩 Female", callback_data='tts_f')]]
        await update.message.reply_text("🎙 ভয়েস জেন্ডার বেছে নিন:", reply_markup=InlineKeyboardMarkup(btns))

    elif text == "🔍 QR & Link":
        btns = [[InlineKeyboardButton("🔍 QR Code", callback_data='m_qr'), InlineKeyboardButton("🔗 Link Short", callback_data='m_short')]]
        await update.message.reply_text("অপশন বেছে নিন:", reply_markup=InlineKeyboardMarkup(btns))

    elif text == "🛠 এক্সট্রা টুলস":
        await update.message.reply_text("🛠 এক্সট্রা টুলস মেনু:", reply_markup=extra_tools_menu())

    elif text == "👤 প্রোফাইল":
        await update.message.reply_text(f"👤 নাম: {update.effective_user.first_name}\n🆔 আইডি: `{user_id}`")

    # সেশন হ্যান্ডলিং (Office/Thumbnail)
    elif state == 'WAIT_WORD':
        doc = Document(); doc.add_paragraph(text); path = f"d_{user_id}.docx"; doc.save(path)
        await update.message.reply_document(document=open(path, 'rb')); os.remove(path); context.user_data.clear()

    elif state == 'WAIT_THUMB':
        vid = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", text)
        if vid: await update.message.reply_photo(photo=f"https://img.youtube.com/vi/{vid.group(1)}/maxresdefault.jpg", caption="✅ Thumbnail!")
        context.user_data.clear()

    elif text.startswith("http"):
        context.user_data['url'] = text
        btns = [[InlineKeyboardButton("🎥 Video", callback_data='dl_v'), InlineKeyboardButton("🎵 MP3", callback_data='dl_a')]]
        await update.message.reply_text("🔗 লিংক পাওয়া গেছে!", reply_markup=InlineKeyboardMarkup(btns))

# --- ফাইল হ্যান্ডলার ---
async def handle_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    file = update.message.document or (update.message.photo[-1] if update.message.photo else None)
    if not file: return

    if update.message.photo or (hasattr(file, 'file_name') and file.file_name.lower().endswith(('.jpg', '.png', '.webp'))):
        f = await (update.message.photo[-1].get_file() if update.message.photo else file.get_file())
        path = f"img_{user_id}.jpg"; await f.download_to_drive(path)
        if user_id not in user_images: user_images[user_id] = []
        user_images[user_id].append(path); context.user_data['img_path'] = path
        await update.message.reply_text("📸 ছবি পাওয়া গেছে!", reply_markup=image_tools_menu())

    elif hasattr(file, 'file_name') and file.file_name.lower().endswith('.pdf'):
        f = await file.get_file(); path = f"e_{user_id}.pdf"; await f.download_to_drive(path)
        pdf_edit_files[user_id] = path
        btns = [[InlineKeyboardButton("🔄 Rotate PDF", callback_data='pdf_rotate'), InlineKeyboardButton("🖼 PDF to Image", callback_data='pdf_to_img')]]
        await update.message.reply_text("📄 PDF পাওয়া গেছে!", reply_markup=InlineKeyboardMarkup(btns))

# --- বাটন অ্যাকশন (Callbacks) ---
async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user_id = query.from_user.id; await query.answer()
    data = query.data

    if data == 'off_word': context.user_data['state'] = 'WAIT_WORD'; await query.message.reply_text("📝 Word ফাইলের টেক্সট দিন:")
    elif data == 'ex_thumb': context.user_data['state'] = 'WAIT_THUMB'; await query.message.reply_text("🎥 YT লিংক দিন:")
    elif data == 'ex_pass':
        pwd = ''.join(secrets.choice(string.ascii_letters + string.digits) for i in range(12))
        await query.message.reply_text(f"🔐 পাসওয়ার্ড: `{pwd}`", parse_mode="Markdown")

    elif data.startswith('img_'):
        p = context.user_data.get('img_path')
        img = Image.open(p)
        if data == 'img_bw': img = ImageOps.grayscale(img)
        elif data == 'img_sketch': img = img.filter(ImageFilter.CONTOUR)
        out = f"res_{user_id}.jpg"; img.save(out)
        await context.bot.send_document(chat_id=user_id, document=open(out, 'rb')); os.remove(out)

    elif data == 'convert_img_pdf':
        imgs = [Image.open(f).convert('RGB') for f in user_images[user_id]]
        out = f"doc_{user_id}.pdf"; imgs[0].save(out, save_all=True, append_images=imgs[1:])
        await context.bot.send_document(chat_id=user_id, document=open(out, 'rb'))
        for f in user_images[user_id]: os.remove(f); del user_images[user_id]

    elif data == 'pdf_rotate':
        p = pdf_edit_files.get(user_id)
        reader = PdfReader(p); writer = PdfWriter()
        for pg in reader.pages: writer.add_page(pg); writer.pages[-1].rotate(90)
        out = f"rot_{user_id}.pdf"
        with open(out, "wb") as f: writer.write(f)
        await context.bot.send_document(chat_id=user_id, document=open(out, 'rb')); os.remove(out)

    elif data in ['dl_v', 'dl_a']:
        url = context.user_data.get('url'); mode = 'v' if data == 'dl_v' else 'a'
        await query.edit_message_text("⏳ ডাউনলোড হচ্ছে...")
        opts = {'format': 'best', 'outtmpl': '%(title)s.%(ext)s', 'max_filesize': 48*1024*1024}
        if mode == 'a': opts['postprocessors'] = [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3'}]
        try:
            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True); p = ydl.prepare_filename(info)
                if mode == 'a': p = p.rsplit('.', 1)[0] + ".mp3"
                await context.bot.send_document(chat_id=user_id, document=open(p, 'rb')); os.remove(p)
        except: await query.message.reply_text("❌ ব্যর্থ!")

    elif data.startswith('tts_'):
        txt = context.user_data.get('tts_t'); slow = True if data == 'tts_m' else False
        out = f"v_{user_id}.mp3"; gTTS(text=txt, lang='bn', slow=slow).save(out)
        await context.bot.send_audio(chat_id=user_id, audio=open(out, 'rb')); os.remove(out)

if __name__ == '__main__':
    keep_alive()
    app = ApplicationBuilder().token(TOKEN).read_timeout(150).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_msg))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, handle_files))
    app.add_handler(CallbackQueryHandler(callback))
    print("🚀 Ultimate Bot is LIVE!")
    app.run_polling()
