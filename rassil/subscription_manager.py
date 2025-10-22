"""
Менеджер подписок - управление подписками пользователей на канал
"""
import logging
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError, BadRequest
from database import get_db, User, BotSettings
from config import CHANNEL_ID, SUCCESS_MESSAGE_WITH_LINK, SUCCESS_MESSAGE_NO_LINK, ALREADY_SUBSCRIBED_MESSAGE

logger = logging.getLogger(__name__)


async def subscribe_user(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """
    Подписка пользователя на закрытый канал
    
    Args:
        context: Контекст бота
        user_id: ID пользователя
    
    Returns:
        tuple: (success: bool, message: str, reply_markup: InlineKeyboardMarkup or None)
    """
    db = get_db()
    try:
        # Получаем пользователя из базы данных
        user = db.query(User).filter_by(user_id=user_id).first()
        
        if not user:
            logger.error(f"Пользователь {user_id} не найден в базе данных")
            return False, "❌ Произошла ошибка. Попробуйте снова командой /start", None
        
        # Проверяем, не подписан ли пользователь уже
        if user.subscribed:
            logger.info(f"Пользователь {user_id} уже подписан")
            return True, ALREADY_SUBSCRIBED_MESSAGE, None
        
        try:
            # Проверяем, есть ли сохраненная инвайт-ссылка в настройках
            invite_link_setting = db.query(BotSettings).filter_by(setting_key='channel_invite_link').first()
            
            if invite_link_setting and invite_link_setting.setting_value:
                # Используем сохраненную ссылку
                invite_link_url = invite_link_setting.setting_value
                logger.info(f"Используется сохраненная инвайт-ссылка для пользователя {user_id}")
                
                # Помечаем пользователя как подписанного
                user.subscribed = True
                user.subscription_date = datetime.utcnow()
                db.commit()
                
                # Текст сообщения
                success_message = """✅ <b>Отлично!</b>

Вы успешно зарегистрированы для получения уведомлений!

Нажмите кнопку ниже, чтобы присоединиться к каналу 👇"""
                
                # Создаем кнопку со ссылкой на канал
                keyboard = [[InlineKeyboardButton("🚀 Перейти в канал", url=invite_link_url)]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                return True, success_message, reply_markup
            
            # Если ссылка не сохранена, пробуем создать через API
            else:
                logger.info(f"Инвайт-ссылка не найдена в настройках, создаем через API...")
                
                # Получаем информацию о канале
                chat = await context.bot.get_chat(CHANNEL_ID)
                logger.info(f"Канал найден: {chat.title}")
                
                try:
                    # Создаем персональную инвайт-ссылку
                    invite_link = await context.bot.create_chat_invite_link(
                        chat_id=CHANNEL_ID,
                        member_limit=1,  # Только для одного пользователя
                        name=f"User_{user_id}"
                    )
                    
                    # Помечаем пользователя как подписанного
                    user.subscribed = True
                    user.subscription_date = datetime.utcnow()
                    db.commit()
                    
                    logger.info(f"Создана инвайт-ссылка для пользователя {user_id}")
                    
                    # Текст сообщения
                    success_message = """✅ <b>Отлично!</b>

Вы успешно зарегистрированы для получения уведомлений!

Нажмите кнопку ниже, чтобы присоединиться к каналу 👇"""
                    
                    # Создаем кнопку со ссылкой на канал
                    keyboard = [[InlineKeyboardButton("🚀 Перейти в канал", url=invite_link.invite_link)]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    return True, success_message, reply_markup
                    
                except BadRequest as e:
                    if "CHAT_ADMIN_REQUIRED" in str(e):
                        logger.error(f"Бот не является администратором канала {CHANNEL_ID}")
                        
                        # Все равно помечаем как подписанного
                        user.subscribed = True
                        user.subscription_date = datetime.utcnow()
                        db.commit()
                        
                        return True, SUCCESS_MESSAGE_NO_LINK, None
                    else:
                        raise
                    
        except TelegramError as e:
            logger.error(f"Ошибка Telegram API при подписке пользователя {user_id}: {e}")
            
            # Даже если не удалось добавить в канал, помечаем как подписанного
            # для остановки напоминаний
            user.subscribed = True
            user.subscription_date = datetime.utcnow()
            db.commit()
            
            return True, SUCCESS_MESSAGE_NO_LINK, None
            
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка при подписке пользователя {user_id}: {e}")
        return False, "❌ Произошла ошибка. Попробуйте позже.", None
    finally:
        db.close()


async def check_subscription_status(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """
    Проверка статуса подписки пользователя
    
    Args:
        context: Контекст бота
        user_id: ID пользователя
    
    Returns:
        bool: True если пользователь подписан, False иначе
    """
    try:
        member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
        
        # Проверяем статус участника
        if member.status in ['member', 'administrator', 'creator']:
            logger.info(f"Пользователь {user_id} является участником канала")
            return True
        else:
            logger.info(f"Пользователь {user_id} не является участником канала")
            return False
            
    except TelegramError as e:
        logger.error(f"Ошибка при проверке статуса подписки пользователя {user_id}: {e}")
        return False


async def unsubscribe_user(user_id: int):
    """
    Отписка пользователя (обновление статуса в БД)
    
    Args:
        user_id: ID пользователя
    
    Returns:
        bool: True если успешно, False иначе
    """
    db = get_db()
    try:
        user = db.query(User).filter_by(user_id=user_id).first()
        
        if user:
            user.subscribed = False
            user.subscription_date = None
            db.commit()
            logger.info(f"Пользователь {user_id} отписан")
            return True
        else:
            logger.warning(f"Пользователь {user_id} не найден в базе данных")
            return False
            
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка при отписке пользователя {user_id}: {e}")
        return False
    finally:
        db.close()


