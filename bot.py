"""Бот Blip VPN: выдаёт APK и инструкцию по установке."""

import io
import json
import logging
import os
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputFile, KeyboardButton, ReplyKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# Ссылка на arm64-версию APK (GitHub Release).
APK_URL = os.environ.get(
    "APK_URL",
    "https://github.com/PaulAndGit/blip-policy/releases/download/v1.2.1/blip-vpn-1.2.1-arm64.apk",
)
APK_FILENAME = "blip-vpn-1.2.1-arm64.apk"
DATA_FILE = Path("data.json")

_APK_BYTES: bytes | None = None
_APK_URL_CACHED: str | None = None
_APK_LOCK = threading.Lock()

INSTRUCTIONS = """📲 Как установить Blip VPN

1. Нажми «Скачать APK» и дождись загрузки файла.
2. Открой скачанный файл. Android спросит разрешение — разреши «Установку из неизвестных источников» для файлового менеджера/браузера.
3. Нажми «Установить» и дождись завершения.
4. Открой приложение Blip.
5. Прими условия использования.
6. Выбери сервер в списке или импортируй свою подписку.
7. Нажми большую кнопку подключения.
8. При первом подключении Android спросит доступ к VPN — разреши и отметь «Запоминать выбор».

Готово — ваш трафик зашифрован.

ℹ️ Blip VPN бесплатен, без рекламы и не собирает персональные данные. Серверы предоставляются третьими лицами: приложение не управляет ими и не гарантирует их доступность. Использование VPN регулируется законодательством вашей страны."""

WELCOME = """👋 Привет! Это официальный бот Blip VPN.

Здесь можно скачать приложение и прочитать инструкцию по установке.

Выберите действие ниже:"""

APK_CAPTION = """📦 Blip VPN v1.2.1

Версия для современных устройств (64-бит, Android 7+). Установка поверх — обновляет существующую.

🆕 Что нового в приложении:
• Kill Switch — блокировка интернета при обрыве туннеля
• Обновление изнутри приложения: «Проверить обновление» → скачать и установить без браузера

Подробная инструкция — в разделе «Инструкция»."""


def reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton("📦 Скачать APK")], [KeyboardButton("📋 Инструкция")]],
        resize_keyboard=True, is_persistent=True,
    )


def main_menu_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📦 Скачать APK", callback_data="apk")],
            [InlineKeyboardButton("📋 Инструкция", callback_data="help")],
        ]
    )


def back_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="back")]])


def download_apk() -> bytes | None:
    """Скачивает APK в память. None — если не получилось."""
    try:
        logging.info("APK download start: %s", APK_URL)
        req = urllib.request.Request(APK_URL, headers={"User-Agent": "BlipBot/1.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
        if not data.startswith(b"PK"):
            logging.error("APK: ответ не похож на zip (%d байт)", len(data))
            return None
        logging.info("APK скачан: %d байт from %s", len(data), APK_URL)
        return data
    except Exception as e:  # noqa: BLE001
        logging.error("APK не скачан: %s", e)
        return None


def ensure_apk() -> bytes | None:
    """Возвращает байты APK, скачивая при необходимости. Инвалидирует кэш при смене URL."""
    global _APK_BYTES, _APK_URL_CACHED
    if _APK_BYTES is not None and _APK_URL_CACHED == APK_URL:
        return _APK_BYTES
    with _APK_LOCK:
        if _APK_BYTES is None or _APK_URL_CACHED != APK_URL:
            logging.info("APK cache miss: cached=%s current=%s", _APK_URL_CACHED, APK_URL)
            data = download_apk()
            if data is not None:
                _APK_BYTES = data
                _APK_URL_CACHED = APK_URL
    return _APK_BYTES


def load_stats() -> dict:
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {"downloads": 0}


def save_stats(stats: dict) -> None:
    DATA_FILE.write_text(json.dumps(stats, ensure_ascii=False), encoding="utf-8")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(WELCOME, reply_markup=reply_keyboard())
    await update.message.reply_text("Выберите действие:", reply_markup=main_menu_markup())


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    try:
        if query.data == "help":
            await query.message.delete()
            await query.message.reply_text(INSTRUCTIONS, reply_markup=back_markup())
            return
        if query.data == "back":
            await query.message.delete()
            await query.message.reply_text(WELCOME, reply_markup=main_menu_markup())
            return
        if query.data == "apk":
            stats = load_stats()
            stats["downloads"] = stats.get("downloads", 0) + 1
            total = stats["downloads"]
            save_stats(stats)
            await query.message.delete()
            caption = f"{APK_CAPTION}\n\n📥 Скачиваний всего: {total}"
            data = ensure_apk()
            if data is not None:
                await context.bot.send_document(
                    chat_id=query.message.chat_id,
                    document=InputFile(io.BytesIO(data), filename=APK_FILENAME),
                    caption=caption,
                    reply_markup=back_markup(),
                )
                return
            try:
                await context.bot.send_document(
                    chat_id=query.message.chat_id, document=APK_URL, caption=caption, reply_markup=back_markup()
                )
                return
            except Exception:  # noqa: BLE001
                logging.exception("Отправка по URL не удалась")
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="⚠️ Не удалось отправить файл. Скачайте APK напрямую:\n\n" + APK_URL,
                reply_markup=back_markup(),
            )
    except Exception:  # noqa: BLE001
        logging.exception("Ошибка в обработчике кнопок")


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "").strip()
    if "Скачать" in text:
        stats = load_stats()
        stats["downloads"] = stats.get("downloads", 0) + 1
        total = stats["downloads"]
        save_stats(stats)
        caption = f"{APK_CAPTION}\n\n📥 Скачиваний всего: {total}"
        data = ensure_apk()
        if data is not None:
            await update.message.reply_document(
                document=InputFile(io.BytesIO(data), filename=APK_FILENAME),
                caption=caption,
                reply_markup=back_markup(),
            )
        else:
            await update.message.reply_text(
                "⚠️ Не удалось отправить файл. Скачайте APK напрямую:\n\n" + APK_URL,
                reply_markup=back_markup(),
            )
    elif "Инструкция" in text:
        await update.message.reply_text(INSTRUCTIONS, reply_markup=back_markup())
    else:
        await update.message.reply_text(WELCOME, reply_markup=main_menu_markup())


def _latest_version() -> str | None:
    """Текущая версия с GitHub Releases (tag без 'v'). None при ошибке."""
    try:
        req = urllib.request.Request(
            "https://api.github.com/repos/PaulAndGit/blip-policy/releases/latest",
            headers={"User-Agent": "BlipBot/1.0"},
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
        tag = data.get("tag_name", "")
        return tag.removeprefix("v") or None
    except Exception as e:  # noqa: BLE001
        logging.error("latest version: %s", e)
        return None


def _parse_ver(v: str) -> list[int]:
    return [int(x) for x in v.strip().removeprefix("v").split(".") if x.isdigit()]


async def version_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/version 1.2 — сравнить установленную версию с последней на GitHub."""
    installed = context.args[0].strip() if context.args else ""
    latest = _latest_version()
    if latest is None:
        await update.message.reply_text("⚠️ Не удалось узнать последнюю версию. Попробуйте позже.")
        return
    if not installed:
        await update.message.reply_text(
            f"Последняя версия: v{latest}\n\n"
            "Пришлите свою версию так: /version 1.2 — я скажу, нужно ли обновляться."
        )
        return
    try:
        if _parse_ver(installed) < _parse_ver(latest):
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("📦 Скачать APK", callback_data="apk")]])
            await update.message.reply_text(
                f"⬆️ Доступно обновление: v{installed} → v{latest}\nНажмите «Скачать APK».",
                reply_markup=kb,
            )
        else:
            await update.message.reply_text(f"✅ У вас последняя версия (v{installed}).")
    except ValueError:
        await update.message.reply_text("Не понял версию. Формат: /version 1.2")


class _Health(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *args):  # noqa: A003
        pass


def start_health_server() -> None:
    """Мини-HTTP-сервер для health-check хостинга (порт из переменной PORT)."""
    port = int(os.environ.get("PORT", 10000))
    HTTPServer(("0.0.0.0", port), _Health).serve_forever()


def main() -> None:
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise SystemExit("BOT_TOKEN не задан (переменная окружения)")
    threading.Thread(target=start_health_server, daemon=True).start()
    # Загрузка APK в фоне — не блокирует старт polling.
    threading.Thread(target=ensure_apk, daemon=True).start()
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    app.add_handler(CommandHandler("version", version_cmd))
    app.add_handler(CallbackQueryHandler(button))
    logging.info("Бот запущен")
    app.run_polling()


if __name__ == "__main__":
    main()