"""
Главный файл запуска Telegram бота "Eldorado Trade"
"""
import logging
import sys
from telegram.ext import Application, ChatJoinRequestHandler
from config import BOT_TOKEN, LOG_LEVEL
from database import init_db
from bot_core import setup_handlers
from admin_panel import setup_admin_handlers
from join_request_handler import handle_join_request

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Главная функция запуска бота"""
    
    # Проверка наличия токена
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN не указан в файле .env")
        sys.exit(1)
    
    logger.info("=" * 50)
    logger.info("Запуск Telegram бота 'Eldorado Trade'")
    logger.info("=" * 50)
    
    try:
        # Инициализация базы данных
        logger.info("Инициализация базы данных...")
        init_db()
        logger.info("База данных успешно инициализирована")
        
        # Создание приложения с persistence для сохранения состояния
        logger.info("Создание приложения бота...")
        from telegram.ext import PicklePersistence
        
        # Используем persistence для сохранения состояния между перезапусками
        persistence = PicklePersistence(filepath='bot_persistence.pickle')
        application = Application.builder().token(BOT_TOKEN).persistence(persistence).build()
        
        # Настройка обработчиков
        logger.info("Настройка обработчиков команд...")
        setup_handlers(application)
        setup_admin_handlers(application)
        
        # Обработчик заявок на вступление в канал
        application.add_handler(ChatJoinRequestHandler(handle_join_request))
        logger.info("Обработчик заявок на вступление настроен")
        
        logger.info("Обработчики успешно настроены")
        
        # Запуск бота
        logger.info("Запуск бота...")
        logger.info("Бот успешно запущен и готов к работе!")
        logger.info("Нажмите Ctrl+C для остановки бота")
        
        # Запуск polling с обработкой пропущенных сообщений
        application.run_polling(
            allowed_updates=['message', 'callback_query', 'chat_join_request'],
            drop_pending_updates=False  # Обрабатываем сообщения, отправленные во время простоя
        )
        
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки (Ctrl+C)")
    except Exception as e:
        logger.error(f"Критическая ошибка при запуске бота: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("Бот остановлен")
        logger.info("=" * 50)


if __name__ == '__main__':
    main()


