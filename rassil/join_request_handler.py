"""
Обработчик заявок на вступление в канал
"""
import logging
from telegram import Update, ChatJoinRequest, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError
from database import get_db, User
from config import CHANNEL_ID, WELCOME_MESSAGE, VERIFICATION_MESSAGE

logger = logging.getLogger(__name__)


async def send_greeting_message(context: ContextTypes.DEFAULT_TYPE, user_chat_id: int):
    """
    Отправить приветственное сообщение пользователю
    
    Args:
        context: Контекст бота
        user_chat_id: Chat ID пользователя для отправки
    """
    try:
        # Отправляем приветственное сообщение
        await context.bot.send_message(
            chat_id=user_chat_id,
            text=WELCOME_MESSAGE,
            parse_mode='HTML'
        )
        
        # Создаем кнопку "Я человек" для отправки в чат
        keyboard = [[KeyboardButton("✅ Я человек!")]]
        reply_markup = ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
            one_time_keyboard=True
        )
        
        # Отправляем сообщение с кнопкой верификации
        await context.bot.send_message(
            chat_id=user_chat_id,
            text=VERIFICATION_MESSAGE,
            reply_markup=reply_markup
        )
        
        logger.info(f"Приветственное сообщение отправлено пользователю {user_chat_id}")
        
    except TelegramError as e:
        logger.error(f"Telegram ошибка при отправке приветствия пользователю {user_chat_id}: {e}")
    except Exception as e:
        logger.error(f"Ошибка при отправке приветствия пользователю {user_chat_id}: {e}")


async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Автоматическое принятие заявок на вступление в канал
    
    Автоматически принимает все заявки и отправляет приветственное сообщение
    """
    join_request: ChatJoinRequest = update.chat_join_request
    user_id = join_request.from_user.id
    chat_id = join_request.chat.id
    user = join_request.from_user
    
    # Проверяем, что это наш канал
    if CHANNEL_ID and str(chat_id) != str(CHANNEL_ID):
        logger.info(f"Заявка в неизвестный канал {chat_id}, игнорируем")
        return
    
    logger.info(f"Получена заявка на вступление в канал от пользователя {user_id} (@{user.username})")
    
    try:
        # Автоматически принимаем заявку
        await context.bot.approve_chat_join_request(
            chat_id=chat_id,
            user_id=user_id
        )
        logger.info(f"✅ Заявка пользователя {user_id} автоматически принята")
        
        # Получаем chat_id пользователя для отправки сообщения
        # Сначала проверяем, есть ли пользователь в БД
        db = get_db()
        try:
            db_user = db.query(User).filter_by(user_id=user_id).first()
            user_chat_id = db_user.chat_id if db_user else user_id
        finally:
            db.close()
        
        # Отправляем приветственное сообщение
        await send_greeting_message(context, user_chat_id)
        
    except TelegramError as e:
        logger.error(f"Telegram ошибка при обработке заявки пользователя {user_id}: {e}")
    except Exception as e:
        logger.error(f"Ошибка при обработке заявки пользователя {user_id}: {e}")


