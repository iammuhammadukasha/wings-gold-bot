import requests
from config import BOT_TOKEN, CHANNEL_ID


def send_message(text):
    # type: (str) -> bool
    url = "https://api.telegram.org/bot{}/sendMessage".format(BOT_TOKEN)
    try:
        resp = requests.post(
            url,
            json={"chat_id": CHANNEL_ID, "text": text},
            timeout=15,
        )
        resp.raise_for_status()
        return True
    except Exception as e:
        print("Telegram error: {}".format(e))
        return False
