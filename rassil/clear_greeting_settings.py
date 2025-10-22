"""
Скрипт для очистки старых настроек приветствия из базы данных
"""
import sys
from database import get_db, BotSettings

def clear_greeting_settings():
    """Удалить старые настройки приветствия из БД"""
    db = get_db()
    try:
        # Ключи настроек приветствия, которые нужно удалить
        greeting_keys = [
            'greeting_message',
            'greeting_button_text',
            'greeting_button_url',
            'greeting_media_paths'
        ]
        
        deleted_count = 0
        for key in greeting_keys:
            setting = db.query(BotSettings).filter_by(setting_key=key).first()
            if setting:
                print(f"✅ Удаляю настройку: {key}")
                print(f"   Старое значение: {setting.setting_value[:100] if setting.setting_value else 'None'}...")
                db.delete(setting)
                deleted_count += 1
            else:
                print(f"ℹ️  Настройка {key} не найдена в БД")
        
        db.commit()
        print(f"\n✅ Успешно удалено {deleted_count} настроек приветствия из БД")
        print("Теперь бот будет использовать новые тексты из config.py")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Ошибка при очистке настроек: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    print("🗑️  Очистка старых настроек приветствия из БД...\n")
    
    response = input("Вы уверены, что хотите удалить старые настройки приветствия? (да/нет): ")
    if response.lower() in ['да', 'yes', 'y', 'д']:
        clear_greeting_settings()
    else:
        print("❌ Отменено")

