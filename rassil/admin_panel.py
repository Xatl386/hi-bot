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
 EDIT_REMINDER_SELECT, EDIT_REMINDER_TEXT, SET_INVITE_LINK,
 GREETING_TEXT, GREETING_MEDIA, GREETING_BUTTON_TEXT, GREETING_BUTTON_URL) = range(10)

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
        [InlineKeyboardButton("👋 Редактировать приветствие", callback_data="admin_edit_greeting")],
        [InlineKeyboardButton("🔗 Установить ссылку на канал", callback_data="admin_set_invite_link")],
        [InlineKeyboardButton("✏️ Изменить тексты напоминаний", callback_data="admin_edit_reminders")],
        [InlineKeyboardButton("📥 Выгрузить статистику (Excel)", callback_data="admin_export_stats")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    admin_text = """
🔐 <b>Админ-панель Eldorado Trade Bot</b>

Выберите действие:

📊 <b>Статистика</b> - просмотр статистики пользователей
📤 <b>Создать рассылку</b> - создание и отправка рассылки
👋 <b>Редактировать приветствие</b> - настройка сообщения для новых участников
🔗 <b>Установить ссылку</b> - настройка инвайт-ссылки на канал
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


async def set_invite_link_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать установку инвайт-ссылки"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not is_admin(user_id):
        await query.edit_message_text("⛔️ У вас нет прав доступа")
        return ConversationHandler.END
    
    # Получаем текущую ссылку
    db = get_db()
    try:
        current_link = db.query(BotSettings).filter_by(setting_key='channel_invite_link').first()
        current_value = current_link.setting_value if current_link else "Не установлена"
    finally:
        db.close()
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = f"""🔗 <b>Установка ссылки на канал</b>

<b>Текущая ссылка:</b>
{current_value}

Отправьте новую инвайт-ссылку на ваш канал.

<b>Как создать ссылку:</b>
1. Откройте ваш канал в Telegram
2. Нажмите на название канала
3. Нажмите "Пригласительные ссылки"
4. Создайте новую ссылку (или скопируйте существующую)
5. Отправьте ссылку сюда

<b>Пример:</b>
<code>https://t.me/+abcdefghijklmnop</code>

Или отправьте /cancel для отмены"""

    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    return SET_INVITE_LINK


async def save_invite_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохранить инвайт-ссылку"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("⛔️ У вас нет прав доступа")
        return ConversationHandler.END
    
    invite_link = update.message.text.strip()
    
    # Проверяем формат ссылки
    if not (invite_link.startswith('https://t.me/+') or invite_link.startswith('https://t.me/joinchat/')):
        await update.message.reply_text(
            "❌ Неверный формат ссылки!\n\n"
            "Ссылка должна начинаться с:\n"
            "• https://t.me/+...\n"
            "• https://t.me/joinchat/...\n\n"
            "Отправьте правильную ссылку или /cancel для отмены"
        )
        return SET_INVITE_LINK
    
    # Сохраняем в базу данных
    db = get_db()
    try:
        setting = db.query(BotSettings).filter_by(setting_key='channel_invite_link').first()
        
        if setting:
            setting.setting_value = invite_link
        else:
            setting = BotSettings(
                setting_key='channel_invite_link',
                setting_value=invite_link
            )
            db.add(setting)
        
        db.commit()
        logger.info(f"Установлена новая инвайт-ссылка: {invite_link}")
        
        keyboard = [[InlineKeyboardButton("🔙 В админ-панель", callback_data="admin_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ <b>Ссылка успешно сохранена!</b>\n\n"
            f"<b>Новая ссылка:</b>\n{invite_link}\n\n"
            f"Теперь все пользователи будут получать эту ссылку при нажатии кнопки 'ОК 🔥'",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
        return ConversationHandler.END
        
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка при сохранении инвайт-ссылки: {e}")
        await update.message.reply_text("❌ Ошибка при сохранении ссылки. Попробуйте позже.")
        return ConversationHandler.END
    finally:
        db.close()


async def cancel_set_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена установки ссылки"""
    if update.callback_query:
        query = update.callback_query
        await query.answer()
    
    keyboard = [[InlineKeyboardButton("🔙 В админ-панель", callback_data="admin_back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            "❌ Установка ссылки отменена",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            "❌ Установка ссылки отменена",
            reply_markup=reply_markup
        )
    
    return ConversationHandler.END


async def admin_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Вернуться в главное меню админки"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("📤 Создать рассылку", callback_data="admin_new_mailing")],
        [InlineKeyboardButton("👋 Редактировать приветствие", callback_data="admin_edit_greeting")],
        [InlineKeyboardButton("🔗 Установить ссылку на канал", callback_data="admin_set_invite_link")],
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


# ============================================================================
# ФУНКЦИИ ДЛЯ РЕДАКТИРОВАНИЯ ПРИВЕТСТВЕННОГО СООБЩЕНИЯ
# ============================================================================

async def edit_greeting_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню редактирования приветственного сообщения"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not is_admin(user_id):
        await query.edit_message_text("⛔️ У вас нет прав доступа")
        return ConversationHandler.END
    
    # Получаем текущие настройки
    db = get_db()
    try:
        greeting_text = db.query(BotSettings).filter_by(setting_key='greeting_message').first()
        button_text = db.query(BotSettings).filter_by(setting_key='greeting_button_text').first()
        button_url = db.query(BotSettings).filter_by(setting_key='greeting_button_url').first()
        media_paths = db.query(BotSettings).filter_by(setting_key='greeting_media_paths').first()
        
        current_text = greeting_text.setting_value if greeting_text else "Не установлен"
        current_button = f"{button_text.setting_value} -> {button_url.setting_value}" if (button_text and button_url) else "Не установлена"
        current_media = "Да" if (media_paths and media_paths.setting_value) else "Нет"
        
    finally:
        db.close()
    
    keyboard = [
        [InlineKeyboardButton("✍️ Изменить текст", callback_data="greeting_edit_text")],
        [InlineKeyboardButton("🖼️ Добавить медиа", callback_data="greeting_add_media")],
        [InlineKeyboardButton("🗑️ Удалить медиа", callback_data="greeting_delete_media")],
        [InlineKeyboardButton("🔘 Изменить кнопку", callback_data="greeting_edit_button")],
        [InlineKeyboardButton("🗑️ Удалить кнопку", callback_data="greeting_delete_button")],
        [InlineKeyboardButton("🔍 Предпросмотр", callback_data="greeting_preview")],
        [InlineKeyboardButton("◀️ Назад", callback_data="admin_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = f"""👋 <b>Редактирование приветственного сообщения</b>

<b>Текущие настройки:</b>

<b>Текст:</b>
{current_text[:100]}{"..." if len(current_text) > 100 else ""}

<b>Кнопка:</b> {current_button}
<b>Медиа:</b> {current_media}

Выберите действие:"""
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')


async def greeting_edit_text_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать редактирование текста приветствия"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not is_admin(user_id):
        await query.edit_message_text("⛔️ У вас нет прав доступа")
        return ConversationHandler.END
    
    # Получаем текущий текст
    db = get_db()
    try:
        greeting_text = db.query(BotSettings).filter_by(setting_key='greeting_message').first()
        current_text = greeting_text.setting_value if greeting_text else "Не установлен"
    finally:
        db.close()
    
    await query.edit_message_text(
        f"✍️ <b>Редактирование текста приветствия</b>\n\n"
        f"<b>Текущий текст:</b>\n{current_text}\n\n"
        f"Отправьте новый текст приветственного сообщения.\n"
        f"Вы можете использовать HTML-форматирование: <b>жирный</b>, <i>курсив</i>, <code>код</code>\n\n"
        f"Или отправьте /cancel для отмены",
        parse_mode='HTML'
    )
    
    return GREETING_TEXT


async def greeting_save_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохранить новый текст приветствия"""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔️ У вас нет прав доступа")
        return ConversationHandler.END
    
    new_text = update.message.text
    
    # Сохраняем в БД
    db = get_db()
    try:
        setting = db.query(BotSettings).filter_by(setting_key='greeting_message').first()
        
        if setting:
            setting.setting_value = new_text
        else:
            setting = BotSettings(setting_key='greeting_message', setting_value=new_text)
            db.add(setting)
        
        db.commit()
        logger.info(f"Обновлен текст приветствия администратором {user_id}")
        
        keyboard = [[InlineKeyboardButton("🔙 В меню приветствий", callback_data="admin_edit_greeting")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "✅ <b>Текст приветствия успешно обновлен!</b>",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
        return ConversationHandler.END
        
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка при сохранении текста приветствия: {e}")
        await update.message.reply_text("❌ Ошибка при сохранении текста")
        return ConversationHandler.END
    finally:
        db.close()


async def greeting_add_media_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать добавление медиа"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not is_admin(user_id):
        await query.edit_message_text("⛔️ У вас нет прав доступа")
        return ConversationHandler.END
    
    # Инициализируем список для хранения путей к медиа
    context.user_data['greeting_media_files'] = []
    
    keyboard = [[InlineKeyboardButton("✅ Завершить", callback_data="greeting_media_done")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🖼️ <b>Добавление медиа к приветствию</b>\n\n"
        "Отправьте изображения (до 10 штук).\n"
        "Можно отправлять как фото (со сжатием), так и файлы (без сжатия).\n\n"
        "После отправки всех изображений нажмите кнопку 'Завершить' ниже.",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    
    return GREETING_MEDIA


async def greeting_receive_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить медиа-файл"""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return GREETING_MEDIA
    
    # Получаем файл
    if update.message.photo:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        filename = f"greeting_{user_id}_{photo.file_id}.jpg"
    elif update.message.document:
        document = update.message.document
        file = await context.bot.get_file(document.file_id)
        filename = f"greeting_{user_id}_{document.file_id}_{document.file_name}"
    else:
        await update.message.reply_text("❌ Пожалуйста, отправьте изображение")
        return GREETING_MEDIA
    
    # Сохраняем файл
    filepath = MEDIA_DIR / filename
    await file.download_to_drive(filepath)
    
    # Добавляем путь в список
    if 'greeting_media_files' not in context.user_data:
        context.user_data['greeting_media_files'] = []
    
    context.user_data['greeting_media_files'].append(str(filepath))
    
    count = len(context.user_data['greeting_media_files'])
    
    keyboard = [[InlineKeyboardButton("✅ Завершить", callback_data="greeting_media_done")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"✅ Изображение {count} сохранено!\n\n"
        f"Можете отправить еще (всего до 10) или нажмите 'Завершить'.",
        reply_markup=reply_markup
    )
    
    return GREETING_MEDIA


async def greeting_media_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Завершить добавление медиа"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not is_admin(user_id):
        await query.edit_message_text("⛔️ У вас нет прав доступа")
        return ConversationHandler.END
    
    media_files = context.user_data.get('greeting_media_files', [])
    
    if not media_files:
        await query.edit_message_text("❌ Не было добавлено ни одного изображения")
        return ConversationHandler.END
    
    # Сохраняем пути к файлам в БД (через запятую)
    db = get_db()
    try:
        media_paths_str = ','.join(media_files)
        
        setting = db.query(BotSettings).filter_by(setting_key='greeting_media_paths').first()
        
        if setting:
            # Удаляем старые файлы
            if setting.setting_value:
                old_paths = setting.setting_value.split(',')
                for old_path in old_paths:
                    old_path = old_path.strip()
                    if old_path and Path(old_path).exists():
                        try:
                            Path(old_path).unlink()
                        except Exception as e:
                            logger.warning(f"Не удалось удалить старый файл {old_path}: {e}")
            
            setting.setting_value = media_paths_str
        else:
            setting = BotSettings(setting_key='greeting_media_paths', setting_value=media_paths_str)
            db.add(setting)
        
        db.commit()
        logger.info(f"Обновлены медиа-файлы приветствия: {len(media_files)} файлов")
        
        keyboard = [[InlineKeyboardButton("🔙 В меню приветствий", callback_data="admin_edit_greeting")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.reply_text(
            f"✅ <b>Медиа успешно добавлены!</b>\n\n"
            f"Сохранено файлов: {len(media_files)}",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
        context.user_data.clear()
        return ConversationHandler.END
        
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка при сохранении медиа: {e}")
        await query.message.reply_text("❌ Ошибка при сохранении медиа")
        return ConversationHandler.END
    finally:
        db.close()


async def greeting_delete_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удалить все медиа"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not is_admin(user_id):
        await query.edit_message_text("⛔️ У вас нет прав доступа")
        return
    
    db = get_db()
    try:
        setting = db.query(BotSettings).filter_by(setting_key='greeting_media_paths').first()
        
        if setting and setting.setting_value:
            # Удаляем файлы
            paths = setting.setting_value.split(',')
            for path in paths:
                path = path.strip()
                if path and Path(path).exists():
                    try:
                        Path(path).unlink()
                    except Exception as e:
                        logger.warning(f"Не удалось удалить файл {path}: {e}")
            
            # Очищаем значение в БД
            setting.setting_value = None
            db.commit()
            
            logger.info(f"Удалены медиа-файлы приветствия")
            
            keyboard = [[InlineKeyboardButton("🔙 В меню приветствий", callback_data="admin_edit_greeting")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.reply_text(
                "✅ <b>Все медиа успешно удалены!</b>",
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        else:
            await query.edit_message_text("ℹ️ Медиа не были добавлены")
            
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка при удалении медиа: {e}")
        await query.message.reply_text("❌ Ошибка при удалении медиа")
    finally:
        db.close()


async def greeting_edit_button_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать редактирование кнопки"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not is_admin(user_id):
        await query.edit_message_text("⛔️ У вас нет прав доступа")
        return ConversationHandler.END
    
    await query.edit_message_text(
        "🔘 <b>Редактирование кнопки</b>\n\n"
        "Отправьте текст для кнопки.\n\n"
        "Или отправьте /cancel для отмены",
        parse_mode='HTML'
    )
    
    return GREETING_BUTTON_TEXT


async def greeting_save_button_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохранить текст кнопки"""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔️ У вас нет прав доступа")
        return ConversationHandler.END
    
    button_text = update.message.text
    context.user_data['greeting_button_text'] = button_text
    
    await update.message.reply_text(
        f"✅ Текст кнопки: <b>{button_text}</b>\n\n"
        f"Теперь отправьте URL для кнопки\n"
        f"(например: https://t.me/your_channel)\n\n"
        f"Или отправьте /cancel для отмены",
        parse_mode='HTML'
    )
    
    return GREETING_BUTTON_URL


async def greeting_save_button_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохранить URL кнопки"""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔️ У вас нет прав доступа")
        return ConversationHandler.END
    
    button_url = update.message.text.strip()
    button_text = context.user_data.get('greeting_button_text')
    
    # Проверяем формат URL
    if not (button_url.startswith('http://') or button_url.startswith('https://')):
        await update.message.reply_text(
            "❌ Неверный формат URL!\n\n"
            "URL должен начинаться с http:// или https://\n\n"
            "Отправьте правильный URL или /cancel для отмены"
        )
        return GREETING_BUTTON_URL
    
    # Сохраняем в БД
    db = get_db()
    try:
        # Сохраняем текст кнопки
        text_setting = db.query(BotSettings).filter_by(setting_key='greeting_button_text').first()
        if text_setting:
            text_setting.setting_value = button_text
        else:
            text_setting = BotSettings(setting_key='greeting_button_text', setting_value=button_text)
            db.add(text_setting)
        
        # Сохраняем URL кнопки
        url_setting = db.query(BotSettings).filter_by(setting_key='greeting_button_url').first()
        if url_setting:
            url_setting.setting_value = button_url
        else:
            url_setting = BotSettings(setting_key='greeting_button_url', setting_value=button_url)
            db.add(url_setting)
        
        db.commit()
        logger.info(f"Обновлена кнопка приветствия: {button_text} -> {button_url}")
        
        keyboard = [[InlineKeyboardButton("🔙 В меню приветствий", callback_data="admin_edit_greeting")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ <b>Кнопка успешно обновлена!</b>\n\n"
            f"<b>Текст:</b> {button_text}\n"
            f"<b>URL:</b> {button_url}",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
        context.user_data.clear()
        return ConversationHandler.END
        
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка при сохранении кнопки: {e}")
        await update.message.reply_text("❌ Ошибка при сохранении кнопки")
        return ConversationHandler.END
    finally:
        db.close()


async def greeting_delete_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удалить кнопку"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not is_admin(user_id):
        await query.edit_message_text("⛔️ У вас нет прав доступа")
        return
    
    db = get_db()
    try:
        text_setting = db.query(BotSettings).filter_by(setting_key='greeting_button_text').first()
        url_setting = db.query(BotSettings).filter_by(setting_key='greeting_button_url').first()
        
        if text_setting:
            text_setting.setting_value = None
        if url_setting:
            url_setting.setting_value = None
        
        db.commit()
        logger.info("Удалена кнопка приветствия")
        
        keyboard = [[InlineKeyboardButton("🔙 В меню приветствий", callback_data="admin_edit_greeting")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.reply_text(
            "✅ <b>Кнопка успешно удалена!</b>",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка при удалении кнопки: {e}")
        await query.message.reply_text("❌ Ошибка при удалении кнопки")
    finally:
        db.close()


async def greeting_preview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать предпросмотр приветствия"""
    query = update.callback_query
    await query.answer("Отправляю предпросмотр...")
    
    user_id = query.from_user.id
    if not is_admin(user_id):
        await query.edit_message_text("⛔️ У вас нет прав доступа")
        return
    
    # Импортируем функцию отправки приветствия
    from join_request_handler import send_greeting_message
    
    # Отправляем приветствие админу
    try:
        await send_greeting_message(context, user_id)
        await query.message.reply_text("✅ Предпросмотр отправлен!")
    except Exception as e:
        logger.error(f"Ошибка при отправке предпросмотра: {e}")
        await query.message.reply_text("❌ Ошибка при отправке предпросмотра")


async def cancel_greeting_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена редактирования приветствия"""
    if update.callback_query:
        query = update.callback_query
        await query.answer()
    
    # Удаляем временные файлы, если они есть
    if 'greeting_media_files' in context.user_data:
        for filepath in context.user_data['greeting_media_files']:
            if Path(filepath).exists():
                try:
                    Path(filepath).unlink()
                except Exception as e:
                    logger.warning(f"Не удалось удалить временный файл {filepath}: {e}")
    
    keyboard = [[InlineKeyboardButton("🔙 В админ-панель", callback_data="admin_back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            "❌ Редактирование отменено",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            "❌ Редактирование отменено",
            reply_markup=reply_markup
        )
    
    context.user_data.clear()
    return ConversationHandler.END


def setup_admin_handlers(application):
    """Настройка обработчиков админ-панели"""
    
    # Главное меню
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CallbackQueryHandler(show_statistics, pattern="^admin_stats$"))
    application.add_handler(CallbackQueryHandler(export_statistics, pattern="^admin_export_stats$"))
    
    # Простые callback для удаления медиа/кнопки (не требуют conversation)
    application.add_handler(CallbackQueryHandler(greeting_delete_media, pattern="^greeting_delete_media$"))
    application.add_handler(CallbackQueryHandler(greeting_delete_button, pattern="^greeting_delete_button$"))
    application.add_handler(CallbackQueryHandler(greeting_preview, pattern="^greeting_preview$"))
    
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
    
    # Conversation handler для установки инвайт-ссылки
    invite_link_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(set_invite_link_start, pattern="^admin_set_invite_link$")],
        states={
            SET_INVITE_LINK: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_invite_link)
            ]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_set_link),
            CallbackQueryHandler(admin_back, pattern="^admin_back$")
        ],
        per_user=True,
        per_chat=True,
        name="invite_link_conversation"
    )
    application.add_handler(invite_link_conv)
    
    # Conversation handler для редактирования приветственного сообщения
    greeting_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(edit_greeting_menu, pattern="^admin_edit_greeting$")],
        states={
            GREETING_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, greeting_save_text)
            ],
            GREETING_MEDIA: [
                MessageHandler(filters.PHOTO, greeting_receive_media),
                MessageHandler(filters.Document.IMAGE, greeting_receive_media),
                CallbackQueryHandler(greeting_media_done, pattern="^greeting_media_done$")
            ],
            GREETING_BUTTON_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, greeting_save_button_text)
            ],
            GREETING_BUTTON_URL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, greeting_save_button_url)
            ]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_greeting_edit),
            CallbackQueryHandler(admin_back, pattern="^admin_back$")
        ],
        per_user=True,
        per_chat=True,
        name="greeting_conversation",
        # Дополнительные entry_points для подменю
        map_to_parent={
            ConversationHandler.END: ConversationHandler.END
        }
    )
    
    # Добавляем вложенные entry points для greeting conversation
    greeting_conv.entry_points.extend([
        CallbackQueryHandler(greeting_edit_text_start, pattern="^greeting_edit_text$"),
        CallbackQueryHandler(greeting_add_media_start, pattern="^greeting_add_media$"),
        CallbackQueryHandler(greeting_edit_button_start, pattern="^greeting_edit_button$")
    ])
    
    application.add_handler(greeting_conv)
    
    # Глобальный обработчик admin_back (должен быть ПОСЛЕ всех ConversationHandler'ов)
    # Сработает только если пользователь не находится в активном conversation
    application.add_handler(CallbackQueryHandler(admin_back, pattern="^admin_back$"))
    
    logger.info("Обработчики админ-панели настроены")


