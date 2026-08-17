"""Бот Blip VPN: выдаёт APK и инструкцию по установке."""

import json
import logging
import os
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# Ссылка на arm64-версию APK (GitHub Release). Файл на сервере не хранится.
APK_URL = os.environ.get(
    "APK_URL",
    "https://github.com/PaulAndGit/blip-policy/releases/download/v1.0/blip-vpn-1.0-arm64.apk",
)
DATA_FILE = Path("data.json")

INSTRUCTIONS = """📲 Как установить Blip VPN

1. Нажми «Скачать APK» и дождись загрузки файла.
2. Открой скачанный файл. Android спросит разрешение — разреши «Установку из неизвестных источников» для файлового менеджера/браузера.
3. Нажми «Установить» и дождись завершения.
4. Открой приложение Blip.
5. Прими условия использования (политика конфиденциальности доступна по кнопке).
6. Выбери сервер в списке или импортируй свою подписку.
7. Нажми большую кнопку подключения.
8. При первом подключении Android спросит доступ к VPN — разреши и отметь «Запоминать выбор».

Готово — ваш трафик зашифрован.

ℹ️ Blip VPN бесплатен, без рекламы и не собирает персональные данные. Серверы предоставляются третьими лицами: приложение не управляет ими и не гарантирует их доступность. Использование VPN регулируется законодательством вашей страны."""

WELCOME = """👋 Привет! Это официальный бот Blip VPN.

Здесь можно скачать приложение и прочитать инструкцию по установке.

Выберите действие ниже:"""

APK_CAPTION = """📦 Blip VPN v1.0

Версия для современных устройств (64-бит, Android 7+). Установка: разрешите установку из неизвестных источников, откройте файл и нажмите «Установить».

Подробная инструкция — в разделе «Инструкция»."""


def load_stats() -> dict:
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {"downloads": 0}


def save_stats(stats: dict) -> None:
    DATA_FILE.write_text(json.dumps(stats), encoding="utf-8")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📦 Скачать APK", callback_data="apk")],
            [InlineKeyboardButton("📋 Инструкция", callback_data="help")],
        ]
    )
    await update.message.reply_text(WELCOME, reply_markup=kb)


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if query.data == "apk":
        stats = load_stats()
        stats["downloads"] += 1
        save_stats(stats)
        await query.message.reply_document(document=APK_URL, caption=APK_CAPTION)
    elif query.data == "help":
        await query.message.reply_text(INSTRUCTIONS)


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    s = load_stats()
    await update.message.reply_text(f"Всего скачиваний: {s['downloads']}")


def main() -> None:
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise SystemExit("BOT_TOKEN не задан (переменная окружения)")
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CallbackQueryHandler(button))
    logging.info("Бот запущен")
    app.run_polling()


if __name__ == "__main__":
    main()
