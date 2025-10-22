#!/bin/bash
# Скрипт управления Eldorado Trade Bot

SERVICE_NAME="eldorado_bot"
BOT_DIR="/opt/eldorado_bot"
LOG_DIR="/var/log/eldorado_bot"

# Цвета
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

show_menu() {
    clear
    echo "================================================"
    echo "    Eldorado Trade Bot - Панель управления"
    echo "================================================"
    echo ""
    echo "1) Статус бота"
    echo "2) Запустить бота"
    echo "3) Остановить бота"
    echo "4) Перезапустить бота"
    echo "5) Просмотр логов (live)"
    echo "6) Просмотр последних 50 строк логов"
    echo "7) Просмотр ошибок"
    echo "8) Обновить бота"
    echo "9) Резервная копия"
    echo "10) Очистить логи"
    echo "0) Выход"
    echo ""
    echo -n "Выберите действие: "
}

check_status() {
    echo ""
    print_info "Проверка статуса службы..."
    echo ""
    systemctl status $SERVICE_NAME --no-pager
    echo ""
    
    if systemctl is-active --quiet $SERVICE_NAME; then
        print_success "Бот работает"
    else
        print_error "Бот не работает"
    fi
    echo ""
}

start_bot() {
    echo ""
    print_info "Запуск бота..."
    systemctl start $SERVICE_NAME
    sleep 2
    if systemctl is-active --quiet $SERVICE_NAME; then
        print_success "Бот успешно запущен"
    else
        print_error "Не удалось запустить бота"
        echo ""
        print_info "Последние строки логов:"
        journalctl -u $SERVICE_NAME -n 10 --no-pager
    fi
    echo ""
}

stop_bot() {
    echo ""
    print_info "Остановка бота..."
    systemctl stop $SERVICE_NAME
    sleep 2
    if ! systemctl is-active --quiet $SERVICE_NAME; then
        print_success "Бот успешно остановлен"
    else
        print_error "Не удалось остановить бота"
    fi
    echo ""
}

restart_bot() {
    echo ""
    print_info "Перезапуск бота..."
    systemctl restart $SERVICE_NAME
    sleep 2
    if systemctl is-active --quiet $SERVICE_NAME; then
        print_success "Бот успешно перезапущен"
    else
        print_error "Не удалось перезапустить бота"
    fi
    echo ""
}

view_logs_live() {
    echo ""
    print_info "Просмотр логов в реальном времени (Ctrl+C для выхода)..."
    echo ""
    sleep 1
    journalctl -u $SERVICE_NAME -f
}

view_logs_tail() {
    echo ""
    print_info "Последние 50 строк логов:"
    echo ""
    journalctl -u $SERVICE_NAME -n 50 --no-pager
    echo ""
}

view_errors() {
    echo ""
    print_info "Ошибки из логов:"
    echo ""
    if [ -f "$LOG_DIR/error.log" ]; then
        tail -n 50 $LOG_DIR/error.log
    else
        print_warning "Файл ошибок не найден"
    fi
    echo ""
}

update_bot() {
    echo ""
    print_warning "Обновление бота..."
    echo ""
    
    read -p "Вы уверены? Это остановит бота на время обновления (y/n): " confirm
    if [ "$confirm" != "y" ]; then
        print_info "Обновление отменено"
        return
    fi
    
    echo ""
    print_info "Остановка бота..."
    systemctl stop $SERVICE_NAME
    
    print_info "Создание резервной копии..."
    backup_date=$(date +%Y%m%d_%H%M%S)
    cp -r $BOT_DIR /opt/eldorado_bot_backup_$backup_date
    print_success "Резервная копия создана: /opt/eldorado_bot_backup_$backup_date"
    
    print_info "Обновление зависимостей..."
    cd $BOT_DIR
    source venv/bin/activate
    pip install --upgrade -r requirements.txt
    deactivate
    
    print_info "Запуск бота..."
    systemctl start $SERVICE_NAME
    sleep 2
    
    if systemctl is-active --quiet $SERVICE_NAME; then
        print_success "Бот успешно обновлен и запущен"
    else
        print_error "Ошибка при запуске обновленного бота"
        print_warning "Восстановите из резервной копии если нужно"
    fi
    echo ""
}

backup_bot() {
    echo ""
    print_info "Создание резервной копии..."
    
    backup_date=$(date +%Y%m%d_%H%M%S)
    backup_dir="/backup/eldorado_bot"
    
    mkdir -p $backup_dir
    
    # Резервная копия БД
    print_info "Резервная копия базы данных..."
    sudo -u postgres pg_dump eldorado_bot_db > $backup_dir/db_$backup_date.sql
    
    # Резервная копия файлов
    print_info "Резервная копия файлов..."
    tar -czf $backup_dir/files_$backup_date.tar.gz $BOT_DIR
    
    print_success "Резервная копия создана:"
    echo "  БД: $backup_dir/db_$backup_date.sql"
    echo "  Файлы: $backup_dir/files_$backup_date.tar.gz"
    echo ""
}

clear_logs() {
    echo ""
    print_warning "Очистка логов..."
    echo ""
    
    read -p "Вы уверены? Все логи будут удалены (y/n): " confirm
    if [ "$confirm" != "y" ]; then
        print_info "Очистка отменена"
        return
    fi
    
    journalctl --vacuum-time=1d
    
    if [ -f "$LOG_DIR/bot.log" ]; then
        > $LOG_DIR/bot.log
    fi
    
    if [ -f "$LOG_DIR/error.log" ]; then
        > $LOG_DIR/error.log
    fi
    
    print_success "Логи очищены"
    echo ""
}

# Проверка прав root
if [ "$EUID" -ne 0 ]; then 
    print_error "Запустите скрипт с правами root: sudo bash bot_control.sh"
    exit 1
fi

# Основной цикл
while true; do
    show_menu
    read choice
    
    case $choice in
        1) check_status ;;
        2) start_bot ;;
        3) stop_bot ;;
        4) restart_bot ;;
        5) view_logs_live ;;
        6) view_logs_tail ;;
        7) view_errors ;;
        8) update_bot ;;
        9) backup_bot ;;
        10) clear_logs ;;
        0) 
            echo ""
            print_info "Выход..."
            exit 0
            ;;
        *)
            print_error "Неверный выбор"
            ;;
    esac
    
    if [ "$choice" != "5" ]; then
        echo ""
        read -p "Нажмите Enter для продолжения..."
    fi
done

