"""
Модуль статистики
"""
import logging
from datetime import datetime, timedelta
from database import get_db, User
import pandas as pd
from pathlib import Path

logger = logging.getLogger(__name__)


async def get_statistics():
    """
    Получение общей статистики
    
    Returns:
        dict: Словарь со статистическими данными
    """
    db = get_db()
    try:
        # Общее количество пользователей
        total_users = db.query(User).count()
        
        # Подписанные/неподписанные
        subscribed_users = db.query(User).filter_by(subscribed=True).count()
        unsubscribed_users = total_users - subscribed_users
        
        # Процент подписки
        subscription_rate = (subscribed_users / total_users * 100) if total_users > 0 else 0
        
        # Статистика по датам
        today = datetime.utcnow().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        today_users = db.query(User).filter(
            User.created_at >= datetime.combine(today, datetime.min.time())
        ).count()
        
        week_users = db.query(User).filter(
            User.created_at >= datetime.combine(week_ago, datetime.min.time())
        ).count()
        
        month_users = db.query(User).filter(
            User.created_at >= datetime.combine(month_ago, datetime.min.time())
        ).count()
        
        # Последняя активность
        last_user = db.query(User).order_by(User.created_at.desc()).first()
        last_activity = last_user.created_at.strftime("%d.%m.%Y %H:%M") if last_user else "Нет данных"
        
        stats = {
            'total_users': total_users,
            'subscribed_users': subscribed_users,
            'unsubscribed_users': unsubscribed_users,
            'subscription_rate': subscription_rate,
            'today_users': today_users,
            'week_users': week_users,
            'month_users': month_users,
            'last_activity': last_activity
        }
        
        logger.info(f"Статистика получена: {stats}")
        return stats
        
    except Exception as e:
        logger.error(f"Ошибка при получении статистики: {e}")
        return {
            'total_users': 0,
            'subscribed_users': 0,
            'unsubscribed_users': 0,
            'subscription_rate': 0,
            'today_users': 0,
            'week_users': 0,
            'month_users': 0,
            'last_activity': 'Ошибка'
        }
    finally:
        db.close()


async def get_detailed_statistics():
    """
    Получение детальной статистики по пользователям
    
    Returns:
        list: Список пользователей с их данными
    """
    db = get_db()
    try:
        users = db.query(User).order_by(User.created_at.desc()).all()
        
        user_data = []
        for user in users:
            user_data.append({
                'user_id': user.user_id,
                'username': user.username or 'Не указано',
                'first_name': user.first_name or 'Не указано',
                'last_name': user.last_name or 'Не указано',
                'subscribed': 'Да' if user.subscribed else 'Нет',
                'subscription_date': user.subscription_date.strftime("%d.%m.%Y %H:%M") if user.subscription_date else 'Не подписан',
                'created_at': user.created_at.strftime("%d.%m.%Y %H:%M"),
                'reminder_3min_sent': 'Да' if user.reminder_3min_sent else 'Нет',
                'reminder_10min_sent': 'Да' if user.reminder_10min_sent else 'Нет',
                'reminder_30min_sent': 'Да' if user.reminder_30min_sent else 'Нет',
                'reminder_9hours_sent': 'Да' if user.reminder_9hours_sent else 'Нет'
            })
        
        logger.info(f"Получена детальная статистика по {len(user_data)} пользователям")
        return user_data
        
    except Exception as e:
        logger.error(f"Ошибка при получении детальной статистики: {e}")
        return []
    finally:
        db.close()


async def export_statistics_excel():
    """
    Экспорт статистики в Excel файл
    
    Returns:
        str: Путь к созданному файлу или None в случае ошибки
    """
    try:
        # Получаем детальную статистику
        user_data = await get_detailed_statistics()
        
        if not user_data:
            logger.warning("Нет данных для экспорта")
            return None
        
        # Создаем DataFrame
        df = pd.DataFrame(user_data)
        
        # Переименовываем колонки на русский
        df.columns = [
            'ID пользователя',
            'Username',
            'Имя',
            'Фамилия',
            'Подписан',
            'Дата подписки',
            'Дата регистрации',
            'Напоминание 3 мин',
            'Напоминание 10 мин',
            'Напоминание 30 мин',
            'Напоминание 9 часов'
        ]
        
        # Создаем папку для экспорта, если её нет
        export_dir = Path("exports")
        export_dir.mkdir(exist_ok=True)
        
        # Создаем имя файла с текущей датой
        filename = f"statistics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        filepath = export_dir / filename
        
        # Сохраняем в Excel
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Пользователи', index=False)
            
            # Получаем общую статистику
            general_stats = await get_statistics()
            
            # Создаем DataFrame с общей статистикой
            stats_df = pd.DataFrame([
                ['Всего пользователей', general_stats['total_users']],
                ['Подписанных', general_stats['subscribed_users']],
                ['Не подписанных', general_stats['unsubscribed_users']],
                ['Процент подписки', f"{general_stats['subscription_rate']:.1f}%"],
                ['Новых за сегодня', general_stats['today_users']],
                ['Новых за неделю', general_stats['week_users']],
                ['Новых за месяц', general_stats['month_users']],
                ['Последняя активность', general_stats['last_activity']]
            ], columns=['Показатель', 'Значение'])
            
            stats_df.to_excel(writer, sheet_name='Общая статистика', index=False)
            
            # Автоматическая настройка ширины колонок
            for sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
        
        logger.info(f"Статистика экспортирована в файл: {filepath}")
        return str(filepath)
        
    except Exception as e:
        logger.error(f"Ошибка при экспорте статистики: {e}")
        return None


async def get_subscription_statistics():
    """
    Получение статистики по подпискам
    
    Returns:
        dict: Статистика по подпискам
    """
    db = get_db()
    try:
        # Статистика по напоминаниям
        total_users = db.query(User).count()
        
        reminder_3min_sent = db.query(User).filter_by(reminder_3min_sent=True).count()
        reminder_10min_sent = db.query(User).filter_by(reminder_10min_sent=True).count()
        reminder_30min_sent = db.query(User).filter_by(reminder_30min_sent=True).count()
        reminder_9hours_sent = db.query(User).filter_by(reminder_9hours_sent=True).count()
        
        # Конверсия после каждого напоминания
        subscribed_after_3min = db.query(User).filter(
            User.reminder_3min_sent == True,
            User.subscribed == True
        ).count()
        
        subscribed_after_10min = db.query(User).filter(
            User.reminder_10min_sent == True,
            User.subscribed == True
        ).count()
        
        subscribed_after_30min = db.query(User).filter(
            User.reminder_30min_sent == True,
            User.subscribed == True
        ).count()
        
        subscribed_after_9hours = db.query(User).filter(
            User.reminder_9hours_sent == True,
            User.subscribed == True
        ).count()
        
        stats = {
            'total_users': total_users,
            'reminder_3min_sent': reminder_3min_sent,
            'reminder_10min_sent': reminder_10min_sent,
            'reminder_30min_sent': reminder_30min_sent,
            'reminder_9hours_sent': reminder_9hours_sent,
            'subscribed_after_3min': subscribed_after_3min,
            'subscribed_after_10min': subscribed_after_10min,
            'subscribed_after_30min': subscribed_after_30min,
            'subscribed_after_9hours': subscribed_after_9hours
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Ошибка при получении статистики подписок: {e}")
        return {}
    finally:
        db.close()





