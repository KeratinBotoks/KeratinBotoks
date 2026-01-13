# 🎮 Симулятор Магната - Telegram игра

Экономический симулятор с бизнесами, биржей и рейтингами игроков.

## 🚀 Деплой на Railway

### 1. Предварительные требования
- [GitHub аккаунт](https://github.com)
- [Telegram бот](https://t.me/BotFather)
- [Railway аккаунт](https://railway.app)

### 2. Создание бота в Telegram
1. Найдите `@BotFather` в Telegram
2. Отправьте `/newbot`
3. Выберите имя бота (например: `MyTycoonBot`)
4. Выберите username (например: `my_tycoon_bot`)
5. **ВАЖНО:** Отключите режим конфиденциальности:
   - `/mybots` → ваш бот → Bot Settings → Group Privacy → Turn OFF
6. Скопируйте токен (выглядит как: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 3. Настройка проекта на Railway

#### Вариант A: Через GitHub (рекомендуется)
1. Загрузите проект на GitHub
2. Перейдите на [Railway.app](https://railway.app)
3. Нажмите "Start a New Project"
4. Выберите "Deploy from GitHub repo"
5. Авторизуйте доступ к вашему GitHub
6. Выберите репозиторий `simulator-tycoon`

#### Вариант B: Через Railway CLI
```bash
# Установите Railway CLI
npm i -g @railway/cli

# Войдите в Railway
railway login

# Создайте новый проект
railway init

# Деплой
railway up