#!/bin/bash
# Скрипт установки/обновления зависимостей Python

BOT_DIR="/opt/eldorado_bot"

echo "================================================"
echo "Установка/обновление зависимостей Python"
echo "================================================"
echo ""

# Проверка существования директории
if [ ! -d "$BOT_DIR" ]; then
    echo "Ошибка: Директория $BOT_DIR не найдена"
    exit 1
fi

cd $BOT_DIR

# Проверка виртуального окружения
if [ ! -d "venv" ]; then
    echo "Создание виртуального окружения..."
    python3 -m venv venv
fi

# Активация окружения
source venv/bin/activate

# Обновление pip
echo "Обновление pip..."
pip install --upgrade pip

# Установка зависимостей
echo ""
echo "Установка зависимостей из requirements.txt..."
pip install -r requirements.txt

echo ""
echo "================================================"
echo "Установка завершена!"
echo "================================================"
echo ""
echo "Установленные пакеты:"
pip list

deactivate

