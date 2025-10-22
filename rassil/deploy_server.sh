#!/bin/bash
# Скрипт автоматического развертывания Eldorado Trade Bot на сервере

set -e  # Остановка при ошибке

echo "================================================"
echo "Развертывание Eldorado Trade Bot"
echo "================================================"
echo ""

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Функция для вывода с цветом
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Проверка прав root
if [ "$EUID" -ne 0 ]; then 
    print_error "Запустите скрипт с правами root: sudo bash deploy_server.sh"
    exit 1
fi

# Настройки
BOT_DIR="/opt/eldorado_bot"
BOT_USER="botuser"
SERVICE_NAME="eldorado_bot"
LOG_DIR="/var/log/eldorado_bot"

echo "Настройки развертывания:"
echo "  Директория: $BOT_DIR"
echo "  Пользователь: $BOT_USER"
echo "  Служба: $SERVICE_NAME"
echo ""

# 1. Обновление системы
echo "Шаг 1/9: Обновление системы..."
apt update && apt upgrade -y
print_success "Система обновлена"

# 2. Установка зависимостей
echo ""
echo "Шаг 2/9: Установка зависимостей..."
apt install -y python3 python3-pip python3-venv postgresql postgresql-contrib nginx git
print_success "Зависимости установлены"

# 3. Создание пользователя для бота
echo ""
echo "Шаг 3/9: Создание пользователя для бота..."
if id "$BOT_USER" &>/dev/null; then
    print_warning "Пользователь $BOT_USER уже существует"
else
    useradd -r -s /bin/bash -d $BOT_DIR $BOT_USER
    print_success "Пользователь $BOT_USER создан"
fi

# 4. Создание директорий
echo ""
echo "Шаг 4/9: Создание директорий..."
mkdir -p $BOT_DIR
mkdir -p $LOG_DIR
mkdir -p $BOT_DIR/media
print_success "Директории созданы"

# 5. Копирование файлов
echo ""
echo "Шаг 5/9: Копирование файлов бота..."
CURRENT_DIR=$(pwd)
cp -r $CURRENT_DIR/* $BOT_DIR/
print_success "Файлы скопированы"

# 6. Создание виртуального окружения
echo ""
echo "Шаг 6/9: Создание виртуального окружения..."
cd $BOT_DIR
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
print_success "Виртуальное окружение создано"

# 7. Настройка .env файла
echo ""
echo "Шаг 7/9: Настройка .env файла..."
if [ ! -f "$BOT_DIR/.env" ]; then
    echo ""
    print_warning "Файл .env не найден. Создаю из шаблона..."
    
    # Запрос данных у пользователя
    read -p "Введите токен бота (BOT_TOKEN): " BOT_TOKEN
    read -p "Введите ID канала (CHANNEL_ID, например -1001234567890): " CHANNEL_ID
    read -p "Введите ID администратора (ADMIN_IDS): " ADMIN_IDS
    
    # Генерация пароля для PostgreSQL
    DB_PASSWORD=$(openssl rand -base64 12)
    
    cat > $BOT_DIR/.env << EOF
# Telegram Bot
BOT_TOKEN=$BOT_TOKEN
CHANNEL_ID=$CHANNEL_ID
ADMIN_IDS=$ADMIN_IDS

# Database
DATABASE_URL=postgresql://eldorado_bot:$DB_PASSWORD@localhost:5432/eldorado_bot_db

# Logging
LOG_LEVEL=INFO
EOF
    
    print_success ".env файл создан"
    echo "Пароль БД: $DB_PASSWORD (сохраните его!)"
else
    print_warning ".env файл уже существует, пропускаю"
fi

# 8. Настройка PostgreSQL
echo ""
echo "Шаг 8/9: Настройка PostgreSQL..."
systemctl start postgresql
systemctl enable postgresql

# Читаем пароль из .env
DB_PASSWORD=$(grep DATABASE_URL $BOT_DIR/.env | cut -d':' -f3 | cut -d'@' -f1)

sudo -u postgres psql -c "CREATE USER eldorado_bot WITH PASSWORD '$DB_PASSWORD';" 2>/dev/null || print_warning "Пользователь БД уже существует"
sudo -u postgres psql -c "CREATE DATABASE eldorado_bot_db OWNER eldorado_bot;" 2>/dev/null || print_warning "База данных уже существует"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE eldorado_bot_db TO eldorado_bot;"

print_success "PostgreSQL настроен"

# 9. Настройка прав доступа
echo ""
echo "Шаг 9/9: Настройка прав доступа..."
chown -R $BOT_USER:$BOT_USER $BOT_DIR
chown -R $BOT_USER:$BOT_USER $LOG_DIR
chmod 600 $BOT_DIR/.env
print_success "Права настроены"

# 10. Установка systemd службы
echo ""
echo "Шаг 10/10: Установка systemd службы..."
cp $BOT_DIR/eldorado_bot.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable $SERVICE_NAME
systemctl start $SERVICE_NAME
print_success "Служба установлена и запущена"

# Проверка статуса
echo ""
echo "================================================"
echo "Развертывание завершено!"
echo "================================================"
echo ""
echo "Проверка статуса службы..."
sleep 2
systemctl status $SERVICE_NAME --no-pager

echo ""
print_success "Бот успешно развернут!"
echo ""
echo "Полезные команды:"
echo "  Статус: systemctl status $SERVICE_NAME"
echo "  Логи: journalctl -u $SERVICE_NAME -f"
echo "  Логи файл: tail -f $LOG_DIR/bot.log"
echo "  Перезапуск: systemctl restart $SERVICE_NAME"
echo "  Остановка: systemctl stop $SERVICE_NAME"
echo ""
echo "Настройте приветствия через /admin в Telegram"
echo ""

