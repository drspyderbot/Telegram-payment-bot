import logging
import threading
from flask import Flask
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    CallbackQueryHandler, MessageHandler,
    ContextTypes, filters
)

# ---------------- KEEP ALIVE ----------------
app_web = Flask("")

@app_web.route("/")
def home():
    return "Bot is running"

def run_web():
    app_web.run(host="0.0.0.0", port=8080)

threading.Thread(target=run_web).start()

# ---------------- SETTINGS ----------------
TOKEN = "8437819341:AAGqHtxyt23uocPMGCw0gUHufwvM1EMPrVA"
ADMIN_ID = 5371277076
GROUP_ID = -1003430597216

QR_IMAGE_PATH = "qr.jpg"   # <-- your qr file

pending_users = {}

logging.basicConfig(level=logging.INFO)

# ---------------- START ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("I have paid", callback_data="paid")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_photo(
        photo=open(QR_IMAGE_PATH, "rb"),
        caption=
        "💰 PAYMENT DETAILS\n\n"
        "Scan the QR above and pay ₹89\n\n"
        "After payment:\n"
        "1️⃣ Send screenshot\n"
        "2️⃣ Click button below 👇",
        reply_markup=reply_markup
    )
# ---------------- BUTTON ----------------
async def paid_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("📸 Please send your payment screenshot now.")

# ---------------- PHOTO ----------------
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    photo = update.message.photo[-1]

    pending_users[user.id] = True

    await update.message.reply_text("✅ Screenshot received. Waiting for admin approval.")

    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=photo.file_id,
        caption=
        f"💳 Payment Proof\n\nUser ID: {user.id}\nUsername: @{user.username}\n\n/approve {user.id}"
    )

# ---------------- APPROVE ----------------
async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    user_id = int(context.args[0])

    if user_id in pending_users:
        invite = await context.bot.create_chat_invite_link(
            chat_id=GROUP_ID,
            member_limit=1,
            expire_date=datetime.utcnow() + timedelta(minutes=10)
        )

        await context.bot.send_message(
            chat_id=user_id,
            text=f"✅ Approved!\nJoin link (10 min):\n{invite.invite_link}"
        )

        del pending_users[user_id]
        await update.message.reply_text("User approved.")

# ---------------- REJECT ----------------
async def reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    if len(context.args) != 1:
        await update.message.reply_text("Usage: /reject USER_ID")
        return

    user_id = int(context.args[0])

    if user_id in pending_users:
        del pending_users[user_id]

    await context.bot.send_message(
        chat_id=user_id,
        text="❌ Your payment proof was rejected.\n\nPlease send a valid screenshot."
    )

    await update.message.reply_text("User rejected and notified.")

# ----------------- REPLY ----------------
async def reply_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    if len(context.args) < 2:
        await update.message.reply_text("Usage: /reply USER_ID message")
        return

    user_id = int(context.args[0])
    message = " ".join(context.args[1:])

    await context.bot.send_message(chat_id=user_id, text=message)
    await update.message.reply_text("Message sent to user.")

#-------- MAIN ----------------
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("approve", approve))
app.add_handler(CallbackQueryHandler(paid_button))
app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
app.add_handler(CommandHandler("reject", reject))
app.add_handler(CommandHandler("reply", reply_user))

app.run_polling()
