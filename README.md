# Blip VPN Bot

Telegram-бот, который выдаёт APK приложения Blip VPN и инструкцию по установке.

## Возможности
- `/start` — приветствие с кнопками «Скачать APK» и «Инструкция».
- `/stats` — счётчик скачиваний.
- APK отправляется по ссылке из GitHub Release (файл не хранится на сервере).

## Запуск локально
```bash
pip install -r requirements.txt
set BOT_TOKEN=токен_из_@BotFather
python bot.py
```

## Деплой на Render (бесплатно)
1. Залий эту папку в **публичный** репозиторий GitHub.
2. На [render.com](https://render.com) → **New → Web Service** → выбери репозиторий.
3. Build command: `pip install -r requirements.txt`
4. Start command: `python bot.py`
5. Environment (переменные):
   - `BOT_TOKEN` — токен бота (обязательно)
   - `APK_URL` — ссылка на APK (если изменится)
6. **Deploy**.

Бесплатный тариф Render засыпает после 15 мин простоя. Чтобы бот работал всегда:
- на [uptimerobot.com](https://uptimerobot.com) создай **HTTP-монитор** на адрес твоего сервиса с интервалом **5 минут**.

## Получение токена
1. В Telegram: @BotFather → `/newbot` → имя и юзернейм.
2. Скопируй токен (вида `123456:ABC-...`).

> Если токен попал в открытый чат или публичный репозиторий — пересоздай его:
> @BotFather → `/mybots` → твой бот → API Token → Revoke.

## APK
arm64-версия для бота собирается так (в корне проекта):
```powershell
$env:JAVA_HOME="C:\Program Files\Android\Android Studio1\jbr"
.\gradlew.bat :androidApp:assembleRelease -PonlyArm64=true
```
Результат: `androidApp/build/outputs/apk/release/androidApp-release.apk` (~28 МБ).
Загрузи его в GitHub Release и укажи URL в `APK_URL`.
