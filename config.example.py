# Copy this file to config.py and fill in real values. config.py is gitignored
# and must NEVER be committed — it holds the bot token. On the server it lives
# at /home/upayztec/wings-gold-bot/config.py and is preserved across deploys.

BOT_TOKEN = "PUT-YOUR-BOTFATHER-TOKEN-HERE"
CHANNEL_ID = "@wingsgoldclub"

# Set to True once client approves and bot is ready to post to the channel
SEND_TO_CHANNEL = False

# Personal recipients — always receive a copy
PERSONAL_RECIPIENTS = [
    "-5184902253",  # WGC Bots group (testing & approval)
]

STATE_DIR = "state"

# --- Forex Factory polling ---------------------------------------------------
# FF's CDN returns 429 on sub-minute polling, so we adapt how often we really
# hit it. The --watch cron still runs every minute (cheap; serves cache), but
# FF itself is fetched at most every FF_CACHE_TTL_SECONDS normally, tightening
# to FF_HOT_CACHE_TTL_SECONDS only inside HOT_WINDOW_MIN around a scheduled
# release — when a fresh `actual` actually matters.
FF_CACHE_TTL_SECONDS = 300        # cold path (~5 min between real fetches)
FF_HOT_CACHE_TTL_SECONDS = 90     # near a release (~90s between real fetches)
HOT_WINDOW_MIN = 30               # minutes after release to stay on the hot path

# --- Morning alert -----------------------------------------------------------
# Hour (SGT, 24h) at/after which the daily news summary fires. The --watch loop
# self-gates on this in Asia/Singapore time, so it is immune to the server clock
# (the box runs US/Eastern) and to DST drift — unlike a fixed cron hour.
MORNING_ALERT_HOUR_SGT = 12

# --- Post-release analysis ---------------------------------------------------
# Wait this long after an event's scheduled time before expecting an `actual`.
POST_RELEASE_DELAY_MIN = 1
# Hard cut-off: stop waiting for an `actual` this long after release. As long as
# FF publishes the number within this window, the analysis is sent — even if it
# arrives late.
POST_RELEASE_EXPIRE_MIN = 360
