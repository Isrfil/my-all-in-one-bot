import os, qrcode, asyncio, httpx, fitz, time
from pypdf import PdfReader, PdfWriter
from yt_dlp import YoutubeDL
from PIL import Image, ImageOps, ImageFilter
from gtts import gTTS
import pyshorteners
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from flask import Flask
from threading import Thread

# --- Flask Server (বটকে ২৪ ঘণ্টা সচল রাখতে) ---
app_web = Flask('')
@app_web.route('/')
def home(): return "Multi-Functional Professional Bot is Online!"
def run(): app_web.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- কনফিগারেশন ---
TOKEN = "8681613014:AAGhaxmwY5Xv_F1FDDyccUwIqT05WXUAQ3M"
ADMIN_ID = 6365947320
MAINTENANCE_MODE = False

# ডাটা স্টোর
user_images = {}
pdf_edit_files = {}

# --- মেইন কিবোর্ড (স্থায়ী) ---
def main_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("📱 ভিডিও ডাউনলোড"), KeyboardButton("📄 PDF টুলস")],
        [KeyboardButton("🖼 ইমেজ এডিটর"), KeyboardButton("🗣 ভয়েস মেসেজ")],
        [KeyboardButton("🔍 QR & Link"), KeyboardButton("👤 প্রোফাইল")]
    ], resize_keyboard=True, is_persistent=True)

# --- সাব-মেনু কিবোর্ডসমূহ ---
def image_tools_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 PNG/JPG/WEBP", callback_data='img_format'), InlineKeyboardButton("🎨 সাদাকালো", callback_data='img_bw')],
        [InlineKeyboardButton("🌫 স্কেচ (Sketch)", callback_data='img_sketch'), InlineKeyboardButton("✂️ রিসাইজ", callback_data='img_resize')],
        [InlineKeyboardButton("🖼 ছবি থেকে PDF", callback_data='convert_img_pdf')]
    ])

def video_platforms_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📸 Instagram", callback_data='v_info'), InlineKeyboardButton("📘 Facebook", callback_data='v_info')],
        [InlineKeyboardButton("🎥 YouTube", callback_data='v_info'), InlineKeyboardButton("🎵 TikTok", callback_data='v_info')]
    ])

# --- মূল ফাংশনসমূহ ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    user = update.effective_user.first_name
    await update.message.reply_text(
        f"🔥 **স্বাগতম {user}!**\nআমি আপনার মাল্টি-টাস্কিং অ্যাসিস্ট্যান্ট।\nনিচের মেনু থেকে কাজ শুরু করুন।",
        reply_markup=main_keyboard(), parse_mode="Markdown"
    )

async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    
    if MAINTENANCE_MODE and user_id != ADMIN_ID:
        await update.message.reply_text("⚠️ সার্ভার মেইনটেইনেন্স চলছে। কিছুক্ষণ পর চেষ্টা করুন।")
        return

    # বাটন ক্লিক হ্যান্ডলিং
    if text == "📱 ভিডিও ডাউনলোড":
        await update.message.reply_text("🎬 ভিডিওর লিংক এখানে পেস্ট করুন (FB/IG/YT/TikTok):", reply_markup=video_platforms_menu())
    
    elif text == "📄 PDF টুলস":
        await update.message.reply_text("📂 একটি PDF ফাইল পাঠান এডিট করার জন্য।")

    elif text == "🖼 ইমেজ এডিটর":
        user_images[user_id] = []
        await update.message.reply_text("📸 ছবি পাঠান (একাধিক ছবি পাঠালে ছবি থেকে PDF করা যাবে)।")

    elif text == "🗣 ভয়েস মেসেজ":
        context.user_data['state'] = 'TTS'
        await update.message.reply_text("📝 যে লেখাটি ভয়েস করতে চান তা পাঠান:")

    elif text == "🔍 QR & Link":
        btns = [[InlineKeyboardButton("🔍 QR Code", callback_data='m_qr'), InlineKeyboardButton("🔗 Link Short", callback_data='m_short')]]
        await update.message.reply_text("কি করতে চান?", reply_markup=InlineKeyboardMarkup(btns))

    elif text == "👤 প্রোফাইল":
        await update.message.reply_text(f"👤 নাম: {update.effective_user.first_name}\n🆔 আইডি: `{user_id}`\n🚀 স্ট্যাটাস: প্রিমিয়াম ইউজার", parse_mode="Markdown")

    # স্টেট হ্যান্ডলিং
    elif context.user_data.get('state') == 'TTS':
        context.user_data['tts_text'] = text
        btns = [[InlineKeyboardButton("👨 Male (পুরুষ)", callback_data='tts_male'), InlineKeyboardButton("👩 Female (নারী)", callback_data='tts_female')]]
        await update.message.reply_text("🎙 কোন ভয়েস চান?", reply_markup=InlineKeyboardMarkup(btns))

    elif context.user_data.get('state') == 'QR':
        path = f"qr_{user_id}.png"
        qrcode.make(text).save(path)
        await update.message.reply_photo(photo=open(path, 'rb'), caption="✅ QR Code তৈরি সম্পন্ন!")
        os.remove(path); context.user_data.clear()

    elif context.user_data.get('state') == 'SHORT':
        try:
            s = pyshorteners.Shortener()
            await update.message.reply_text(f"✅ ছোট লিংক: {s.tinyurl.short(text)}")
        except: await update.message.reply_text("❌ ভুল লিংক।")
        context.user_data.clear()

    # লিংক শনাক্তকরণ
    elif text.startswith("http"):
        context.user_data['url'] = text
        btns = [[InlineKeyboardButton("🎥 Video", callback_data='dl_v'), InlineKeyboardButton("🎵 MP3", callback_data='dl_a')]]
        await update.message.reply_text("🔗 লিংক পাওয়া গেছে! কি চান?", reply_markup=InlineKeyboardMarkup(btns))

# --- ফাইল হ্যান্ডলার (Images & PDF) ---
async def handle_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    file = update.message.document or (update.message.photo[-1] if update.message.photo else None)
    if not file: return

    # ছবি হ্যান্ডলার
    if update.message.photo or (hasattr(file, 'file_name') and file.file_name.lower().endswith(('.jpg', '.png', '.webp'))):
        f = await (update.message.photo[-1].get_file() if update.message.photo else file.get_file())
        path = f"img_{user_id}_{int(time.time())}.jpg"
        await f.download_to_drive(path)
        
        if user_id not in user_images: user_images[user_id] = []
        user_images[user_id].append(path)
        context.user_data['img_path'] = path
        
        await update.message.reply_text(f"📸 ছবি পাওয়া গেছে! ({len(user_images[user_id])} টি যুক্ত হয়েছে)", reply_markup=image_tools_menu())

    # পিডিএফ হ্যান্ডলার
    elif hasattr(file, 'file_name') and file.file_name.lower().endswith('.pdf'):
        f = await file.get_file()
        path = f"edit_{user_id}.pdf"
        await f.download_to_drive(path)
        pdf_edit_files[user_id] = path
        btns = [[InlineKeyboardButton("🔄 Rotate PDF", callback_data='pdf_rotate'), InlineKeyboardButton("🖼 PDF to Image", callback_data='pdf_to_img')]]
        await update.message.reply_text("📄 PDF ফাইল পাওয়া গেছে!", reply_markup=InlineKeyboardMarkup(btns))

# --- বাটন একশনস (Callbacks) ---
async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    # ইমেজ প্রসেসিং
    if query.data.startswith('img_'):
        path = context.user_data.get('img_path')
        img = Image.open(path)
        if query.data == 'img_bw': img = ImageOps.grayscale(img)
        elif query.data == 'img_sketch': img = img.filter(ImageFilter.CONTOUR)
        elif query.data == 'img_format': path = path.rsplit('.',1)[0]+".png"; img.save(path, "PNG")
        
        out = f"proc_{user_id}.jpg" if not query.data == 'img_format' else path
        if not query.data == 'img_format': img.save(out)
        else: out = path
        
        await context.bot.send_document(chat_id=user_id, document=open(out, 'rb'), caption="✅ সম্পন্ন!")
        os.remove(out)

    # ছবি থেকে পিডিএফ
    elif query.data == 'convert_img_pdf':
        if user_id in user_images and user_images[user_id]:
            msg = await query.message.reply_text("⏳ পিডিএফ তৈরি হচ্ছে...")
            imgs = [Image.open(f).convert('RGB') for f in user_images[user_id]]
            pdf_path = f"doc_{user_id}.pdf"
            imgs[0].save(pdf_path, save_all=True, append_images=imgs[1:])
            await context.bot.send_document(chat_id=user_id, document=open(pdf_path, 'rb'), caption="✅ PDF রেডি!")
            for f in user_images[user_id]: os.remove(f)
            os.remove(pdf_path); del user_images[user_id]; await msg.delete()

    # পিডিএফ থেকে ছবি
    elif query.data == 'pdf_to_img':
        path = pdf_edit_files.get(user_id)
        doc = fitz.open(path)
        for i in range(len(doc)):
            pix = doc.load_page(i).get_pixmap()
            img_out = f"p{i}_{user_id}.jpg"; pix.save(img_out)
            await context.bot.send_photo(chat_id=user_id, photo=open(img_out, 'rb'))
            os.remove(img_out)
        doc.close(); os.remove(path)

    # ভয়েস জেনারেশন
    elif query.data.startswith('tts_'):
        text = context.user_data.get('tts_text')
        slow = True if query.data == 'tts_male' else False
        out = f"v_{user_id}.mp3"
        gTTS(text=text, lang='bn', slow=slow).save(out)
        await context.bot.send_audio(chat_id=user_id, audio=open(out, 'rb'))
        os.remove(out); context.user_data.clear()

    # ডাউনলোড
    elif query.data in ['dl_v', 'dl_a']:
        url = context.user_data.get('url')
        mode = 'v' if query.data == 'dl_v' else 'a'
        await query.edit_message_text("⏳ ডাউনলোড হচ্ছে...")
        opts = {'format': 'best', 'outtmpl': '%(title)s.%(ext)s', 'max_filesize': 48*1024*1024}
        if mode == 'a': opts['postprocessors'] = [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3'}]
        try:
            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True); path = ydl.prepare_filename(info)
                if mode == 'a': path = path.rsplit('.', 1)[0] + ".mp3"
                await context.bot.send_document(chat_id=user_id, document=open(path, 'rb'), caption="✅ সম্পন্ন!")
                os.remove(path)
        except: await query.message.reply_text("❌ ব্যর্থ!")

    # মেনু নেভিগেশন
    elif query.data == 'm_qr': context.user_data['state'] = 'QR'; await query.message.reply_text("লিংক পাঠান:")
    elif query.data == 'm_short': context.user_data['state'] = 'SHORT'; await query.message.reply_text("বড় লিংক পাঠান:")

if __name__ == '__main__':
    keep_alive()
    app = ApplicationBuilder().token(TOKEN).read_timeout(100).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_msg))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, handle_files))
    app.add_handler(CallbackQueryHandler(callback))
    print("🚀 All-in-One Master Bot is Running...")
    app.run_polling()
