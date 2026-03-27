"""
Конфигурация бота записи в салон красоты.
Все параметры из .env файла.
"""
from os import getenv
from dotenv import load_dotenv

load_dotenv()

# ── Telegram ──────────────────────────────────────────────────
TOKEN = getenv("BOT_TOKEN", "your_token_here")
ADMIN_ID = int(getenv("ADMIN_ID", "123456789"))

# ── Канал для обязательной подписки ──────────────────────────
# CHANNEL_ID: числовой ID канала (например -1001234567890)
# CHANNEL_LINK: публичная ссылка (https://t.me/yourchannel)
CHANNEL_ID = getenv("CHANNEL_ID", "")          # обязательно заполнить
CHANNEL_LINK = getenv("CHANNEL_LINK", "https://t.me/yourchannel")
CHANNEL_NAME = getenv("CHANNEL_NAME", "наш канал")  # для текста

# ── База данных ───────────────────────────────────────────────
DB_PATH = getenv("DB_PATH", "beauty_bot.db")

# ── Часовой пояс ─────────────────────────────────────────────
TIMEZONE = getenv("TIMEZONE", "Europe/Moscow")

# ── Логи ─────────────────────────────────────────────────────
LOG_FILE = getenv("LOG_FILE", "beauty_bot.log")

# ── Контакты салона (показываются в разделе "Контакты") ───────
SALON_NAME = getenv("SALON_NAME", "Nail Studio")
SALON_ADDRESS = getenv("SALON_ADDRESS", "г. Москва, ул. Примерная, д. 1")
SALON_PHONE = getenv("SALON_PHONE", "+7 (999) 123-45-67")
SALON_ADMIN_USERNAME = getenv("SALON_ADMIN_USERNAME", "admin")  # без @
SALON_WORK_HOURS = getenv("SALON_WORK_HOURS", "Пн-Сб 10:00–20:00")

# ── Расписание на сколько дней вперёд показывать ─────────────
BOOKING_DAYS_AHEAD = int(getenv("BOOKING_DAYS_AHEAD", "14"))
