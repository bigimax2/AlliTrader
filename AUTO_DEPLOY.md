# AlliTrader - Auto-Deploy Setup Guide

## Quick Start

Этот проект теперь поддерживает автоматическое обновление через GitHub Webhooks.

### Что нужно сделать для начала работы:

1. **Сгенерируйте необходимые токены:**
```bash
python scripts/generate_webhook_token.py
python scripts/generate_secret_key.py
```

2. **Создайте файл `.env` на основе `.env.example`:**
```bash
cp .env.example .env
# Отредактируйте .env с вашими реальными значениями
```

3. **Настройте GitHub Webhook:**
   - Settings → Webhooks → Add webhook
   - Payload URL: `https://your-server.com/webhook/deploy/`
   - Secret: `<сгенерированный webhook token>`
   - Which events: `Just the push event`

4. **На сервере:**
```bash
# Установите зависимости
sudo apt-get install supervisor git python3-venv

# Создайте структуру
sudo mkdir -p /var/www/allitrader/logs
sudo chown -R $USER:$USER /var/www/allitrader

# Склонируйте репозиторий
cd /var/www/allitrader
git clone <YOUR_GIT_URL> .
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Настройте supervisor
sudo cp scripts/supervisor/*.conf /etc/supervisor/conf.d/
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start allitrader:*
```

---

## How It Works

```
GitHub Push → Webhook → Django View → Celery Task → Deploy → Restart Services
```

1. Вы делаете `git push origin master`
2. GitHub отправляет POST запрос на `/webhook/deploy/`
3. Django view проверяет подпись (HMAC) и ветку
4. Запускается Celery task `deploy_task()`
5. Скрипт обновляет код, устанавливает зависимости, применяет миграции
6. Сервисы перезапускаются через supervisor
7. Все действия логируются в `deploy.log`

---

## Тестирование

### Отправить test commit:
```bash
git commit --allow-empty -m "Test auto-deploy"
git push origin master
```

### Посмотреть логи:
```bash
tail -f /var/www/allitrader/deploy.log
```

### Проверить статус сервисов:
```bash
supervisorctl status allitrader:*
```

---

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

---

## Документация

- [AUTO_DEPLOY_README.md](AUTO_DEPLOY_README.md) - Полная документация по auto-deploy
- [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) - Резюме реализации
- [scripts/README.md](scripts/README.md) - Документация по скриптам

---

## Безопасность

✅ Webhook подпись проверяется через HMAC SHA256
✅ Только ветка `master` может запустить деплой
✅ Все попытки доступа логируются

---

## Проблемы? Смотри:

1. `/var/www/allitrader/deploy.log` - логи деплоя
2. `/var/www/allitrader/logs/` - логи сервисов (gunicorn, celery)
3. [AUTO_DEPLOY_README.md#troubleshooting](AUTO_DEPLOY_README.md#troubleshooting)

---

## Next Push

После настройки всё готово! Просто сделайте `git push` и проект обновится автоматически. 🚀
