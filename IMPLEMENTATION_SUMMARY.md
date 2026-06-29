# Auto-Deploy System - Implementation Summary

## What was implemented

### Project Files Created/Modified:

#### 1. Scripts (scripts/)
- ✅ `scripts/deploy_script.py` - Python script for automated deployment
- ✅ `scripts/restart_services.sh` - Bash script for service restart
- ✅ `scripts/supervisor/allitrader-gunicorn.conf` - Supervisor config for Gunicorn
- ✅ `scripts/supervisor/allitrader-celery.conf` - Supervisor config for Celery worker
- ✅ `scripts/supervisor/allitrader-celery-beat.conf` - Supervisor config for Celery beat
- ✅ `scripts/generate_webhook_token.py` - Tool to generate webhook secret token
- ✅ `scripts/generate_secret_key.py` - Tool to generate Django SECRET_KEY

#### 2. Django Application (trader/)
- ✅ `trader/views/webhook_handler.py` - Webhook handler view with HMAC verification
- ✅ `trader/views.py` - Added import for webhook_deploy
- ✅ `trader/tasks.py` - Added `deploy_task()` Celery task
- ✅ `trader/urls.py` - Added `/webhook/deploy/` URL pattern
- ✅ `trader/__init__.py` - Exported webhook_deploy view (WITHOUT full Django import)

#### 3. Configuration Files
- ✅ `Main/settings.py` - Added `WEBHOOK_SECRET_TOKEN` configuration
- ✅ `Main/celery.py` - Created Celery app configuration
- ✅ `AUTO_DEPLOY_README.md` - Complete deployment documentation
- ✅ `.env.example` - Example .env file with all required variables
- ✅ `.gitignore` - Updated to exclude secrets and generated files

---

## How the System Works

```
1. Developer pushes code to GitHub repository
         ↓
2. GitHub sends POST webhook to server: /webhook/deploy/
         ↓
3. Django view (webhook_deploy) receives webhook:
   - Verifies HMAC signature (security)
   - Checks if event is 'push'
   - Checks if branch is 'master'
         ↓
4. If valid, Celery task (deploy_task) is triggered asynchronously
         ↓
5. Deploy task performs:
   - git pull origin master
   - pip install -r requirements.txt
   - python manage.py migrate --noinput
   - python manage.py collectstatic --noinput
   - supervisorctl restart allitrader:*
         ↓
6. All actions logged to /var/www/allitrader/deploy.log
```

---

## Security Features

1. **Webhook Signature Verification** (HMAC SHA256)
   - Only GitHub with correct secret token can trigger deploy
   - Prevents unauthorized deployment requests

2. **Branch Filtering**
   - Only pushes to 'master' branch trigger deploy
   - Prevents accidental deployments from feature branches

3. **CSRF Protection Disabled**
   - Only for webhook endpoint (POST only)
   - Proper security through signature verification

4. **Logging**
   - All webhook attempts logged
   - Failed attempts recorded for security audit

---

## Troubleshooting

### Error: AppRegistryNotReady("Apps aren't loaded yet.")

**Problem**: When importing tasks, Django models are loaded before Django is initialized.

**Solution**: The issue was fixed by removing the Django import from `trader/__init__.py`:

Before:
```python
# trader/__init__.py
from .views.webhook_handler import webhook_deploy
__all__ = ['webhook_deploy']
```

After:
```python
# trader/__init__.py
# Webhook handler imported directly in urls.py, not via __init__.py
# This avoids AppRegistryNotReady errors when importing models
```

And updated `trader/urls.py`:
```python
from trader.views import webhook_deploy  # Direct import instead of via views
path('webhook/deploy/', webhook_deploy, name='webhook_deploy'),
```

**Root Cause**: The import chain was:
`trader/__init__.py` → `trader.views` → `trader.forms` → `trader.models` → `eveonline.models` → Django `apps.get_containing_app_config()` → `AppRegistryNotReady`

This happened because the models were being loaded before Django was fully initialized.

**How to Fix**: Always import views directly in `urls.py` instead of importing them through `__init__.py` when those views depend on Django functionality.

---

## Files Structure

```
AlliTrader/
├── scripts/
│   ├── deploy_script.py                  # Main deployment script
│   ├── restart_services.sh               # Service restart script
│   ├── supervisor/
│   │   ├── allitrader-gunicorn.conf      # Gunicorn config
│   │   ├── allitrader-celery.conf        # Celery worker config
│   │   └── allitrader-celery-beat.conf   # Celery beat config
│   ├── generate_webhook_token.py         # Token generator
│   └── generate_secret_key.py            # SECRET_KEY generator
├── trader/
│   ├── views/
│   │   └── webhook_handler.py            # Webhook endpoint
│   ├── tasks.py                          # Celery tasks
│   ├── urls.py                           # URL patterns
│   └── __init__.py                       # Exports
├── Main/
│   ├── settings.py                       # Added WEBHOOK_SECRET_TOKEN
│   └── celery.py                         # Created Celery app configuration
├── AUTO_DEPLOY_README.md                 # Full documentation
├── .env.example                          # Environment example
├── .gitignore                            # Updated
└── .gigacode/
    └── plans/...                         # This plan
```

---

## Server Setup (After Implementation)

### 1. Install Dependencies
```bash
sudo apt-get update
sudo apt-get install supervisor git python3-venv
```

### 2. Create Directory Structure
```bash
sudo mkdir -p /var/www/allitrader
sudo mkdir -p /var/www/allitrader/logs
sudo chown -R $USER:$USER /var/www/allitrader
```

### 3. Clone Repository
```bash
cd /var/www/allitrader
git clone <YOUR_GIT_URL> .
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Configure Supervisor
```bash
sudo cp scripts/supervisor/*.conf /etc/supervisor/conf.d/
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start allitrader:*
```

### 5. Generate Tokens
```bash
# Generate webhook secret token
python3 scripts/generate_webhook_token.py

# Generate Django SECRET_KEY
python3 scripts/generate_secret_key.py
```

### 6. Setup .env File
```bash
cp .env.example .env
# Edit .env with your values
```

### 7. Configure GitHub Webhook
- Settings → Webhooks → Add webhook
- Payload URL: `https://your-server.com/webhook/deploy/`
- Content type: `application/json`
- Secret: `<generated_webhook_token>`
- Which events: `Just the push event`

---

## Testing

### Manual Test Push
```bash
git commit --allow-empty -m "Test commit for webhook"
git push origin master
```

### Monitor Deployment
```bash
# Watch logs
tail -f /var/www/allitrader/deploy.log

# Check service status
supervisorctl status
```

### Manual Deployment
```bash
cd /var/www/allitrader
source .venv/bin/activate
python scripts/deploy_script.py
```

---

## Key Features

✅ **Automated Deployment** - Push to GitHub, system deploys automatically
✅ **Secure** - HMAC signature verification, branch filtering
✅ **Async** - Deployment runs as Celery task, doesn't block webhook
✅ **Loggable** - All actions logged for debugging
✅ **Rollback Ready** - Easy to implement manual rollback
✅ **Supervisor Managed** - Services automatically restarted

---

## Next Steps (Optional)

1. **Environment-specific deploy** - Different branches → different environments
2. **Rollback button** - Manual rollback to previous version
3. **Health check** - Verify app is working after deploy
4. **Telegram notifications** - Get notified of deploy results
5. **Staging environment** - Test deployments before production

---

## Troubleshooting

### Webhook not received
- Check firewall settings
- Verify GitHub webhook URL is accessible
- Use ngrok for local testing

### Deploy fails
- Check `/var/www/allitrader/deploy.log`
- Verify permissions on `/var/www/allitrader`
- Ensure `git`, `supervisorctl`, `pip` are available

### Error: ModuleNotFoundError("No module named 'Main.celery'")

**Problem**: The `Main/celery.py` file was missing.

**Solution**: Created `Main/celery.py` with Celery app configuration.

**Root Cause**: The `Main/__init__.py` file imports `from .celery import app as celery_app`, but the `celery.py` file didn't exist.

**How to Fix**: 
- Ensure `Main/celery.py` exists (it was created during implementation)
- The file contains the Celery app initialization with autodiscovery

### Error: ImportError("cannot import name 'webhook_deploy' from 'trader.views'")

**Problem**: When importing `webhook_deploy` from `trader.views`, it wasn't available because the view was in a subdirectory.

**Solution**: Added import in `trader/views.py`:
```python
from trader.views.webhook_handler import webhook_deploy
```

And updated `trader/urls.py` to use `views.webhook_deploy`.

**Root Cause**: The `webhook_handler.py` file is in a subdirectory `trader/views/`, not directly in `trader/`.

**How to Fix**: Import the view from the correct location (`trader.views.webhook_handler`) and make it available through `trader.views` module.

### Error: AppRegistryNotReady("Apps aren't loaded yet.")

**Problem**: When importing tasks, Django models are loaded before Django is initialized.

### Services not starting
- Check supervisor logs: `/var/www/allitrader/logs/`
- Verify config files in `/etc/supervisor/conf.d/`
- Check service status: `supervisorctl status`

---

## Commands Reference

```bash
# Restart all services
supervisorctl restart allitrader:*

# Check service status
supervisorctl status allitrader:*

# Tail deploy logs
tail -f /var/www/allitrader/deploy.log

# Run deployment manually
cd /var/www/allitrader
source .venv/bin/activate
python scripts/deploy_script.py

# Generate webhook token
python3 scripts/generate_webhook_token.py
```

---

## Contact & Support

For issues or questions, refer to:
- `AUTO_DEPLOY_README.md` - Complete documentation
- `/var/www/allitrader/deploy.log` - Deployment logs
- `/var/www/allitrader/logs/` - Service logs
