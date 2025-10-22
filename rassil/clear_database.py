#!/usr/bin/env python3
"""
Скрипт для очистки базы данных Eldorado Trade Bot
Удаляет все данные из таблиц, но сохраняет структуру
"""
import sys
from database import get_db, User, Mailing, ReminderText, BotSettings, init_db
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def clear_database():
    """Очистить все таблицы в базе данных"""
    
    print("\n⚠️  ВНИМАНИЕ! Это удалит ВСЕ данные из базы данных!")
    print("Будут очищены таблицы:")
    print("  - users (пользователи)")
    print("  - mailings (рассылки)")
    print("  - reminder_texts (тексты напоминаний)")
    print("  - bot_settings (настройки бота, включая ссылку на канал)")
    
    confirm = input("\nВы уверены? Введите 'YES' для подтверждения: ")
    
    if confirm != 'YES':
        print("❌ Отменено")
        return
    
    try:
        db = get_db()
        
        # Удаляем данные из таблиц в правильном порядке (из-за возможных связей)
        logger.info("Очистка таблицы mailings...")
        deleted_mailings = db.query(Mailing).delete()
        logger.info(f"Удалено записей из mailings: {deleted_mailings}")
        
        logger.info("Очистка таблицы users...")
        deleted_users = db.query(User).delete()
        logger.info(f"Удалено записей из users: {deleted_users}")
        
        logger.info("Очистка таблицы reminder_texts...")
        deleted_reminders = db.query(ReminderText).delete()
        logger.info(f"Удалено записей из reminder_texts: {deleted_reminders}")
        
        logger.info("Очистка таблицы bot_settings...")
        deleted_settings = db.query(BotSettings).delete()
        logger.info(f"Удалено записей из bot_settings: {deleted_settings}")
        
        # Сохраняем изменения
        db.commit()
        db.close()
        
        print("\n✅ База данных успешно очищена!")
        print(f"   - Пользователей удалено: {deleted_users}")
        print(f"   - Рассылок удалено: {deleted_mailings}")
        print(f"   - Текстов напоминаний удалено: {deleted_reminders}")
        print(f"   - Настроек удалено: {deleted_settings}")
        print("\n⚠️  Не забудьте заново установить ссылку на канал через админ-панель!")
        
    except Exception as e:
        logger.error(f"Ошибка при очистке базы данных: {e}")
        print(f"\n❌ Ошибка: {e}")
        sys.exit(1)


def recreate_database():
    """Пересоздать структуру базы данных"""
    
    print("\n⚠️  ВНИМАНИЕ! Это пересоздаст структуру базы данных!")
    print("Все данные будут удалены!")
    
    confirm = input("\nВы уверены? Введите 'YES' для подтверждения: ")
    
    if confirm != 'YES':
        print("❌ Отменено")
        return
    
    try:
        logger.info("Пересоздание базы данных...")
        init_db()
        print("\n✅ База данных успешно пересоздана!")
        
    except Exception as e:
        logger.error(f"Ошибка при пересоздании базы данных: {e}")
        print(f"\n❌ Ошибка: {e}")
        sys.exit(1)


if __name__ == '__main__':
    print("=" * 60)
    print("  ОЧИСТКА БАЗЫ ДАННЫХ ELDORADO TRADE BOT")
    print("=" * 60)
    
    print("\nВыберите действие:")
    print("1 - Очистить данные (удалить все записи, сохранить структуру)")
    print("2 - Пересоздать базу данных (удалить и создать заново)")
    print("0 - Отмена")
    
    choice = input("\nВаш выбор: ")
    
    if choice == '1':
        clear_database()
    elif choice == '2':
        recreate_database()
    elif choice == '0':
        print("❌ Отменено")
    else:
        print("❌ Неверный выбор")
        sys.exit(1)




