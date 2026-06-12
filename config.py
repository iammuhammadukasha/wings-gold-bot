BOT_TOKEN = "8277424435:AAGdTZjMC8dSMxpXxSl5DK8_5IALs59oYXk"
CHANNEL_ID = "@wingsgoldclub"

# Set to True once client approves and bot is ready to post to the channel
SEND_TO_CHANNEL = False

# Personal recipients — always receive a copy
PERSONAL_RECIPIENTS = [
    "-5184902253",  # WGC Bots group (testing & approval)
]

STATE_DIR = "state"

# --- Forex Factory polling ---------------------------------------------------
# Short TTL so the every-minute --watch job actually sees fresh data each run
# (runs are 60s apart, so a 50s cache is expired by the next tick). The 429
# backoff in ff._fetch_raw still protects us if FF rate-limits.
FF_CACHE_TTL_SECONDS = 50

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
# arrives late. (Previously a 60-min "timeout" permanently skipped the event,
# so a late/missed `actual` meant the analysis never went out at all.)
POST_RELEASE_EXPIRE_MIN = 360
# Kept for backward compatibility with any older cron/invocation.
POST_RELEASE_TIMEOUT_MIN = POST_RELEASE_EXPIRE_MIN
