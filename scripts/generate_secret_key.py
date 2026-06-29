#!/usr/bin/env python3
"""
Скрипт для генерации SECRET_KEY для Django
"""

import secrets


def generate_secret_key():
    """Генерация случайного SECRET_KEY для Django"""
    return secrets.token_urlsafe(50)


if __name__ == '__main__':
    secret_key = generate_secret_key()
    print(f"Generated SECRET_KEY:")
    print(secret_key)
    print(f"\nДлина: {len(secret_key)} символов")
    print("\nДобавьте этот токен в ваш .env файл:")
    print(f"SECRET_KEY={secret_key}")
