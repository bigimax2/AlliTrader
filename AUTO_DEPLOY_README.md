# Auto-Deploy Documentation

## Как это работает

1. Вы делаете `git push` в репозиторий
2. GitHub отправляет webhook на ваш сервер
3. Django view (`webhook_deploy`) принимает webhook и проверяет подпись
4. Запускается Celery task (`deploy_task`) для выполнения деплоя
5. Скрипт обновляет код, устанавливает зависимости, применяет миграции
6. Сервисы перезапускаются через supervisor
7. Все действия логируются в `deploy.log`

## Архитектура

```
GitHub Repository
       |
       | (POST webhook при push)
       ↓
   [Server]
   ┌─────────────────────┐
   | webhook_deploy      | ← Django endpoint для приема webhook
   └─────────────────────┘
           |
           | (Celery task)
           ↓
   ┌─────────────────────┐
   | deploy_task()       | ← Асинхронная задача деплоя
   └─────────────────────┘
           |
           | (вызов скриптов)
           ↓
   ┌─────────────────────┐
   | Project Updated +   |
   | Services Restarted  |
   └─────────────────────┘
```

## Управление вручную

### Запустить деплой вручную:

```bash
cd /var/www/allitrader
source .venv/bin/activate
python scripts/deploy_script.py
```

### Перезапустить сервисы:

```bash
supervisorctl restart allitrader:*
```

### Посмотреть логи:

```bash
tail -f /var/www/allitrader/deploy.log
```

### Проверить статус сервисов:

```bash
supervisorctl status
```

## Настройка сервера

### 1. Установка зависимостей:

```bash
sudo apt-get update
sudo apt-get install supervisor git python3-venv
```

### 2. Создание структуры директорий:

```bash
sudo mkdir -p /var/www/allitrader
sudo mkdir -p /var/www/allitrader/logs
sudo chown -R $USER:$USER /var/www/allitrader
```

### 3. Клонирование репозитория:

```bash
cd /var/www/allitrader
git clone <ВАШ_GIT_URL> .
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Настройка supervisor:

```bash
sudo cp scripts/supervisor/*.conf /etc/supervisor/conf.d/
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start allitrader:*
```

### 5. Настройка GitHub Webhook:

1. Перейти в Settings → Webhooks → Add webhook
2. Payload URL: `https://your-server.com/webhooc_deploy/`
3. Content type: `application/json`
4. Secret: `YOUR_WEBHOOK_SECRET_TOKEN`
5. Which events: `Just the push event`

### 6. Генерация webhook secret token:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 7. Добавление WEBHOOK_SECRET_TOKEN в .env файл:

```bash
# Добавить в .env файл:
WEBHOOK_SECRET_TOKEN=<сгенерированный_токен>
```

## Тестирование

### Отправить test push:

```bash
git commit --allow-empty -m "Test commit for webhook"
git push origin master
```

### Проверить логи деплоя:

```bash
tail -f /var/www/allitrader/deploy.log
```

### Проверить статус сервисов:

```bash
supervisorctl status
```

## Troubleshooting

### Webhook не приходит:

- Проверьте настройки webhook в GitHub
- Убедитесь, что сервер доступен извне
- Проверьте firewall
- Используйте ngrok для локального тестирования:

```bash
ngrok http 8000
```

### Деплой не проходит:

- Посмотрите логи в `deploy.log`
- Проверьте права доступа к директориям
- Убедитесь, что все команды доступны (`git`, `supervisorctl`, `pip`)

### Сервисы не запускаются:

- Проверьте статус: `supervisorctl status`
- Посмотрите логи сервисов в `/var/www/allitrader/logs/`
- Проверьте конфиги в `/etc/supervisor/conf.d/`

### Ошибка "WEBHOOK_SECRET_TOKEN not configured":

- Добавьте `WEBHOOK_SECRET_TOKEN` в `.env` файл
- Убедитесь, что переменная загружается в Django settings

## Файлы проекта

### Скрипты:
- `scripts/deploy_script.py` - основной скрипт деплоя
- `scripts/restart_services.sh` - скрипт перезапуска сервисов

### Конфигурации supervisor:
- `scripts/supervisor/allitrader-gunicorn.conf`
- `scripts/supervisor/allitrader-celery.conf`
- `scripts/supervisor/allitrader-celery-beat.conf`

### Django:
- `trader/views/webhook_handler.py` - view для приема webhook
- `trader/tasks.py` - Celery задачи (включая `deploy_task`)

## Безопасность

- ✅ Webhook secret token verification (HMAC SHA256)
- ✅ Логирование всех попыток доступа
- ✅ Проверка ветки (только `master`)
- ✅ CSRF отключен для webhook endpoint (только POST запросы)

## Возможные расширения

1. **Environment-specific deploy**: разные ветки → разные окружения
2. **Rollback**: кнопка отката к предыдущей версии
3. **Blue-Green Deploy**: бесперебойные обновления
4. **Health Check**: проверка работоспособности после деплоя
5. **Telegram Notifications**: уведомления в Telegram о результатах деплоя
