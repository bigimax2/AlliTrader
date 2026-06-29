#!/usr/bin/env python3
"""
Auto-Deploy Script для AlliTrader
Скрипт автоматического обновления проекта при пуше в GitHub
"""

import os
import sys
import subprocess
import logging
from datetime import datetime
from pathlib import Path

# Настройка логирования
BASE_DIR = Path(__file__).resolve().parent.parent
LOG_FILE = BASE_DIR / 'deploy.log'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Конфигурация
PROJECT_PATH = Path('/var/www/allitrader')
VIRTUALENV_PATH = PROJECT_PATH / '.venv'
MANAGE_PY = PROJECT_PATH / 'manage.py'
REQUIREMENTS_FILE = PROJECT_PATH / 'requirements.txt'
BRANCH = 'master'


def run_command(cmd, cwd=None):
    """Выполнение команды оболочки"""
    logger.info(f"Running: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd or PROJECT_PATH,
            capture_output=True,
            text=True,
            check=True
        )
        logger.info(result.stdout)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {e.stderr}")
        return False


def deploy():
    """Основная функция деплоя"""
    logger.info("="*60)
    logger.info("Starting deployment...")
    logger.info(f"Branch: {BRANCH}")
    logger.info(f"Project path: {PROJECT_PATH}")
    logger.info("="*60)
    
    # 1. Проверка переменных окружения
    os.environ.setdefault('PROJECT_NAME', 'Main')
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Main.settings')
    
    # 2. git pull
    logger.info("Step 1/5: Updating code from repository...")
    if not run_command(['git', 'pull', 'origin', BRANCH]):
        logger.error("Failed to update code")
        return False
    
    # 3. Установка зависимостей
    logger.info("Step 2/5: Installing dependencies...")
    pip_bin = VIRTUALENV_PATH / 'bin' / 'pip'
    if not run_command([str(pip_bin), 'install', '-r', str(REQUIREMENTS_FILE)]):
        logger.warning("Failed to install dependencies, continuing...")
    
    # 4. Применение миграций
    logger.info("Step 3/5: Running migrations...")
    python_bin = VIRTUALENV_PATH / 'bin' / 'python'
    if not run_command([str(python_bin), str(MANAGE_PY), 'migrate', '--noinput']):
        logger.warning("Failed to run migrations, continuing...")
    
    # 5. Сборка статики
    logger.info("Step 4/5: Collecting static files...")
    if not run_command([str(python_bin), str(MANAGE_PY), 'collectstatic', '--noinput']):
        logger.warning("Failed to collect static files, continuing...")
    
    # 6. Перезапуск сервисов
    logger.info("Step 5/5: Restarting services...")
    if not run_command(['supervisorctl', 'restart', 'allitrader:*']):
        logger.error("Failed to restart services")
        return False
    
    logger.info("="*60)
    logger.info("Deployment completed successfully!")
    logger.info("="*60)
    return True


if __name__ == '__main__':
    success = deploy()
    sys.exit(0 if success else 1)
