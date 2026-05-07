import os
import sqlite3
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ---------------- CONFIG ----------------
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("BOT_TOKEN is not set in environment variables")

bot_username = "YourBotUsername"  # change this
ADMIN_ID = 123456789  # change this

# ---------------- DATABASE ----------------
conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    balance INTEGER,
    referrals INTEGER,
    accepted_policy INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    product TEXT,
    status TEXT
)
""")

conn.commit()

# ---------------- HELPERS ----------------
def get_user(user_id):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    return cursor.fetchone()

def create_user(user_id):
    if not get_user(user_id):
        cursor.execute(
            "INSERT INTO users VALUES (?, ?, ?, ?)",
            (user_id, 0, 0, 0)
        )
        conn.commit()

# ---------------- PRODUCTS ----------------
products = {
    "vip": 50,
    "gold": 80,
    "basic": 10
}

# ---------------- COMMANDS ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    args = context.args

    create_user(user_id)

    if args:
        ref_id = args[0].replace("ref_", "")
        if ref_id != user_id and get_user(ref_id):
            cursor.execute("""
                UPDATE users 
                SET referrals = referrals + 1, balance = balance + 5 
                WHERE user_id=?
            """, (ref_id,))
            conn.commit()

    keyboard = [
        ["💵 wallet", "🛒 store"],
        ["🔗 referral", "🏆 leaderboard"],
        ["📜 policy", "📦 orders"]
    ]

    await update.message.reply_text(
        "🔥 Welcome to Pro Shop Bot",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

async def wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    user = get_user(user_id)

    await update.message.reply_text(
        f"💵 WALLET\n\nBalance: {user[1]} USDT\nReferrals: {user[2]}"
    )

async def referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    link = f"https://t.me/{bot_username}?start=ref_{user_id}"

    await update.message.reply_text(f"🔗 Referral Link:\n{link}")

async def policy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)

    cursor.execute(
        "UPDATE users SET accepted_policy=1 WHERE user_id=?",
        (user_id,)
    )
    conn.commit()

    await update.message.reply_text("📜 Policy accepted ✅")

async def store(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "🛒 STORE\n\n"
    for k, v in products.items():
        msg += f"{k.upper()} - {v} USDT\n"

    await update.message.reply_text(msg)

async def orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)

    cursor.execute(
        "SELECT product, status FROM orders WHERE user_id=?",
        (user_id,)
    )
    data = cursor.fetchall()

    if not data:
        await update.message.reply_text("📦 No orders yet.")
        return

    msg = "📦 ORDERS\n\n"
    for d in data:
        msg += f"{d[0]} - {d[1]}\n"

    await update.message.reply_text(msg)

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor.execute("""
        SELECT user_id, referrals 
        FROM users 
        ORDER BY referrals DESC 
        LIMIT 5
    """)
    data = cursor.fetchall()

    msg = "🏆 LEADERBOARD\n\n"
    rank = 1

    for d in data:
        msg += f"{rank}. {d[0]} - {d[1]} refs\n"
        rank += 1

    await update.message.reply_text(msg)

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    text = update.message.text.lower()

    create_user(user_id)
    user = get_user(user_id)

    if text == "💵 wallet":
        await wallet(update, context)

    elif text == "🔗 referral":
        await referral(update, context)

    elif text == "📜 policy":
        await policy(update, context)

    elif text == "🛒 store":
        await store(update, context)

    elif text == "🏆 leaderboard":
        await leaderboard(update, context)

    elif text == "📦 orders":
        await orders(update, context)

    elif text in products:
        if user[3] == 0:
            await update.message.reply_text("❌ Accept policy first")
            return

        price = products[text]

        if user[1] >= price:
            cursor.execute(
                "UPDATE users SET balance = balance - ? WHERE user_id=?",
                (price, user_id)
            )
            cursor.execute(
                "INSERT INTO orders (user_id, product, status) VALUES (?, ?, ?)",
                (user_id, text, "completed")
            )
            conn.commit()

            await update.message.reply_text(f"✅ Purchased {text.upper()}")
        else:
            await update.message.reply_text("❌ Not enough balance")

# ---------------- MAIN ----------------
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

    app.run_polling()

if __name__ == "__main__":
    main()
