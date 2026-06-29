# Scripts Directory

This directory contains scripts for auto-deployment and system management.

## Scripts Overview

### Deployment Scripts

| File | Description | Usage |
|------|-------------|-------|
| `deploy_script.py` | Main deployment script - updates code, installs deps, runs migrations | `python scripts/deploy_script.py` |
| `restart_services.sh` | Restart all services via supervisorctl | `bash scripts/restart_services.sh` |

### Utility Scripts

| File | Description | Usage |
|------|-------------|-------|
| `generate_webhook_token.py` | Generate random token for GitHub webhook | `python scripts/generate_webhook_token.py` |
| `generate_secret_key.py` | Generate Django SECRET_KEY | `python scripts/generate_secret_key.py` |

### Supervisor Configurations

| File | Description |
|------|-------------|
| `supervisor/allitrader-gunicorn.conf` | Gunicorn WSGI server config |
| `supervisor/allitrader-celery.conf` | Celery worker config |
| `supervisor/allitrader-celery-beat.conf` | Celery beat (scheduled tasks) config |

---

## Usage

### Generate Required Tokens

```bash
# Generate webhook secret token
python scripts/generate_webhook_token.py

# Generate Django SECRET_KEY
python scripts/generate_secret_key.py
```

### Manual Deployment

```bash
# Deploy the latest code
python scripts/deploy_script.py

# Restart all services
bash scripts/restart_services.sh
```

---

## Configuration

### Environment Variables

Scripts use the following environment variables:

- `PROJECT_NAME` - Name of the Django project (default: "Main")
- `DJANGO_SETTINGS_MODULE` - Django settings module (default: "Main.settings")
- `PROJECT_PATH` - Path to project directory (default: "/var/www/allitrader")
- `VIRTUALENV_PATH` - Path to virtual environment (default: PROJECT_PATH/.venv)

---

## Logs

All deployment actions are logged to:

- `deploy.log` - Main deployment log (in project root)
- `/var/www/allitrader/logs/` - Service-specific logs (gunicorn, celery, etc.)

---

## Security Notes

⚠️ **Never commit tokens or secrets to git!**

The `.gitignore` file excludes:
- `*.secret` files
- `*.key` files
- `.env` files

Use `.env.example` as template and create your own `.env` with actual values.

---

## Related Documentation

- [AUTO_DEPLOY_README.md](../AUTO_DEPLOY_README.md) - Complete auto-deploy documentation
- [IMPLEMENTATION_SUMMARY.md](../IMPLEMENTATION_SUMMARY.md) - Implementation overview
