#!/bin/bash
# Скрипт проверки работы бота и автоматического перезапуска

SERVICE_NAME="eldorado_bot"
LOG_FILE="/var/log/eldorado_bot/monitoring.log"

# Проверка работы службы
if ! systemctl is-active --quiet $SERVICE_NAME; then
    echo "$(date): ⚠️  Бот не работает! Попытка перезапуска..." >> $LOG_FILE
    
    # Перезапуск службы
    systemctl start $SERVICE_NAME
    
    # Проверка через 5 секунд
    sleep 5
    
    if systemctl is-active --quiet $SERVICE_NAME; then
        echo "$(date): ✓ Бот успешно перезапущен" >> $LOG_FILE
    else
        echo "$(date): ✗ Не удалось перезапустить бота!" >> $LOG_FILE
        
        # Отправка уведомления админу (опционально)
        # Здесь можно добавить отправку email или telegram уведомления
    fi
else
    # Бот работает, проверяем использование ресурсов
    CPU=$(ps aux | grep "[p]ython.*main.py" | awk '{print $3}')
    MEM=$(ps aux | grep "[p]ython.*main.py" | awk '{print $4}')
    
    # Если использование CPU или памяти слишком высокое
    if (( $(echo "$CPU > 80" | bc -l) )) || (( $(echo "$MEM > 80" | bc -l) )); then
        echo "$(date): ⚠️  Высокое использование ресурсов: CPU=${CPU}%, MEM=${MEM}%" >> $LOG_FILE
    fi
fi

# Очистка старых логов мониторинга (старше 30 дней)
find $LOG_FILE -mtime +30 -delete 2>/dev/null

