# 🎮 Симулятор Магната - Telegram Bot

Экономическая игра с бизнесом, биржей и инвестициями.

## 🚀 Быстрый запуск на Railway

### 1. Подготовка
1. Создайте бота через [@BotFather](https://t.me/BotFather)
2. Скопируйте токен бота
3. Создайте публичный канал для статистики (опционально)

### 2. Развертывание на Railway

**Способ 1: Через GitHub**
1. Форкните или загрузите проект в GitHub
2. Перейдите на [Railway](https://railway.app)
3. Нажмите "New Project" → "Deploy from GitHub repo"
4. Выберите ваш репозиторий
5. Добавьте переменные окружения (Environment Variables):
   - `BOT_TOKEN` - токен вашего бота
   - `CHANNEL_ID` - ID канала для статистики (опционально)
6. Нажмите "Deploy"

**Способ 2: Через Railway CLI**
1. Установите Railway CLI:
   ```bash
   npm i -g @railway/cli