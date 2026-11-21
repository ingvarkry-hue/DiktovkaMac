#!/bin/bash
# Установка «Диктовки» для macOS: окружение, библиотеки, модель, приложение.
set -e
cd "$(dirname "$0")"

echo "==> Проверяю Python…"
if ! command -v python3 >/dev/null; then
    echo "Python не найден. Установите: brew install python3"
    exit 1
fi
python3 --version

echo "==> Создаю виртуальное окружение…"
python3 -m venv venv
./venv/bin/python -m pip install --upgrade pip >/dev/null

echo "==> Ставлю библиотеки…"
./venv/bin/pip install -r requirements.txt

echo "==> Подготавливаю config.json…"
[ -f config.json ] || cp config.example.json config.json

echo "==> Скачиваю модель распознавания (~1,6 ГБ, один раз)…"
./venv/bin/python diktovka_mac.py --download

echo "==> Собираю Diktovka.app…"
bash make_app.sh

echo
echo "Готово! Сейчас откроется macOS с вопросом про «Универсальный доступ» — разрешите."
echo "После этого нажмите 英数 (или свою клавишу из config.json) и говорите."
open Diktovka.app
