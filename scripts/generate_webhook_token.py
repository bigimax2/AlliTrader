#!/usr/bin/env python3
"""
Скрипт для генерации webhook secret token
Используйте этот токен для настройки GitHub Webhook
"""

import secrets
import sys


def generate_webhook_token(length=32):
    """Генерация случайного токена для webhook"""
    return secrets.token_urlsafe(length)


if __name__ == '__main__':
    # Длина токена по умолчанию 32 символа
    length = int(sys.argv[1]) if len(sys.argv) > 1 else 32
    
    token = generate_webhook_token(length)
    print(f"Generated WEBHOOK_SECRET_TOKEN:")
    print(token)
    print(f"\nДлина: {len(token)} символов")
    print("\nДобавьте этот токен в ваш .env файл:")
    print(f"WEBHOOK_SECRET_TOKEN={token}")
