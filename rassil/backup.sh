#!/bin/bash
# Скрипт автоматического резервного копирования

BACKUP_DIR="/backup/eldorado_bot"
DATE=$(date +%Y%m%d_%H%M%S)
BOT_DIR="/opt/eldorado_bot"
LOG_FILE="/var/log/eldorado_bot/backup.log"

# Создание директории для бэкапов
mkdir -p $BACKUP_DIR

echo "$(date): Начало резервного копирования" >> $LOG_FILE

# Резервная копия базы данных
echo "$(date): Резервная копия БД..." >> $LOG_FILE
sudo -u postgres pg_dump eldorado_bot_db > $BACKUP_DIR/db_$DATE.sql

if [ $? -eq 0 ]; then
    echo "$(date): БД успешно сохранена" >> $LOG_FILE
    gzip $BACKUP_DIR/db_$DATE.sql
else
    echo "$(date): ОШИБКА при резервном копировании БД" >> $LOG_FILE
fi

# Резервная копия файлов
echo "$(date): Резервная копия файлов..." >> $LOG_FILE
tar -czf $BACKUP_DIR/files_$DATE.tar.gz \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    $BOT_DIR

if [ $? -eq 0 ]; then
    echo "$(date): Файлы успешно сохранены" >> $LOG_FILE
else
    echo "$(date): ОШИБКА при резервном копировании файлов" >> $LOG_FILE
fi

# Удаление старых копий (старше 7 дней)
echo "$(date): Удаление старых резервных копий..." >> $LOG_FILE
find $BACKUP_DIR -name "db_*.sql.gz" -mtime +7 -delete
find $BACKUP_DIR -name "files_*.tar.gz" -mtime +7 -delete

echo "$(date): Резервное копирование завершено" >> $LOG_FILE
echo "========================================" >> $LOG_FILE

# Статистика места на диске
df -h $BACKUP_DIR >> $LOG_FILE
echo "" >> $LOG_FILE

