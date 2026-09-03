import requests
import pandas as pd
import time
from datetime import datetime
from telegram import Bot
import asyncio

TELEGRAM_TOKEN = "8222832200:AAF9ySyA1QEb-QLKMFk832k2CjQvtj9_4DQ"
TELEGRAM_CHAT_ID = "386048422"

async def send_telegram(message):
    try:
        bot = Bot(token=TELEGRAM_TOKEN)
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        print("✅ Сообщение отправлено в Telegram")
    except Exception as e:
        print("❌ Ошибка Telegram:", e)

def get_klines():
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": "BTCUSDT", "interval": "15m", "limit": 100}
    resp = requests.get(url, params=params)
    data = resp.json()
    df = pd.DataFrame(data, columns=[
        "time", "open", "high", "low", "close", "volume",
        "close_time", "quote_volume", "trades", "taker_base", "taker_quote", "ignore"
    ])
    df["close"] = df["close"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    df["volume"] = df["volume"].astype(float)
    return df

def calculate_rsi(df, period=14):
    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    df["rsi"] = 100 - (100 / (1 + rs))
    return df

def calculate_ema(df, period):
    return df["close"].ewm(span=period, adjust=False).mean()

def get_signal(df):
    # Проверяем, что данных достаточно
    if len(df) < 3:
        return {
            "price": df["close"].iloc[-1],
            "rsi": 50,
            "ema_short": df["close"].iloc[-1],
            "ema_long": df["close"].iloc[-1],
            "support": df["low"].iloc[-1],
            "resistance": df["high"].iloc[-1],
            "signals": ["⚠️ Недостаточно данных для анализа"],
            "verdict": "⚪ НЕТ СИГНАЛА — жди"
        }

    df["ema_short"] = calculate_ema(df, 9)
    df["ema_long"] = calculate_ema(df, 21)
    df = calculate_rsi(df)

    last = df.iloc[-1]
    prev = df.iloc[-2]

    price = last["close"]
    ema_s = last["ema_short"]
    ema_l = last["ema_long"]
    rsi = last["rsi"]

    recent_high = df["high"].iloc[-24:].max()
    recent_low = df["low"].iloc[-24:].min()

    buy_score = 0
    sell_score = 0
    signals = []

    if prev["ema_short"] <= prev["ema_long"] and ema_s > ema_l:
        buy_score += 2
        signals.append("✅ EMA9 пересекла EMA21 вверх")
    if rsi < 35:
        buy_score += 1
        signals.append(f"📈 RSI = {rsi:.1f} (перепроданность)")
    if price <= recent_low * 1.005:
        buy_score += 1
        signals.append(f"🛡️ Цена у поддержки {recent_low:.0f}")

    if prev["ema_short"] >= prev["ema_long"] and ema_s < ema_l:
        sell_score += 2
        signals.append("❌ EMA9 пересекла EMA21 вниз")
    if rsi > 65:
        sell_score += 1
        signals.append(f"📉 RSI = {rsi:.1f} (перекупленность)")
    if price >= recent_high * 0.995:
        sell_score += 1
        signals.append(f"🔴 Цена у сопротивления {recent_high:.0f}")

    verdict = "⚪ НЕТ СИГНАЛА — жди"
    if buy_score >= 3:
        stop = price - (price - recent_low) * 0.7
        take = price + (recent_high - price) * 0.6
        verdict = f"🟢 ПОКУПКА\nВход: {price:.0f}\nСтоп: {stop:.0f}\nТейк: {take:.0f}"
    elif sell_score >= 3:
        stop = price + (recent_high - price) * 0.7
        take = price - (price - recent_low) * 0.6
        verdict = f"🔴 ПРОДАЖА\nВход: {price:.0f}\nСтоп: {stop:.0f}\nТейк: {take:.0f}"

    return {
        "price": price,
        "rsi": rsi,
        "ema_short": ema_s,
        "ema_long": ema_l,
        "support": recent_low,
        "resistance": recent_high,
        "signals": signals,
        "verdict": verdict,
    }

def format_message(result):
    lines = []
    lines.append(f"🤖 BTC/USDT | 15m")
    lines.append(f"⏰ {datetime.now().strftime('%H:%M:%S')}")
    lines.append("─" * 30)
    lines.append(f"💰 Цена: {result['price']:.0f}")
    lines.append(f"📊 RSI: {result['rsi']:.1f}")
    lines.append(f"📈 EMA9: {result['ema_short']:.0f} | EMA21: {result['ema_long']:.0f}")
    lines.append(f"🛡️ Поддержка: {result['support']:.0f}")
    lines.append(f"🔴 Сопротивление: {result['resistance']:.0f}")
    if result['signals']:
        lines.append("─" * 30)
        for s in result['signals']:
            lines.append(f"🔔 {s}")
    lines.append("─" * 30)
    lines.append(f"🎯 {result['verdict']}")
    lines.append("─" * 30)
    lines.append("⚠️ Решение за тобой! Ты — руки и глаза.")
    return "\n".join(lines)

def main():
    try:
        df = get_klines()
        result = get_signal(df)
        msg = format_message(result)
        print(msg)
        print("=" * 50)
        asyncio.run(send_telegram(msg))
    except Exception as e:
        error_msg = f"❌ Ошибка: {e}"
        print(error_msg)
        asyncio.run(send_telegram(error_msg))

if __name__ == "__main__":
    print("🤖 ТОРГОВЫЙ МОЗГ ЗАПУЩЕН!")
    asyncio.run(send_telegram("✅ Торговый бот запущен и анализирует рынок!"))
    print("Нажми Ctrl+C для остановки")
    print("=" * 50)
    while True:
        main()
        time.sleep(300)
