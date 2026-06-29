# Auto-Deploy Implementation Checklist

## ✅ Файлы созданы

### Scripts (scripts/)
- [x] `scripts/deploy_script.py` (3413 bytes)
- [x] `scripts/restart_services.sh` (387 bytes)
- [x] `scripts/generate_webhook_token.py` (556 bytes)
- [x] `scripts/generate_secret_key.py` (811 bytes)

### Supervisor Configs (scripts/supervisor/)
- [x] `allitrader-gunicorn.conf` (579 bytes)
- [x] `allitrader-celery.conf` (418 bytes)
- [x] `allitrader-celery-beat.conf` (431 bytes)

### Django Application (trader/)
- [x] `trader/views/webhook_handler.py` (2999 bytes)
- [x] `trader/urls.py` (обновлен - добавлен webhook)
- [x] `trader/tasks.py` (обновлен - добавлен deploy_task)
- [x] `trader/__init__.py` (обновлен - экспортирует webhook_deploy)

### Configuration
- [x] `Main/settings.py` (обновлен - добавлен WEBHOOK_SECRET_TOKEN)
- [x] `.gitignore` (обновлен - исключает секреты)

### Documentation
- [x] `AUTO_DEPLOY_README.md` (6104 bytes)
- [x] `AUTO_DEPLOY.md` (3769 bytes)
- [x] `IMPLEMENTATION_SUMMARY.md` (7292 bytes)
- [x] `scripts/README.md` (новый файл)
- [x] `.env.example` (новый файл)

---

## ✅ Код проверен

### Django URLs
```python
# trader/urls.py
path('webhook/deploy/', views.webhook_deploy, name='webhook_deploy'),
```

### Django Settings
```python
# Main/settings.py
import secrets
WEBHOOK_SECRET_TOKEN = os.getenv('WEBHOOK_SECRET_TOKEN', secrets.token_urlsafe(32))
```

### Celery Task
```python
# trader/tasks.py
@app_task()
def deploy_task():
    # git pull, pip install, migrate, collectstatic, supervisorctl restart
```

### Webhook Handler
```python
# trader/views/webhook_handler.py
@csrf_exempt
def webhook_deploy(request):
    # verify signature, check branch, start deploy_task
```

---

## 🚀 Следующие шаги (на сервере)

1. **Установить зависимости:**
```bash
sudo apt-get update
sudo apt-get install supervisor git python3-venv
```

2. **Создать структуру:**
```bash
sudo mkdir -p /var/www/allitrader/logs
sudo chown -R $USER:$USER /var/www/allitrader
```

3. **Склонировать репозиторий:**
```bash
cd /var/www/allitrader
git clone <YOUR_GIT_URL> .
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

4. **Настроить supervisor:**
```bash
sudo cp scripts/supervisor/*.conf /etc/supervisor/conf.d/
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start allitrader:*
```

5. **Сгенерировать токены:**
```bash
# На локальной машине:
python scripts/generate_webhook_token.py
python scripts/generate_secret_key.py

# На сервере:
cp .env.example .env
# Отредактировать .env
```

6. **Настроить GitHub Webhook:**
- Settings → Webhooks → Add webhook
- Payload URL: `https://your-server.com/webhook/deploy/`
- Secret: `<сгенерированный token>`
- Which events: `Just the push event`

---

## ✅ Проверка работоспособности

### Локально (через ngrok):
```bash
ngrok http 8000
# Указать ngrok URL в GitHub webhook
```

### Тестовый push:
```bash
git commit --allow-empty -m "Test auto-deploy"
git push origin master
```

### Проверка на сервере:
```bash
# Логи деплоя
tail -f /var/www/allitrader/deploy.log

# Статус сервисов
supervisorctl status allitrader:*

# Ручной деплой
cd /var/www/allitrader
source .venv/bin/activate
python scripts/deploy_script.py
```

---

## 📝 Troubleshooting

### Проблема: Webhook не приходит
- Проверить firewall
- Убедиться, что сервер доступен извне
- Использовать ngrok для тестирования

### Проблема: Деплой не проходит
- Посмотреть логи: `/var/www/allitrader/deploy.log`
- Проверить права доступа
- Убедиться, что все команды доступны

### Проблема: Сервисы не запускаются
- Проверить статус: `supervisorctl status`
- Посмотреть логи: `/var/www/allitrader/logs/`
- Проверить конфиги: `/etc/supervisor/conf.d/`

---

## 🎉 Готово к работе!

После выполнения всех шагов проект будет обновляться автоматически при каждом `git push origin master`.

### Как это работает:
1. Developer → `git push origin master`
2. GitHub → POST `/webhook/deploy/`
3. Django → verify signature, check branch
4. Celery → start deploy_task()
5. Deploy → git pull, pip install, migrate, collectstatic
6. Restart → supervisorctl restart allitrader:*
7. Done! →Project updated ✅

---

## 📚 Документация

- **Полная документация:** [AUTO_DEPLOY_README.md](AUTO_DEPLOY_README.md)
- **Резюме реализации:** [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
- **Быстрый старт:** [AUTO_DEPLOY.md](AUTO_DEPLOY.md)
- **Скрипты:** [scripts/README.md](scripts/README.md)
