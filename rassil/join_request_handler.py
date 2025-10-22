"""
Обработчик заявок на вступление в канал
"""
import logging
from pathlib import Path
from telegram import Update, ChatJoinRequest, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ContextTypes
from telegram.error import TelegramError
from database import get_db, User, BotSettings
from config import CHANNEL_ID

logger = logging.getLogger(__name__)


async def get_greeting_message():
    """Получить приветственное сообщение из БД"""
    db = get_db()
    try:
        greeting_setting = db.query(BotSettings).filter_by(setting_key='greeting_message').first()
        message_text = greeting_setting.setting_value if greeting_setting else "Добро пожаловать в канал! 👋"
        return message_text
    finally:
        db.close()


async def get_greeting_button():
    """Получить настройки кнопки для приветственного сообщения"""
    db = get_db()
    try:
        button_text_setting = db.query(BotSettings).filter_by(setting_key='greeting_button_text').first()
        button_url_setting = db.query(BotSettings).filter_by(setting_key='greeting_button_url').first()
        
        button_text = button_text_setting.setting_value if button_text_setting else None
        button_url = button_url_setting.setting_value if button_url_setting else None
        
        if button_text and button_url:
            return {'text': button_text, 'url': button_url}
        return None
    finally:
        db.close()


async def get_greeting_media():
    """Получить медиа-файлы для приветственного сообщения"""
    db = get_db()
    try:
        media_setting = db.query(BotSettings).filter_by(setting_key='greeting_media_paths').first()
        if media_setting and media_setting.setting_value:
            # Путь к файлам хранится как строка, разделенная запятыми
            paths = media_setting.setting_value.split(',')
            # Проверяем существование файлов
            existing_paths = [path.strip() for path in paths if Path(path.strip()).exists()]
            return existing_paths if existing_paths else None
        return None
    finally:
        db.close()


async def send_greeting_message(context: ContextTypes.DEFAULT_TYPE, user_chat_id: int):
    """
    Отправить приветственное сообщение пользователю
    
    Args:
        context: Контекст бота
        user_chat_id: Chat ID пользователя для отправки
    """
    try:
        # Получаем текст приветствия
        message_text = await get_greeting_message()
        
        # Получаем настройки кнопки
        button_config = await get_greeting_button()
        
        # Получаем медиа-файлы
        media_paths = await get_greeting_media()
        
        # Формируем кнопку, если она настроена
        reply_markup = None
        if button_config:
            keyboard = [[InlineKeyboardButton(button_config['text'], url=button_config['url'])]]
            reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Отправляем сообщение
        if media_paths and len(media_paths) > 0:
            # Отправка с медиа (если есть несколько изображений - отправляем группой)
            if len(media_paths) == 1:
                # Одно изображение - отправляем с текстом и кнопкой
                with open(media_paths[0], 'rb') as photo:
                    await context.bot.send_photo(
                        chat_id=user_chat_id,
                        photo=photo,
                        caption=message_text,
                        parse_mode='HTML',
                        reply_markup=reply_markup
                    )
            else:
                # Несколько изображений - отправляем группой (до 10 штук)
                media_group = []
                for idx, path in enumerate(media_paths[:10]):  # Telegram ограничивает до 10 медиа
                    with open(path, 'rb') as photo:
                        if idx == 0:
                            # Первое изображение с подписью
                            media_group.append(
                                InputMediaPhoto(
                                    media=photo.read(),
                                    caption=message_text,
                                    parse_mode='HTML'
                                )
                            )
                        else:
                            # Остальные без подписи
                            media_group.append(InputMediaPhoto(media=photo.read()))
                
                await context.bot.send_media_group(
                    chat_id=user_chat_id,
                    media=media_group
                )
                
                # Если есть кнопка, отправляем отдельным сообщением
                # (т.к. media_group не поддерживает кнопки)
                if reply_markup:
                    await context.bot.send_message(
                        chat_id=user_chat_id,
                        text="👆",
                        reply_markup=reply_markup
                    )
        else:
            # Отправка только текста с кнопкой
            await context.bot.send_message(
                chat_id=user_chat_id,
                text=message_text,
                parse_mode='HTML',
                reply_markup=reply_markup,
                disable_web_page_preview=True
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


