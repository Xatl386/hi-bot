"""
Админ-панель для управления ботом
"""
import logging
import os
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler, CallbackQueryHandler, MessageHandler, 
    ConversationHandler, ContextTypes, filters
)
from config import ADMIN_IDS
from database import get_db, ReminderText, Mailing, BotSettings
from mailing_system import create_mailing, send_test_mailing, send_mass_mailing
from statistics import get_statistics, export_statistics_excel

logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
(MAILING_TEXT, MAILING_IMAGE, MAILING_CONFIRM, 
 EDIT_REMINDER_SELECT, EDIT_REMINDER_TEXT) = range(5)

# Папка для хранения изображений
MEDIA_DIR = Path("media")
MEDIA_DIR.mkdir(exist_ok=True)


def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь администратором"""
    return user_id in ADMIN_IDS


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главное меню админ-панели"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("⛔️ У вас нет прав доступа к админ-панели")
        return
    
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("📤 Создать рассылку", callback_data="admin_new_mailing")],
        [InlineKeyboardButton("✏️ Изменить тексты напоминаний", callback_data="admin_edit_reminders")],
        [InlineKeyboardButton("📥 Выгрузить статистику (Excel)", callback_data="admin_export_stats")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    admin_text = """
🔐 <b>Админ-панель Eldorado Trade Bot</b>

Выберите действие:

📊 <b>Статистика</b> - просмотр статистики пользователей
📤 <b>Создать рассылку</b> - создание и отправка рассылки
✏️ <b>Изменить тексты напоминаний</b> - настройка текстов напоминаний
📥 <b>Выгрузить статистику</b> - экспорт данных в Excel
    """
    
    await update.message.reply_text(admin_text, reply_markup=reply_markup, parse_mode='HTML')


async def show_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать статистику"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not is_admin(user_id):
        await query.edit_message_text("⛔️ У вас нет прав доступа")
        return
    
    stats = await get_statistics()
    
    stats_text = f"""
📊 <b>Статистика бота</b>

👥 <b>Всего пользователей:</b> {stats['total_users']}
✅ <b>Подписанных:</b> {stats['subscribed_users']} ({stats['subscription_rate']:.1f}%)
❌ <b>Не подписанных:</b> {stats['unsubscribed_users']}

📅 <b>Сегодня:</b> {stats['today_users']} новых
📅 <b>За неделю:</b> {stats['week_users']} новых
📅 <b>За месяц:</b> {stats['month_users']} новых

📬 <b>Последняя активность:</b>
{stats.get('last_activity', 'Нет данных')}
    """
    
    keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="admin_back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(stats_text, reply_markup=reply_markup, parse_mode='HTML')


async def start_new_mailing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать создание новой рассылки"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not is_admin(user_id):
        await query.edit_message_text("⛔️ У вас нет прав доступа")
        return ConversationHandler.END
    
    await query.edit_message_text(
        "📝 <b>Создание рассылки</b>\n\n"
        "Отправьте текст сообщения для рассылки.\n"
        "Вы можете использовать HTML-форматирование: <b>жирный</b>, <i>курсив</i>, <code>код</code>\n\n"
        "Для отмены отправьте /cancel",
        parse_mode='HTML'
    )
    
    return MAILING_TEXT


async def receive_mailing_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить текст рассылки"""
    context.user_data['mailing_text'] = update.message.text
    
    keyboard = [
        [InlineKeyboardButton("➡️ Продолжить без изображения", callback_data="mailing_no_image")],
        [InlineKeyboardButton("❌ Отмена", callback_data="mailing_cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "✅ Текст сохранен!\n\n"
        "📸 Теперь отправьте изображение для рассылки или нажмите кнопку ниже, чтобы продолжить без изображения.",
        reply_markup=reply_markup
    )
    
    return MAILING_IMAGE


async def receive_mailing_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить изображение для рассылки"""
    if update.message.photo:
        # Получаем файл изображения
        photo = update.message.photo[-1]  # Берем самое большое фото
        file = await context.bot.get_file(photo.file_id)
        
        # Сохраняем изображение
        filename = f"mailing_{update.effective_user.id}_{photo.file_id}.jpg"
        filepath = MEDIA_DIR / filename
        await file.download_to_drive(filepath)
        
        context.user_data['mailing_image'] = str(filepath)
        
        await update.message.reply_text("✅ Изображение сохранено!")
    
    # Показываем предпросмотр
    return await show_mailing_preview(update, context)


async def skip_mailing_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пропустить добавление изображения"""
    query = update.callback_query
    await query.answer()
    
    context.user_data['mailing_image'] = None
    
    # Показываем предпросмотр
    return await show_mailing_preview(update, context)


async def show_mailing_preview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать предпросмотр рассылки"""
    message_text = context.user_data.get('mailing_text', '')
    image_path = context.user_data.get('mailing_image')
    
    preview_text = f"""
📋 <b>Предпросмотр рассылки</b>

<b>Текст:</b>
{message_text}

<b>Изображение:</b> {'✅ Да' if image_path else '❌ Нет'}
    """
    
    keyboard = [
        [InlineKeyboardButton("✉️ Тестовая отправка", callback_data="mailing_test")],
        [InlineKeyboardButton("📢 Отправить всем", callback_data="mailing_send_all")],
        [InlineKeyboardButton("❌ Отмена", callback_data="mailing_cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if isinstance(update, Update) and update.callback_query:
        await update.callback_query.message.reply_text(
            preview_text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            preview_text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    
    return MAILING_CONFIRM


async def send_test_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправить тестовое сообщение"""
    query = update.callback_query
    await query.answer("Отправляю тестовое сообщение...")
    
    user_id = query.from_user.id
    message_text = context.user_data.get('mailing_text', '')
    image_path = context.user_data.get('mailing_image')
    
    # Создаем рассылку
    mailing_id = await create_mailing(message_text, image_path, user_id)
    
    if mailing_id:
        success, message = await send_test_mailing(context, mailing_id, user_id)
        
        if success:
            await query.message.reply_text(
                "✅ Тестовое сообщение отправлено!\n\n"
                "Проверьте личные сообщения и выберите действие:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📢 Отправить всем", callback_data=f"mailing_send_all_{mailing_id}")],
                    [InlineKeyboardButton("❌ Отмена", callback_data="mailing_cancel")]
                ])
            )
        else:
            await query.message.reply_text(f"❌ Ошибка: {message}")
            return ConversationHandler.END
    else:
        await query.message.reply_text("❌ Ошибка при создании рассылки")
        return ConversationHandler.END
    
    return MAILING_CONFIRM


async def send_mass_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправить массовое сообщение"""
    query = update.callback_query
    await query.answer("Начинаю массовую рассылку...")
    
    user_id = query.from_user.id
    message_text = context.user_data.get('mailing_text', '')
    image_path = context.user_data.get('mailing_image')
    
    # Проверяем, есть ли ID рассылки в callback_data
    callback_data = query.data
    if '_' in callback_data:
        parts = callback_data.split('_')
        if len(parts) > 3:
            mailing_id = int(parts[-1])
        else:
            # Создаем новую рассылку
            mailing_id = await create_mailing(message_text, image_path, user_id)
    else:
        mailing_id = await create_mailing(message_text, image_path, user_id)
    
    if mailing_id:
        await query.message.reply_text("📨 Начинаю отправку сообщений...")
        
        # Передаем user_id для уведомления о завершении
        success, sent_count, total_count = await send_mass_mailing(context, mailing_id, admin_id=user_id)
        
        if success:
            await query.message.reply_text(
                f"✅ <b>Рассылка запущена в фоновом режиме!</b>\n\n"
                f"Будет отправлено {total_count} пользователям.\n\n"
                f"Вы получите уведомление о завершении.",
                parse_mode='HTML'
            )
        else:
            await query.message.reply_text("❌ Ошибка при запуске рассылки")
    else:
        await query.message.reply_text("❌ Ошибка при создании рассылки")
    
    # Очищаем данные
    context.user_data.clear()
    
    return ConversationHandler.END


async def cancel_mailing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отменить создание рассылки"""
    query = update.callback_query
    if query:
        await query.answer()
        await query.message.reply_text("❌ Создание рассылки отменено")
    else:
        await update.message.reply_text("❌ Создание рассылки отменено")
    
    # Удаляем сохраненное изображение
    image_path = context.user_data.get('mailing_image')
    if image_path and Path(image_path).exists():
        try:
            Path(image_path).unlink()
        except Exception as e:
            logger.warning(f"Не удалось удалить изображение: {e}")
    
    context.user_data.clear()
    return ConversationHandler.END


async def edit_reminders_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню редактирования текстов напоминаний"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    logger.info(f"Пользователь {user_id} открыл меню редактирования напоминаний")
    
    if not is_admin(user_id):
        await query.edit_message_text("⛔️ У вас нет прав доступа")
        return ConversationHandler.END
    
    keyboard = [
        [InlineKeyboardButton("⏱ Напоминание 3 минуты", callback_data="edit_reminder_3min")],
        [InlineKeyboardButton("⏱ Напоминание 10 минут", callback_data="edit_reminder_10min")],
        [InlineKeyboardButton("⏱ Напоминание 30 минут", callback_data="edit_reminder_30min")],
        [InlineKeyboardButton("⏱ Напоминание 9 часов", callback_data="edit_reminder_9hours")],
        [InlineKeyboardButton("◀️ Назад", callback_data="admin_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "✏️ <b>Редактирование текстов напоминаний</b>\n\n"
        "Выберите, какое напоминание хотите изменить:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    
    return EDIT_REMINDER_SELECT


async def select_reminder_to_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбрать напоминание для редактирования"""
    query = update.callback_query
    await query.answer()
    
    # Получаем тип напоминания из callback_data
    reminder_type = query.data.replace('edit_', '')
    context.user_data['editing_reminder'] = reminder_type
    
    # Получаем текущий текст
    db = get_db()
    try:
        reminder_text = db.query(ReminderText).filter_by(reminder_type=reminder_type).first()
        current_text = reminder_text.text if reminder_text else "Текст не найден"
    finally:
        db.close()
    
    reminder_names = {
        'reminder_3min': '3 минуты',
        'reminder_10min': '10 минут',
        'reminder_30min': '30 минут',
        'reminder_9hours': '9 часов'
    }
    
    await query.edit_message_text(
        f"✏️ <b>Редактирование напоминания ({reminder_names.get(reminder_type, reminder_type)})</b>\n\n"
        f"<b>Текущий текст:</b>\n{current_text}\n\n"
        f"Отправьте новый текст напоминания или /cancel для отмены",
        parse_mode='HTML'
    )
    
    return EDIT_REMINDER_TEXT


async def save_reminder_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохранить новый текст напоминания"""
    reminder_type = context.user_data.get('editing_reminder')
    new_text = update.message.text
    
    db = get_db()
    try:
        reminder_text = db.query(ReminderText).filter_by(reminder_type=reminder_type).first()
        
        if reminder_text:
            reminder_text.text = new_text
            db.commit()
            
            await update.message.reply_text(
                f"✅ Текст напоминания <b>{reminder_type}</b> успешно обновлен!",
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text("❌ Напоминание не найдено")
            
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка при сохранении текста напоминания: {e}")
        await update.message.reply_text("❌ Ошибка при сохранении")
    finally:
        db.close()
    
    context.user_data.clear()
    return ConversationHandler.END


async def export_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Экспорт статистики в Excel"""
    query = update.callback_query
    await query.answer("Подготавливаю файл...")
    
    user_id = query.from_user.id
    if not is_admin(user_id):
        await query.edit_message_text("⛔️ У вас нет прав доступа")
        return
    
    try:
        filepath = await export_statistics_excel()
        
        if filepath and Path(filepath).exists():
            with open(filepath, 'rb') as file:
                await context.bot.send_document(
                    chat_id=user_id,
                    document=file,
                    filename="statistics.xlsx",
                    caption="📊 Статистика пользователей бота"
                )
            
            # Удаляем временный файл
            try:
                Path(filepath).unlink()
            except Exception as e:
                logger.warning(f"Не удалось удалить временный файл: {e}")
            
            await query.message.reply_text("✅ Файл отправлен!")
        else:
            await query.message.reply_text("❌ Ошибка при создании файла")
            
    except Exception as e:
        logger.error(f"Ошибка при экспорте статистики: {e}")
        await query.message.reply_text("❌ Ошибка при экспорте статистики")


async def admin_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Вернуться в главное меню админки"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("📤 Создать рассылку", callback_data="admin_new_mailing")],
        [InlineKeyboardButton("✏️ Изменить тексты напоминаний", callback_data="admin_edit_reminders")],
        [InlineKeyboardButton("📥 Выгрузить статистику (Excel)", callback_data="admin_export_stats")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    admin_text = """
🔐 <b>Админ-панель Eldorado Trade Bot</b>

Выберите действие:
    """
    
    await query.edit_message_text(admin_text, reply_markup=reply_markup, parse_mode='HTML')
    return ConversationHandler.END


def setup_admin_handlers(application):
    """Настройка обработчиков админ-панели"""
    
    # Главное меню
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CallbackQueryHandler(show_statistics, pattern="^admin_stats$"))
    application.add_handler(CallbackQueryHandler(export_statistics, pattern="^admin_export_stats$"))
    
    # Conversation handler для создания рассылки
    mailing_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_new_mailing, pattern="^admin_new_mailing$")],
        states={
            MAILING_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_mailing_text)],
            MAILING_IMAGE: [
                MessageHandler(filters.PHOTO, receive_mailing_image),
                CallbackQueryHandler(skip_mailing_image, pattern="^mailing_no_image$"),
                CallbackQueryHandler(cancel_mailing, pattern="^mailing_cancel$")
            ],
            MAILING_CONFIRM: [
                CallbackQueryHandler(send_test_message, pattern="^mailing_test$"),
                CallbackQueryHandler(send_mass_message, pattern="^mailing_send_all"),
                CallbackQueryHandler(cancel_mailing, pattern="^mailing_cancel$")
            ]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_mailing),
            CallbackQueryHandler(cancel_mailing, pattern="^mailing_cancel$")
        ],
        per_user=True,
        per_chat=True,
        name="mailing_conversation"
    )
    application.add_handler(mailing_conv)
    
    # Conversation handler для редактирования напоминаний
    reminder_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(edit_reminders_menu, pattern="^admin_edit_reminders$")],
        states={
            EDIT_REMINDER_SELECT: [
                CallbackQueryHandler(select_reminder_to_edit, pattern="^edit_reminder_"),
                CallbackQueryHandler(admin_back, pattern="^admin_back$")
            ],
            EDIT_REMINDER_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_reminder_text)
            ]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_mailing),
            CallbackQueryHandler(admin_back, pattern="^admin_back$")
        ],
        per_user=True,
        per_chat=True,
        name="reminder_conversation"
    )
    application.add_handler(reminder_conv)
    
    # Глобальный обработчик admin_back (должен быть ПОСЛЕ всех ConversationHandler'ов)
    # Сработает только если пользователь не находится в активном conversation
    application.add_handler(CallbackQueryHandler(admin_back, pattern="^admin_back$"))
    
    logger.info("Обработчики админ-панели настроены")


