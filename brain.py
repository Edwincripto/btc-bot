import sys
print("🚀 СКРИПТ ЗАПУЩЕН!", file=sys.stderr)
sys.stdout.flush()
sys.stderr.flush()

import requests
import pandas as pd
import time
from datetime import datetime
from telegram import Bot
import asyncio

print("📦 БИБЛИОТЕКИ ЗАГРУЖЕНЫ", file=sys.stderr)

TELEGRAM_TOKEN = "8222832200:AAF9ySyA1QEb-QLKMFk832k2CjQvtj9_4DQ"
TELEGRAM_CHAT_ID = "386048422"

print(f"🤖 ТОКЕН: {TELEGRAM_TOKEN[:10]}...", file=sys.stderr)

async def send_telegram(message):
    try:
        bot = Bot(token=TELEGRAM_TOKEN)
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        print("✅ Сообщение отправлено в Telegram", file=sys.stderr)
    except Exception as e:
        print(f"❌ Ошибка Telegram: {e}", file=sys.stderr)

# ОСТАЛЬНОЙ КОД (всё, что было раньше, но с print в stderr)
# ... 
