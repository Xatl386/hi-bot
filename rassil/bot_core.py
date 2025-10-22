"""
Основной модуль бота
"""
import logging
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from datetime import datetime
from database import get_db, User
from config import WELCOME_MESSAGE, VERIFICATION_MESSAGE, VERIFICATION_SUCCESS

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    logger.info(f"Команда /start от пользователя {user.id} ({user.username})")
    
    # Сохранение пользователя в базу данных
    db = get_db()
    try:
        existing_user = db.query(User).filter_by(user_id=user.id).first()
        
        if existing_user:
            # Обновляем информацию о пользователе
            existing_user.username = user.username
            existing_user.first_name = user.first_name
            existing_user.last_name = user.last_name
            existing_user.chat_id = chat_id
            logger.info(f"Обновлена информация о пользователе {user.id}")
        else:
            # Создаем нового пользователя (НЕ подписанного)
            new_user = User(
                user_id=user.id,
                chat_id=chat_id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                subscribed=False,  # Пользователь не подписан до нажатия кнопки "Ок"
                created_at=datetime.utcnow()
            )
            db.add(new_user)
            logger.info(f"Создан новый пользователь {user.id}")
        
        db.commit()
        
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка при сохранении пользователя: {e}")
    finally:
        db.close()
    
    # Отправляем приветственное сообщение
    await update.message.reply_text(
        WELCOME_MESSAGE,
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
    await update.message.reply_text(
        VERIFICATION_MESSAGE,
        reply_markup=reply_markup
    )


async def save_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстового сообщения '✅ Я человек!' - сохранение пользователя для рассылки"""
    user = update.effective_user
    
    logger.info(f"Пользователь {user.id} отправил '✅ Я человек!'")
    
    # Сохраняем пользователя в БД как подписанного (для рассылки)
    db = get_db()
    try:
        db_user = db.query(User).filter_by(user_id=user.id).first()
        
        if db_user:
            # Отмечаем пользователя как подписанного
            db_user.subscribed = True
            db_user.subscription_date = datetime.utcnow()
            db.commit()
            
            logger.info(f"Пользователь {user.id} сохранен в БД для рассылки")
            
            # Сообщение об успехе (убираем клавиатуру)
            await update.message.reply_text(
                text=VERIFICATION_SUCCESS,
                reply_markup=ReplyKeyboardRemove()
            )
            
            # Отправляем главное меню
            await update.message.reply_text(
                text="<b>Главное меню</b>\n\nИспользуйте /help для просмотра доступных команд",
                parse_mode='HTML'
            )
        else:
            logger.error(f"Пользователь {user.id} не найден в БД")
            await update.message.reply_text(
                text="❌ Ошибка: пользователь не найден. Попробуйте отправить /start еще раз.",
                reply_markup=ReplyKeyboardRemove()
            )
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка при сохранении пользователя {user.id}: {e}")
        await update.message.reply_text(
            text="❌ Произошла ошибка при регистрации. Попробуйте позже.",
            reply_markup=ReplyKeyboardRemove()
        )
    finally:
        db.close()


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    help_text = """
🤖 <b>Eldorado Trade Bot - Помощь</b>

<b>Доступные команды:</b>
/start - Начать работу с ботом
/help - Показать это сообщение

<b>Что делает бот:</b>
• Автоматически принимает заявки на вступление в канал
• Отправляет приветственные сообщения новым участникам
• Позволяет получать рассылки и важные уведомления

Нажмите кнопку "Ок ✅" чтобы зарегистрироваться для получения рассылок!
    """
    
    await update.message.reply_text(help_text, parse_mode='HTML')


def setup_handlers(application: Application):
    """Настройка обработчиков команд и кнопок"""
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # Обработчик текстового сообщения "✅ Я человек!"
    application.add_handler(MessageHandler(
        filters.TEXT & filters.Regex("^✅ Я человек!$"),
        save_user_message
    ))
    
    logger.info("Обработчики команд настроены")


