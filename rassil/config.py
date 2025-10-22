"""
Конфигурационный файл для Telegram бота "Eldorado Trade"
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot настройки
BOT_TOKEN = os.getenv('BOT_TOKEN', '')
CHANNEL_ID = os.getenv('CHANNEL_ID', '')  # ID закрытого канала (например: -1001234567890)
ADMIN_IDS = [int(id.strip()) for id in os.getenv('ADMIN_IDS', '').split(',') if id.strip()]

# База данных
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://user:password@localhost:5432/eldorado_bot')

# Интервалы напоминаний (в секундах)
REMINDER_INTERVALS = {
    'reminder_3min': 3 * 60,      # 3 минуты
    'reminder_10min': 10 * 60,    # 10 минут
    'reminder_30min': 30 * 60,    # 30 минут
    'reminder_9hours': 9 * 3600   # 9 часов
}

# Тексты по умолчанию
WELCOME_MESSAGE = """👋 <b>Добро пожаловать!</b>

Это бот для получения важных уведомлений и рассылок.

Нажмите кнопку "Ок ✅" ниже, чтобы зарегистрироваться для получения рассылок! 👇"""

DEFAULT_REMINDER_TEXT = """⏰ Напоминание!

Вы еще не подписались на наш канал. Не упустите важные обновления!

Нажмите на кнопку "ОК 🔥" ниже 👇"""

# Текст приветствия для новых участников канала (по умолчанию)
DEFAULT_GREETING_MESSAGE = """👋 <b>Добро пожаловать в наш канал!</b>

Рады видеть вас среди участников! 

Здесь вы будете получать:
• Важные оповещения
• Актуальные новости
• Полезные материалы

Оставайтесь с нами! 🎉"""

# Настройки логирования
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')


