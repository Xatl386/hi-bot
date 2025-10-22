"""
Планировщик напоминаний
"""
import logging
from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import get_db, User, ReminderText
from config import REMINDER_INTERVALS

logger = logging.getLogger(__name__)


async def send_reminder(context: ContextTypes.DEFAULT_TYPE, user_id: int, chat_id: int, reminder_type: str):
    """Отправка напоминания пользователю"""
    db = get_db()
    try:
        # Проверяем, не подписался ли пользователь
        user = db.query(User).filter_by(user_id=user_id).first()
        
        if not user:
            logger.warning(f"Пользователь {user_id} не найден в базе данных")
            return
        
        if user.subscribed:
            logger.info(f"Пользователь {user_id} уже подписан, напоминание не отправляется")
            return
        
        # Проверяем, не было ли уже отправлено это напоминание
        reminder_field = f"{reminder_type}_sent"
        if getattr(user, reminder_field, False):
            logger.info(f"Напоминание {reminder_type} уже было отправлено пользователю {user_id}")
            return
        
        # Получаем текст напоминания
        reminder_text_obj = db.query(ReminderText).filter_by(reminder_type=reminder_type).first()
        
        if not reminder_text_obj:
            logger.error(f"Текст напоминания {reminder_type} не найден в базе данных")
            return
        
        # Создаем кнопку
        keyboard = [[InlineKeyboardButton("ОК 🔥", callback_data="subscribe")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Отправляем напоминание
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=reminder_text_obj.text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            
            # Отмечаем, что напоминание отправлено
            setattr(user, reminder_field, True)
            db.commit()
            
            logger.info(f"Напоминание {reminder_type} отправлено пользователю {user_id}")
            
        except Exception as e:
            logger.error(f"Ошибка при отправке напоминания пользователю {user_id}: {e}")
            
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка при обработке напоминания: {e}")
    finally:
        db.close()


async def schedule_reminders(context: ContextTypes.DEFAULT_TYPE, user_id: int, chat_id: int):
    """Планирование напоминаний для пользователя"""
    try:
        # Планируем напоминания на разные интервалы
        for reminder_type, interval in REMINDER_INTERVALS.items():
            job_name = f"reminder_{user_id}_{reminder_type}"
            
            # Удаляем существующую задачу, если она есть
            current_jobs = context.job_queue.get_jobs_by_name(job_name)
            for job in current_jobs:
                job.schedule_removal()
            
            # Планируем новую задачу
            context.job_queue.run_once(
                callback=lambda ctx, uid=user_id, cid=chat_id, rt=reminder_type: 
                    send_reminder(ctx, uid, cid, rt),
                when=interval,
                name=job_name,
                user_id=user_id
            )
            
            logger.info(f"Запланировано напоминание {reminder_type} для пользователя {user_id} через {interval} секунд")
            
    except Exception as e:
        logger.error(f"Ошибка при планировании напоминаний: {e}")


async def cancel_reminders(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Отмена всех напоминаний для пользователя"""
    try:
        # Отменяем все запланированные напоминания
        for reminder_type in REMINDER_INTERVALS.keys():
            job_name = f"reminder_{user_id}_{reminder_type}"
            current_jobs = context.job_queue.get_jobs_by_name(job_name)
            
            for job in current_jobs:
                job.schedule_removal()
                logger.info(f"Отменено напоминание {job_name}")
                
    except Exception as e:
        logger.error(f"Ошибка при отмене напоминаний: {e}")


