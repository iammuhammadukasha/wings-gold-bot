import requests
from config import BOT_TOKEN, CHANNEL_ID, SEND_TO_CHANNEL, PERSONAL_RECIPIENTS


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
    """Send to personal recipients always; channel only when SEND_TO_CHANNEL is True."""
    results = []

    if SEND_TO_CHANNEL:
        results.append(_post(CHANNEL_ID, text))

    for uid in PERSONAL_RECIPIENTS:
        results.append(_post(uid, text))

    return any(results)
