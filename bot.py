import os
import time
import math
import requests
from datetime import datetime, timezone

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("Railway Variables ішіне BOT_TOKEN қос!")

TG = f"https://api.telegram.org/bot{TOKEN}"
YAHOO = "https://query1.finance.yahoo.com/v8/finance/chart/"

ASSETS = {
    "BTC-USD": "₿ Bitcoin",
    "ETH-USD": "◆ Ethereum",
    "SOL-USD": "◎ Solana",
    "XRP-USD": "✕ XRP",
    "EURUSD=X": "🇪🇺 EUR/USD",
    "GBPUSD=X": "🇬🇧 GBP/USD",
    "JPY=X": "🇯🇵 USD/JPY",
    "AUDUSD=X": "🇦🇺 AUD/USD",
    "NZDUSD=X": "🇳🇿 NZD/USD",
    "CAD=X": "🇨🇦 USD/CAD",
    "CHF=X": "🇨🇭 USD/CHF",
    "GC=F": "🥇 Gold",
    "SI=F": "🥈 Silver",
    "CL=F": "🛢️ Oil WTI",
    "BZ=F": "🛢️ Oil Brent",
    "NG=F": "🔥 Natural Gas",
}

FRAMES = {
    "1m": ("1 минут", "1m"),
    "5m": ("5 минут", "5m"),
    "15m": ("15 минут", "15m"),
    "1h": ("1 сағат", "60m"),
}

def tg(method, payload=None):
    r = requests.post(
        f"{TG}/{method}",
        json=payload or {},
        timeout=30
    )
    r.raise_for_status()
    data = r.json()
    if not data.get("ok"):
        raise RuntimeError(str(data))
    return data["result"]

def send(chat_id, text, keyboard=None):
    data = {"chat_id": chat_id, "text": text}
    if keyboard:
        data["reply_markup"] = {"inline_keyboard": keyboard}
    tg("sendMessage", data)

def buttons(items, prefix, per_row=2):
    rows = []
    row = []
    for key, label in items:
        row.append({
            "text": label,
            "callback_data": f"{prefix}:{key}"
        })
        if len(row) == per_row:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return rows

def menu(chat_id):
    send(
        chat_id,
        "📊 HysCheckOlymo\n\n"
        "Активті таңда да, RSI + EMA көрсеткіштерін "
        "оқу мақсатында талда.\n\n"
        "/signal — талдау\n"
        "/assets — активтер\n"
        "/help — көмек",
        [[{"text": "📈 Талдауды бастау", "callback_data": "start_signal"}],
         [{"text": "🌍 Активтер", "callback_data": "show_assets"}]]
    )

def ema(values, period):
    if len(values) < period:
        return None
    result = sum(values[:period]) / period
    alpha = 2 / (period + 1)
    for value in values[period:]:
        result = alpha * value + (1 - alpha) * result
    return result

def rsi(values, period=14):
    if len(values) <= period:
        return None
    changes = [values[i] - values[i-1]
               for i in range(1, len(values))]
    gains = [max(x, 0) for x in changes]
    losses = [max(-x, 0) for x in changes]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(changes)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    return 100 - 100 / (1 + avg_gain / avg_loss)

def fetch_prices(symbol, interval):
    params = {
        "range": "5d" if interval in ("5m", "15m", "60m") else "1d",
        "interval": interval,
    }
    response = requests.get(
        YAHOO + requests.utils.quote(symbol, safe="=^"),
        params=params,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=20,
    )
    response.raise_for_status()
    result = response.json()["chart"]
    if result.get("error"):
        raise ValueError("Дерек көзі қате қайтарды")

    data = result["result"]
    if not data:
        raise ValueError("Бұл активке дерек жоқ")

    timestamps = data[0].get("timestamp", [])
    closes = data[0]["indicators"]["quote"][0].get("close", [])
    pairs = [
        (ts, float(price))
        for ts, price in zip(timestamps, closes)
        if price is not None and math.isfinite(float(price))
    ]

    if len(pairs) < 30:
        raise ValueError("RSI/EMA үшін дерек жеткіліксіз")

    return pairs

def analyze(symbol, interval):
    pairs = fetch_prices(symbol, interval)
    prices = [price for _, price in pairs]
    last_price = prices[-1]

    r = rsi(prices)
    e9 = ema(prices, 9)
    e21 = ema(prices, 21)

    if r is None or e9 is None or e21 is None:
        raise ValueError("Индикатор есептеу үшін дерек жеткіліксіз")

    # Бұл - эвристикалық индикаторлық ұпай,
    # нақты ықтималдық немесе сауда табысының болжамы емес.
    ema_component = max(-1, min(1, (e9 / e21 - 1) * 500))
    rsi_component = max(-1, min(1, (r - 50) / 20))
    score = 0.6 * ema_component + 0.4 * rsi_component

    up_score = round(50 + 50 * score)
    down_score = 100 - up_score

    if score > 0.12:
        bias = "Жоғары бағытқа бейімділік"
    elif score < -0.12:
        bias = "Төмен бағытқа бейімділік"
    else:
        bias = "Аралас сигнал — айқын бағыт жоқ"

    ts = pairs[-1][0]
    candle_time = datetime.fromtimestamp(
        ts, timezone.utc
    ).strftime("%Y-%m-%d %H:%M UTC")

    return (
        f"📊 HysCheckOlymo\n\n"
        f"Актив: {ASSETS[symbol]}\n"
        f"Таймфрейм: {FRAMES[interval][0]}\n"
        f"Соңғы баға: {last_price:.6g}\n"
        f"Дерек уақыты: {candle_time}\n\n"
        f"RSI(14): {r:.2f}\n"
        f"EMA(9): {e9:.6g}\n"
        f"EMA(21): {e21:.6g}\n\n"
        f"🟢 UP индикаторлық ұпайы: {up_score}/100\n"
        f"🔴 DOWN индикаторлық ұпайы: {down_score}/100\n\n"
        f"Бағалау: {bias}\n\n"
        f"⚠️ Ұпайлар нақты жеңу ықтималдығы емес. "
        f"Бұл дерек Olymp Trade бағасымен, әсіресе OTC "
        f"активтерімен сәйкес келмеуі мүмкін. "
        f"Нақты мәміле ұсынысы емес."
    )

def handle_message(message):
    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip().split()[0].lower() \
        if message.get("text", "").strip() else ""

    if text in ("/start", "/help"):
        menu(chat_id)
    elif text == "/signal":
        send(
            chat_id,
            "🌍 Талдағың келетін активті таңда:",
            buttons(ASSETS.items(), "asset")
        )
    elif text == "/assets":
        send(
            chat_id,
            "Қолжетімді мысал активтер:\n\n" +
            "\n".join(f"• {name} ({symbol})"
                      for symbol, name in ASSETS.items()) +
            "\n\nБұл Olymp Trade-тегі барлық активтің "
            "тізімі емес."
        )
    else:
        send(chat_id, "Команда түсініксіз. /help деп жаз.")

def handle_callback(query):
    data = query.get("data", "")
    chat_id = query["message"]["chat"]["id"]
    callback_id = query["id"]

    tg("answerCallbackQuery", {"callback_query_id": callback_id})

    if data in ("start_signal", "show_assets"):
        send(
            chat_id,
            "🌍 Активті таңда:",
            buttons(ASSETS.items(), "asset")
        )
        return

    if data.startswith("asset:"):
        symbol = data.split(":", 1)[1]
        if symbol not in ASSETS:
            send(chat_id, "Актив табылмады.")
            return

        keyboard = buttons(
            [(key, label) for key, (label, _) in FRAMES.items()],
            f"frame:{symbol}"
        )
        send(
            chat_id,
            f"Таңдалды: {ASSETS[symbol]}\n"
            "🕯️ Таймфреймді таңда:",
            keyboard
        )
        return

    if data.startswith("frame:"):
        _, symbol, interval = data.split(":")
        if symbol not in ASSETS or interval not in FRAMES:
            send(chat_id, "Таңдау қате. /signal деп қайта баста.")
            return

        send(chat_id, "⏳ Нарық деректерін алып, есептеп жатырмын...")
        try:
            report = analyze(symbol, interval)
            send(chat_id, report)
        except Exception as error:
            print("Analysis error:", repr(error))
            send(
                chat_id,
                "❌ Қазір бұл активтің дерегін ала алмадым.\n"
                "Кейінірек қайталап көр немесе басқа актив таңда."
            )

def main():
    offset = None
    print("HysCheckOlymo started")

    while True:
        try:
            params = {"timeout": 25}
            if offset is not None:
                params["offset"] = offset

            response = requests.get(
                f"{TG}/getUpdates",
                params=params,
                timeout=35,
            )
            response.raise_for_status()

            for update in response.json().get("result", []):
                offset = update["update_id"] + 1
                try:
                    if "message" in update:
                        handle_message(update["message"])
                    elif "callback_query" in update:
                        handle_callback(update["callback_query"])
                except Exception as error:
                    print("Update error:", repr(error))

        except Exception as error:
            print("Polling error:", repr(error))
            time.sleep(5)

if __name__ == "__main__":
    main()
