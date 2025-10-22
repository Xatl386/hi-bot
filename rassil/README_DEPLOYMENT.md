# 🚀 Руководство по развертыванию Eldorado Trade Bot

## Краткая инструкция - 3 простых шага

### Вариант 1: Автоматическое развертывание (РЕКОМЕНДУЕТСЯ)

```bash
# 1. Загрузите файлы на сервер
scp -r /path/to/project root@your-server:/tmp/eldorado_bot

# 2. Подключитесь к серверу
ssh root@your-server

# 3. Запустите автоматическую установку
cd /tmp/eldorado_bot
bash deploy_server.sh
```

**Готово!** Бот установлен и работает.

---

## Что входит в комплект

### 📄 Файлы для развертывания

| Файл | Описание |
|------|----------|
| `eldorado_bot.service` | Systemd служба для автозапуска |
| `deploy_server.sh` | Автоматический скрипт развертывания |
| `bot_control.sh` | Интерактивная панель управления |
| `backup.sh` | Скрипт резервного копирования |
| `check_bot.sh` | Мониторинг и автоперезапуск |
| `install_requirements.sh` | Установка/обновление зависимостей |

### 📚 Документация

| Файл | Описание |
|------|----------|
| `РАЗВЕРТЫВАНИЕ_НА_СЕРВЕРЕ.md` | Полная инструкция по развертыванию |
| `КОМАНДЫ_СЕРВЕРА.md` | Справочник всех команд |
| `НОВЫЙ_ФУНКЦИОНАЛ.md` | Описание всех возможностей |
| `БЫСТРЫЙ_СТАРТ.md` | Краткое руководство |
| `МИГРАЦИЯ_С_СТАРОЙ_ВЕРСИИ.md` | Переход со старой версии |

---

## Требования к серверу

- **OS:** Ubuntu 20.04+ / Debian 11+
- **RAM:** 1 GB минимум (2 GB рекомендуется)
- **Диск:** 10 GB минимум
- **Сеть:** Доступ в интернет

---

## Быстрая установка

### Метод 1: Полностью автоматический

Самый простой способ - использовать скрипт `deploy_server.sh`:

```bash
# На сервере
cd /tmp
git clone https://your-repo/eldorado-bot.git
cd eldorado-bot
sudo bash deploy_server.sh
```

Скрипт спросит:
- Токен бота (от @BotFather)
- ID канала (например: -1001234567890)
- ID администратора (ваш Telegram ID)

Все остальное настроится автоматически.

### Метод 2: Ручная установка

Если нужен контроль над каждым шагом, используйте ручную установку из файла `РАЗВЕРТЫВАНИЕ_НА_СЕРВЕРЕ.md`.

---

## После установки

### 1. Проверьте статус

```bash
sudo systemctl status eldorado_bot
```

Должно быть: `Active: active (running)`

### 2. Посмотрите логи

```bash
sudo journalctl -u eldorado_bot -f
```

### 3. Настройте приветствия

В Telegram отправьте боту:
```
/admin → 👋 Редактировать приветствие
```

---

## Управление ботом

### Интерактивная панель

```bash
sudo bash /opt/eldorado_bot/bot_control.sh
```

Панель управления предоставляет:
- Просмотр статуса
- Запуск/остановка/перезапуск
- Просмотр логов
- Обновление
- Резервное копирование
- Очистка логов

### Основные команды

```bash
# Статус
sudo systemctl status eldorado_bot

# Перезапуск
sudo systemctl restart eldorado_bot

# Логи
sudo journalctl -u eldorado_bot -f

# База данных
sudo -u postgres psql eldorado_bot_db
```

Полный список команд в файле `КОМАНДЫ_СЕРВЕРА.md`.

---

## Структура после установки

```
/opt/eldorado_bot/          # Директория бота
├── venv/                   # Виртуальное окружение Python
├── main.py                 # Главный файл
├── bot_core.py             # Логика бота
├── admin_panel.py          # Админ-панель
├── *.py                    # Другие модули
├── .env                    # Конфигурация (chmod 600)
├── media/                  # Медиа-файлы
└── *.sh                    # Скрипты управления

/var/log/eldorado_bot/      # Логи
├── bot.log                 # Основной лог
├── error.log               # Ошибки
├── backup.log              # Лог резервных копий
└── monitoring.log          # Лог мониторинга

/etc/systemd/system/        # Системные службы
└── eldorado_bot.service    # Служба бота

/backup/eldorado_bot/       # Резервные копии
├── db_*.sql.gz            # Дампы БД
└── files_*.tar.gz         # Архивы файлов
```

---

## Автоматизация

### Резервное копирование

Добавьте в cron для ежедневного бэкапа в 3:00:

```bash
sudo crontab -e
```

Добавьте:
```
0 3 * * * /opt/eldorado_bot/backup.sh
```

### Мониторинг

Добавьте проверку каждые 5 минут:

```bash
sudo crontab -e
```

Добавьте:
```
*/5 * * * * /opt/eldorado_bot/check_bot.sh
```

---

## Обновление бота

### Быстрое обновление

```bash
sudo systemctl stop eldorado_bot
cd /opt/eldorado_bot
git pull  # или загрузите новые файлы
sudo -u botuser bash -c "source venv/bin/activate && pip install -r requirements.txt"
sudo systemctl start eldorado_bot
```

### Безопасное обновление

Используйте панель управления:

```bash
sudo bash /opt/eldorado_bot/bot_control.sh
# Выберите: 8) Обновить бота
```

---

## Траблшутинг

### Бот не запускается

```bash
# Проверьте логи
sudo journalctl -u eldorado_bot -n 50

# Попробуйте запустить вручную
sudo -u botuser bash
cd /opt/eldorado_bot
source venv/bin/activate
python main.py
```

### Ошибка подключения к БД

```bash
# Проверьте PostgreSQL
sudo systemctl status postgresql

# Проверьте настройки
sudo cat /opt/eldorado_bot/.env | grep DATABASE_URL
```

### Недостаточно прав

```bash
# Установите правильные права
sudo chown -R botuser:botuser /opt/eldorado_bot
sudo chmod 600 /opt/eldorado_bot/.env
```

Полный список решений в `РАЗВЕРТЫВАНИЕ_НА_СЕРВЕРЕ.md`.

---

## Безопасность

### Обязательные настройки

1. **Защита .env файла:**
   ```bash
   sudo chmod 600 /opt/eldorado_bot/.env
   ```

2. **Настройка firewall:**
   ```bash
   sudo ufw allow 22/tcp
   sudo ufw enable
   ```

3. **Сложный пароль БД:**
   - Используйте сгенерированный пароль из скрипта
   - Не используйте простые пароли

4. **Регулярные обновления:**
   ```bash
   sudo apt update && sudo apt upgrade
   ```

---

## Мониторинг и логи

### Просмотр логов

```bash
# Реальное время
sudo journalctl -u eldorado_bot -f

# Последние ошибки
sudo journalctl -u eldorado_bot -p err

# Файлы логов
sudo tail -f /var/log/eldorado_bot/bot.log
```

### Статистика использования

```bash
# Процессор и память
top -p $(pgrep -f "python.*main.py")

# Дисковое пространство
df -h

# Размер БД
sudo -u postgres psql -c "SELECT pg_size_pretty(pg_database_size('eldorado_bot_db'));"
```

---

## Резервное копирование

### Автоматическое

Настройте автоматическое резервное копирование:

```bash
# Добавить в cron
sudo crontab -e

# Ежедневно в 3:00
0 3 * * * /opt/eldorado_bot/backup.sh
```

### Ручное

```bash
# Создать резервную копию
sudo bash /opt/eldorado_bot/backup.sh

# Или через панель управления
sudo bash /opt/eldorado_bot/bot_control.sh
# Выберите: 9) Резервная копия
```

### Восстановление

```bash
# Остановить бота
sudo systemctl stop eldorado_bot

# Восстановить БД
sudo -u postgres psql eldorado_bot_db < /backup/eldorado_bot/db_20251022.sql

# Восстановить файлы
sudo tar -xzf /backup/eldorado_bot/files_20251022.tar.gz -C /

# Запустить бота
sudo systemctl start eldorado_bot
```

---

## Масштабирование

### При росте нагрузки

1. **Увеличьте RAM** до 4 GB
2. **Оптимизируйте PostgreSQL:**
   ```bash
   sudo nano /etc/postgresql/*/main/postgresql.conf
   ```
   Увеличьте `shared_buffers` и `effective_cache_size`

3. **Используйте SSD** вместо HDD

---

## Полезные ссылки

- 📖 [Полная инструкция по развертыванию](РАЗВЕРТЫВАНИЕ_НА_СЕРВЕРЕ.md)
- 🔧 [Справочник команд](КОМАНДЫ_СЕРВЕРА.md)
- 🎯 [Новый функционал](НОВЫЙ_ФУНКЦИОНАЛ.md)
- 🚀 [Быстрый старт](БЫСТРЫЙ_СТАРТ.md)
- 📦 [Миграция со старой версии](МИГРАЦИЯ_С_СТАРОЙ_ВЕРСИИ.md)

---

## Поддержка

При возникновении проблем:

1. Проверьте логи: `sudo journalctl -u eldorado_bot -f`
2. Изучите документацию в файлах выше
3. Проверьте права доступа к файлам
4. Убедитесь, что PostgreSQL работает

---

## Checklist развертывания

После развертывания проверьте:

- [ ] Бот запущен: `systemctl status eldorado_bot`
- [ ] Логи без ошибок
- [ ] БД подключена и работает
- [ ] Бот отвечает на `/start`
- [ ] Админ-панель работает: `/admin`
- [ ] Автопринятие заявок настроено
- [ ] Приветствия отправляются
- [ ] Рассылки работают
- [ ] .env защищен (chmod 600)
- [ ] Резервное копирование настроено
- [ ] Мониторинг работает

---

**Готово!** Бот развернут и готов к работе 24/7 🚀

Для управления используйте интерактивную панель:
```bash
sudo bash /opt/eldorado_bot/bot_control.sh
```

