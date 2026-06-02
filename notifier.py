import requests
from config import BOT_TOKEN, CHANNEL_ID, PERSONAL_ID


def _post(chat_id, text):
    # type: (str, str) -> bool
    url = "https://api.telegram.org/bot{}/sendMessage".format(BOT_TOKEN)
    try:
        resp = requests.post(
            url,
            json={"chat_id": chat_id, "text": text},
            timeout=15,
        )
        resp.raise_for_status()
        return True
    except Exception as e:
        print("Telegram error ({}): {}".format(chat_id, e))
        return False


def send_message(text):
    # type: (str) -> bool
    """Send to the main channel and a personal copy to PERSONAL_ID."""
    channel_ok = _post(CHANNEL_ID, text)
    personal_ok = _post(PERSONAL_ID, text)
    return channel_ok or personal_ok
