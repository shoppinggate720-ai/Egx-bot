# bot.py - EGX + US Telegram Bot V7 (Fixed)
import json
import logging
import re
import urllib.request
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# إعداد السجلات لمتابعة الأخطاء
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# ⚠️ ضع التوكن الخاص بك بين علامتي التنصيص
TOKEN = "8928961873:AAEzb6NWhEB6XU84WWyTHWKP3U-q93FML8I"

EGX_REAL = {
    "TMGH": 86.98,
    "COMI": 98.45,
    "HRHO": 25.30,
    "KRDI": 0.425,
    "FWRY": 8.90,
    "SWDY": 78.20,
    "ATQA": 14.50,
}


def get_egypt_price(sym):
    sym = sym.upper()
    try:
        url = f"https://www.mubasher.info/markets/EGX/stocks/{sym}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            html = r.read().decode("utf-8", errors="ignore")
            m = re.search(r'"lastPrice"\s*:\s*([0-9.]+)', html)
            if m:
                return float(m.group(1)), "Mubasher Live"
    except Exception as e:
        logging.error(f"Error fetching EGX price for {sym}: {e}")

    if sym in EGX_REAL:
        return EGX_REAL[sym], "EGX Close 30-Sep Real"
    return None, "غير موجود في القائمة أو فشل الاتصال"


def get_us_price(sym):
    sym = sym.upper()
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=1mo&interval=1d"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            j = json.loads(r.read().decode())
            price = float(j["chart"]["result"][0]["meta"]["regularMarketPrice"])
            return price, "Yahoo US Live"
    except Exception as e:
        logging.error(f"Error fetching US price for {sym}: {e}")
        return None, "خطأ في جلب البيانات من Yahoo"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton(
                "🇪🇬 السوق المصري EGX", callback_data="market_1"
            )
        ],
        [
            InlineKeyboardButton(
                "🇺🇸 السوق الامريكي US", callback_data="market_2"
            )
        ],
    ]
    await update.message.reply_text(
        "أهلاً بك! اختر السوق أولاً:\n\n🤖 *EGX Pro Bot V7*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    market = query.data.split("_")[1]
    context.user_data["market"] = market
    name = "المصري EGX" if market == "1" else "الأمريكي US"

    await query.edit_message_text(
        f"تمام، اخترت السوق: *{name}*\n\nالآن أرسل رمز السهم:\nمثال: `TMGH` أو `AAPL`",
        parse_mode="Markdown",
    )


async def change_market(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [
            InlineKeyboardButton(
                "🇪🇬 السوق المصري", callback_data="market_1"
            )
        ],
        [
            InlineKeyboardButton(
                "🇺🇸 السوق الامريكي", callback_data="market_2"
            )
        ],
    ]
    await query.edit_message_text(
        "اختر السوق:", reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    symbol = update.message.text.upper().strip()
    market = context.user_data.get("market", "1")

    # حماية من الأوامر والرموز غير الصحيحة
    if len(symbol) > 10 or not symbol.isalnum():
        await update.message.reply_text("❌ يرجى إدخال رمز سهم صحيح.")
        return

    wait_msg = await update.message.reply_text(f"⏳ جاري جلب سعر {symbol}...")

    if market == "1":
        price, src = get_egypt_price(symbol)
        curr = "EGP"
    else:
        price, src = get_us_price(symbol)
        curr = "USD"

    if price is None:
        await wait_msg.edit_text(
            f"❌ متعذر العثور على {symbol}\nالسبب: {src}\nجرب رمزاً آخر."
        )
        return

    sup = price * 0.94
    res = price * 1.07
    stop = price * 0.92
    t1 = price * 1.05
    t2 = price * 1.10

    recommendation = (
        "شراء تحت 88"
        if symbol == "TMGH" and price < 88
        else "انتظار"
        if price > res * 0.95
        else "تجميع قرب الدعم"
    )

    msg = f"""
📊 *{symbol} | {'EGX' if market=='1' else 'US'}*

💰 السعر: *{price:.2f} {curr}*
📡 المصدر: {src}

📉 الدعم: `{sup:.2f}`
📈 المقاومة: `{res:.2f}`
🛑 وقف الخسارة: `{stop:.2f}` (-8%)
🎯 هدف 1: `{t1:.2f}` (+5%)
🎯 هدف 2: `{t2:.2f}` (+10%)

💡 التوصية: *{recommendation}*

_اضغط /start لتغيير السوق_
"""
    keyboard = [
        [InlineKeyboardButton("🔄 تغيير السوق", callback_data="change")]
    ]

    await wait_msg.edit_text(
        msg,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


if __name__ == "__main__":
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^market_"))
    app.add_handler(CallbackQueryHandler(change_market, pattern="^change$"))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler)
    )

    print("Bot is running...")
    app.run_polling()
  
