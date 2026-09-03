import requests
import pandas as pd
import time
from datetime import datetime
import telegram

# =============================================
# НАСТРОЙКИ (ПОМЕНЯЙ ТОЛЬКО ТОКЕН)
# =============================================
SYMBOL = "BTCUSDT"
INTERVAL = "15m"          # 15 минут, можно 5m, 1h
LIMIT = 100
RSI_PERIOD = 14
EMA_SHORT = 9
EMA_LONG = 21

# ВСТАВЬ СВОЙ ТОКЕН ОТ @BotFather (вместо "ВАШ_ТОКЕН")
TELEGRAM_TOKEN = "@Edwincrypto_bot"        # например: "123456:ABC-DEF"
TELEGRAM_CHAT_ID = "386648422"      # твой ID, уже вставлен

RISK_PERCENT = 1.5
MAX_POSITION = 1000
# =============================================

def send_telegram(message):
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        try:
            bot = telegram.Bot(token=TELEGRAM_TOKEN)
            bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        except Exception as e:
            print(f"Telegram error: {e}")

def get_klines():
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": SYMBOL, "interval": INTERVAL, "limit": LIMIT}
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

def calculate_rsi(df, period=RSI_PERIOD):
    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    df["rsi"] = 100 - (100 / (1 + rs))
    return df

def calculate_ema(df, period):
    return df["close"].ewm(span=period, adjust=False).mean()

def get_signal(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    df["ema_short"] = calculate_ema(df, EMA_SHORT)
    df["ema_long"] = calculate_ema(df, EMA_LONG)
    df = calculate_rsi(df)
    
    price = last["close"]
    ema_s = last["ema_short"]
    ema_l = last["ema_long"]
    rsi = last["rsi"]
    
    recent_high = df["high"].iloc[-24:].max()
    recent_low = df["low"].iloc[-24:].min()
    
    avg_volume = df["volume"].iloc[-20:].mean()
    last_volume = last["volume"]
    volume_spike = last_volume > avg_volume * 1.5
    
    signals = []
    signal_type = "HOLD"
    stop = 0
    take = 0
    
    buy_score = 0
    if prev["ema_short"] <= prev["ema_long"] and ema_s > ema_l:
        buy_score += 2
        signals.append("✅ EMA9 пересекла EMA21 вверх")
    if rsi < 35:
        buy_score += 1
        signals.append(f"📈 RSI = {rsi:.1f} (перепроданность)")
    if price <= recent_low * 1.005:
        buy_score += 1
        signals.append(f"🛡️ Цена у поддержки {recent_low:.0f}")
    if volume_spike:
        buy_score += 1
        signals.append("📊 Всплеск объема")
    
    sell_score = 0
    if prev["ema_short"] >= prev["ema_long"] and ema_s < ema_l:
        sell_score += 2
        signals.append("❌ EMA9 пересекла EMA21 вниз")
    if rsi > 65:
        sell_score += 1
        signals.append(f"📉 RSI = {rsi:.1f} (перекупленность)")
    if price >= recent_high * 0.995:
        sell_score += 1
        signals.append(f"🔴 Цена у сопротивления {recent_high:.0f}")
    
    if buy_score >= 3:
        signal_type = "BUY"
        stop = price - (price - recent_low) * 0.7
        take = price + (recent_high - price) * 0.6
        if take > recent_high:
            take = recent_high * 0.995
        verdict = f"🟢 ПОКУПКА\nВход: {price:.0f}\nСтоп: {stop:.0f}\nТейк: {take:.0f}\nРиск: {(price-stop)/price*100:.2f}%"
    elif sell_score >= 3:
        signal_type = "SELL"
        stop = price + (recent_high - price) * 0.7
        take = price - (price - recent_low) * 0.6
        if take < recent_low:
            take = recent_low * 1.005
        verdict = f"🔴 ПРОДАЖА (шорт)\nВход: {price:.0f}\nСтоп: {stop:.0f}\nТейк: {take:.0f}\nРиск: {(stop-price)/price*100:.2f}%"
    else:
        verdict = "⚪ НЕТ СИГНАЛА — жди"
    
    return {
        "price": price,
        "rsi": rsi,
        "ema_short": ema_s,
        "ema_long": ema_l,
        "support": recent_low,
        "resistance": recent_high,
        "volume_spike": volume_spike,
        "signals": signals,
        "verdict": verdict,
        "signal_type": signal_type,
        "stop": stop,
        "take": take
    }

def format_message(result):
    lines = []
    lines.append(f"🤖 BTC/USDT | {INTERVAL}")
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
        send_telegram(msg)
    except Exception as e:
        error_msg = f"❌ Ошибка: {e}"
        print(error_msg)
        send_telegram(error_msg)

if __name__ == "__main__":
    print("🤖 МОЗГ ЗАПУЩЕН! Ожидаю сигналы...")
    send_telegram("✅ Бот подключен! Жду сигналы...")
    print("Нажми Ctrl+C для остановки")
    print("=" * 50)
    while True:
        main()
        time.sleep(300)