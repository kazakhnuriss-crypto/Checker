import os
import time
import requests

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN айнымалысы орнатылмаған")

API = f"https://api.telegram.org/bot{TOKEN}"
ASSETS = {
    "BTC/USD": "Bitcoin / АҚШ доллары",
    "ETH/USD": "Ethereum / АҚШ доллары",
    "EUR/USD": "Еуро / АҚШ доллары",
    "GBP/USD": "Фунт / АҚШ доллары",
    "USD/JPY": "АҚШ доллары / Жапон иенасы",
    "XAU/USD": "Алтын / АҚШ доллары",
    "OIL": "Мұнай",
}

def send(chat_id, text):
    response = requests.post(
        f"{API}/sendMessage",
        json={"chat_id": chat_id, "text": text},
        timeout=20,
    )
    response.raise_for_status()

def handle(chat_id, command):
    if command in ("/start", "/help"):
        send(chat_id,
            "📊 HysCheckOlymo\n\n"
            "/assets — мысал активтер тізімі\n"
            "/signal — RSI және EMA туралы\n"
            "/about — бот туралы\n\n"
            "Ескерту: бұл оқу нұсқасы. Нақты баға "
            "деректері мен сауда сигналдары жоқ.")
    elif command == "/assets":
        items = "\n".join(
            f"• {symbol} — {name}"
            for symbol, name in ASSETS.items()
        )
        send(chat_id,
            "📈 Мысал активтер:\n\n" + items +
            "\n\nБұл тізім Olymp Trade-тегі барлық "
            "активті немесе OTC бағаларын қамтымайды.")
    elif command == "/signal":
        send(chat_id,
            "📚 RSI + EMA оқу бөлімі\n\n"
            "RSI — баға қозғалысының қарқынын сипаттайды.\n"
            "EMA — бағаның орташа бағытын көрсетеді.\n\n"
            "Екі индикатор да болашақты нақты "
            "болжамайды. Бұл нұсқа нақты нарық "
            "деректерін талдамайды.")
    elif command == "/about":
        send(chat_id,
            "HysCheckOlymo — нарық индикаторларын "
            "үйренуге арналған Telegram бот.\n"
            "Ол Olymp Trade-пен байланыспайды, "
            "сауда ашпайды және пайдаға кепілдік бермейді.")
    else:
        send(chat_id, "Команда табылмады. /help деп көр.")

def main():
    offset = None
    print("HysCheckOlymo іске қосылды")

    while True:
        try:
            params = {"timeout": 25}
            if offset is not None:
                params["offset"] = offset

            data = requests.get(
                f"{API}/getUpdates",
                params=params,
                timeout=35,
            )
            data.raise_for_status()

            for update in data.json().get("result", []):
                offset = update["update_id"] + 1
                message = update.get("message", {})
                chat = message.get("chat", {})
                chat_id = chat.get("id")
                text = message.get("text", "").strip()

                if chat_id and text.startswith("/"):
                    command = text.split()[0].split("@")[0].lower()
                    try:
                        handle(chat_id, command)
                    except Exception as error:
                        print("Хабар жіберу қатесі:", error)

        except Exception as error:
            print("Байланыс қатесі:", error)
            time.sleep(5)

if __name__ == "__main__":
    main()
