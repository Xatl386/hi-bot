"""
Система рассылок
"""
import logging
import asyncio
from telegram import InputMediaPhoto
from telegram.ext import ContextTypes
from telegram.error import TelegramError
from database import get_db, User, Mailing
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Глобальный флаг активной рассылки (для предотвращения блокировки)
_active_mailings = set()


async def send_test_mailing(context: ContextTypes.DEFAULT_TYPE, mailing_id: int, admin_id: int):
    """
    Отправка тестовой рассылки администратору
    
    Args:
        context: Контекст бота
        mailing_id: ID рассылки
        admin_id: ID администратора для отправки теста
    
    Returns:
        tuple: (success: bool, message: str)
    """
    db = get_db()
    try:
        # Получаем рассылку
        mailing = db.query(Mailing).filter_by(id=mailing_id).first()
        
        if not mailing:
            return False, "❌ Рассылка не найдена"
        
        # Отправляем сообщение администратору
        try:
            if mailing.image_path and Path(mailing.image_path).exists():
                # Отправка с изображением
                with open(mailing.image_path, 'rb') as photo:
                    await context.bot.send_photo(
                        chat_id=admin_id,
                        photo=photo,
                        caption=mailing.message_text,
                        parse_mode='HTML'
                    )
            else:
                # Отправка только текста
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=mailing.message_text,
                    parse_mode='HTML'
                )
            
            # Обновляем статус
            mailing.status = 'test_sent'
            db.commit()
            
            logger.info(f"Тестовая рассылка {mailing_id} отправлена администратору {admin_id}")
            return True, "✅ Тестовое сообщение отправлено вам в личные сообщения!"
            
        except TelegramError as e:
            logger.error(f"Ошибка при отправке тестовой рассылки: {e}")
            return False, f"❌ Ошибка отправки: {str(e)}"
            
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка при обработке тестовой рассылки: {e}")
        return False, "❌ Произошла ошибка"
    finally:
        db.close()


async def _background_mass_mailing(context: ContextTypes.DEFAULT_TYPE, mailing_id: int, admin_id: int = None):
    """
    Фоновая массовая рассылка (не блокирует бота)
    
    Args:
        context: Контекст бота
        mailing_id: ID рассылки
        admin_id: ID администратора для уведомления о завершении
    """
    global _active_mailings
    _active_mailings.add(mailing_id)
    
    db = get_db()
    try:
        # Получаем рассылку
        mailing = db.query(Mailing).filter_by(id=mailing_id).first()
        
        if not mailing:
            logger.error(f"Рассылка {mailing_id} не найдена")
            return
        
        # Получаем всех пользователей и извлекаем нужные данные
        users = db.query(User).all()
        total_count = len(users)
        
        # ВАЖНО: Извлекаем данные пользователей перед закрытием сессии
        users_data = [
            {
                'user_id': user.user_id,
                'chat_id': user.chat_id
            }
            for user in users
        ]
        
        # Сохраняем путь к изображению и текст сообщения
        image_path = mailing.image_path
        message_text = mailing.message_text
        
        # Обновляем статус
        mailing.status = 'sending'
        mailing.total_count = total_count
        db.commit()
        db.close()  # Теперь безопасно закрываем соединение
        
        logger.info(f"Начата массовая рассылка {mailing_id} для {total_count} пользователей (в фоне)")
        
        sent_count = 0
        
        # Отправляем сообщения
        for user_data in users_data:
            try:
                if image_path and Path(image_path).exists():
                    # Отправка с изображением
                    with open(image_path, 'rb') as photo:
                        await context.bot.send_photo(
                            chat_id=user_data['chat_id'],
                            photo=photo,
                            caption=message_text,
                            parse_mode='HTML'
                        )
                else:
                    # Отправка только текста
                    await context.bot.send_message(
                        chat_id=user_data['chat_id'],
                        text=message_text,
                        parse_mode='HTML'
                    )
                
                sent_count += 1
                
                # Обновляем счетчик каждые 10 сообщений
                if sent_count % 10 == 0:
                    db = get_db()
                    mailing_update = db.query(Mailing).filter_by(id=mailing_id).first()
                    if mailing_update:
                        mailing_update.sent_count = sent_count
                        db.commit()
                    db.close()
                
                # Небольшая задержка для избежания лимитов
                await asyncio.sleep(0.05)
                
            except TelegramError as e:
                logger.warning(f"Не удалось отправить сообщение пользователю {user_data['user_id']}: {e}")
                continue
            except Exception as e:
                logger.error(f"Ошибка при отправке сообщения пользователю {user_data['user_id']}: {e}")
                continue
        
        # Обновляем финальный статус
        db = get_db()
        mailing_final = db.query(Mailing).filter_by(id=mailing_id).first()
        if mailing_final:
            mailing_final.status = 'sent'
            mailing_final.sent_count = sent_count
            db.commit()
        db.close()
        
        logger.info(f"Массовая рассылка {mailing_id} завершена: отправлено {sent_count} из {total_count}")
        
        # Отправляем уведомление администратору о завершении
        if admin_id:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=f"✅ <b>Рассылка завершена!</b>\n\n"
                         f"Отправлено: <b>{sent_count}</b> из <b>{total_count}</b> пользователей",
                    parse_mode='HTML'
                )
            except Exception as e:
                logger.error(f"Не удалось отправить уведомление админу {admin_id}: {e}")
        
    except Exception as e:
        logger.error(f"Ошибка при массовой рассылке: {e}")
        db = get_db()
        mailing_error = db.query(Mailing).filter_by(id=mailing_id).first()
        if mailing_error:
            mailing_error.status = 'draft'
            db.commit()
        db.close()
        
        # Уведомляем админа об ошибке
        if admin_id:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=f"❌ <b>Ошибка при рассылке!</b>\n\n"
                         f"Рассылка #{mailing_id} не завершена из-за ошибки.",
                    parse_mode='HTML'
                )
            except Exception as notify_error:
                logger.error(f"Не удалось отправить уведомление об ошибке админу {admin_id}: {notify_error}")
    finally:
        _active_mailings.discard(mailing_id)


async def send_mass_mailing(context: ContextTypes.DEFAULT_TYPE, mailing_id: int, admin_id: int = None):
    """
    Запуск массовой рассылки в фоновом режиме (не блокирует бота)
    
    Args:
        context: Контекст бота
        mailing_id: ID рассылки
        admin_id: ID администратора для уведомления о завершении (опционально)
    
    Returns:
        tuple: (success: bool, sent_count: int, total_count: int)
    """
    global _active_mailings
    
    # Проверяем, не запущена ли уже эта рассылка
    if mailing_id in _active_mailings:
        logger.warning(f"Рассылка {mailing_id} уже выполняется")
        return False, 0, 0
    
    db = get_db()
    try:
        # Получаем рассылку
        mailing = db.query(Mailing).filter_by(id=mailing_id).first()
        
        if not mailing:
            logger.error(f"Рассылка {mailing_id} не найдена")
            return False, 0, 0
        
        # Получаем количество пользователей
        total_count = db.query(User).count()
        
        # Запускаем рассылку в фоновой задаче с уведомлением админа
        asyncio.create_task(_background_mass_mailing(context, mailing_id, admin_id))
        
        logger.info(f"Рассылка {mailing_id} запущена в фоне для {total_count} пользователей")
        return True, 0, total_count
        
    except Exception as e:
        logger.error(f"Ошибка при запуске массовой рассылки: {e}")
        return False, 0, 0
    finally:
        db.close()


async def create_mailing(message_text: str, image_path: str = None, created_by: int = None):
    """
    Создание новой рассылки
    
    Args:
        message_text: Текст сообщения
        image_path: Путь к изображению (опционально)
        created_by: ID создателя рассылки
    
    Returns:
        int: ID созданной рассылки или None в случае ошибки
    """
    db = get_db()
    try:
        mailing = Mailing(
            message_text=message_text,
            image_path=image_path,
            created_by=created_by,
            status='draft',
            created_at=datetime.utcnow()
        )
        
        db.add(mailing)
        db.commit()
        db.refresh(mailing)
        
        logger.info(f"Создана новая рассылка ID: {mailing.id}")
        return mailing.id
        
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка при создании рассылки: {e}")
        return None
    finally:
        db.close()


async def get_mailing(mailing_id: int):
    """
    Получение информации о рассылке
    
    Args:
        mailing_id: ID рассылки
    
    Returns:
        Mailing: Объект рассылки или None
    """
    db = get_db()
    try:
        mailing = db.query(Mailing).filter_by(id=mailing_id).first()
        return mailing
    finally:
        db.close()


async def delete_mailing(mailing_id: int):
    """
    Удаление рассылки
    
    Args:
        mailing_id: ID рассылки
    
    Returns:
        bool: True если успешно, False иначе
    """
    db = get_db()
    try:
        mailing = db.query(Mailing).filter_by(id=mailing_id).first()
        
        if mailing:
            # Удаляем изображение, если оно есть
            if mailing.image_path and Path(mailing.image_path).exists():
                try:
                    Path(mailing.image_path).unlink()
                except Exception as e:
                    logger.warning(f"Не удалось удалить изображение: {e}")
            
            db.delete(mailing)
            db.commit()
            logger.info(f"Рассылка {mailing_id} удалена")
            return True
        else:
            logger.warning(f"Рассылка {mailing_id} не найдена")
            return False
            
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка при удалении рассылки: {e}")
        return False
    finally:
        db.close()


