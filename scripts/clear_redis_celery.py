#!/usr/bin/env python
"""
Скрипт для проверки и очистки Redis ключей Celery.
Проверяет наличие ключей Celery и позволяет очистить только ключи своего проекта.
"""

import sys
from pathlib import Path
import redis

# Добавляем корневую директорию в PYTHONPATH
project_root = Path(__file__).resolve().parent.parent
if project_root not in sys.path:
    sys.path.insert(0, str(project_root))

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Main.settings")


def get_redis_client(db=1):
    """Создает клиент Redis для указанной БД."""
    return redis.from_url(f"redis://127.0.0.1:6379/{db}")


def get_celery_key_prefix():
    """Получает префикс ключей Celery из настроек проекта."""
    try:
        from django.conf import settings
        return getattr(settings, 'CELERY_KEY_PREFIX', 'allitrader_celery')
    except Exception:
        return 'allitrader_celery'


def scan_celery_keys(redis_client, prefix, count=100):
    """Ищет все ключи с указанным префиксом."""
    cursor = 0
    keys = []
    
    while True:
        cursor, partial_keys = redis_client.scan(
            cursor=cursor,
            match=f"{prefix}*",
            count=count
        )
        keys.extend(partial_keys)
        
        if cursor == 0:
            break
    
    return keys


def check_redis_keys():
    """Проверяет наличие ключей Celery в Redis."""
    print("=" * 70)
    print("ПРОВЕРКА КЛЮЧЕЙ CELERY В REDIS")
    print("=" * 70)
    
    # Получаем префикс из настроек
    prefix = get_celery_key_prefix()
    print(f"\n📌 Ожидаемый префикс ключей: {prefix}")
    
    # Проверяем разные БД
    databases = [0, 1, 2, 3]
    
    for db_num in databases:
        try:
            client = get_redis_client(db_num)
            key_count = client.dbsize()
            
            print(f"\n--- БД {db_num} (всего ключей: {key_count}) ---")
            
            # Ищем ключи с нашим префиксом
            my_keys = scan_celery_keys(client, prefix)
            
            if my_keys:
                print(f"✅ Найдено {len(my_keys)} ключей с префиксом '{prefix}':")
                for key in my_keys[:10]:  # Показываем первые 10
                    key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                    print(f"   - {key_str}")
                if len(my_keys) > 10:
                    print(f"   ... и ещё {len(my_keys) - 10} ключей")
            else:
                print(f"❌ Ключей с префиксом '{prefix}' не найдено")
            
            # Ищем любые ключи Celery (без префикса или с другими префиксами)
            all_celery_keys = scan_celery_keys(client, "celery")
            if all_celery_keys and not my_keys:
                print(f"⚠️  ВНИМАНИЕ: Найдено {len(all_celery_keys)} ключей 'celery*' (чужие задачи!)")
                for key in all_celery_keys[:5]:
                    key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                    print(f"   - {key_str}")
                    
        except redis.ConnectionError as e:
            print(f"❌ Ошибка подключения к БД {db_num}: {e}")
        except Exception as e:
            print(f"❌ Ошибка при проверке БД {db_num}: {e}")


def clear_celery_keys(db_num=1, dry_run=True):
    """Очищает ключи Celery из указанной БД."""
    prefix = get_celery_key_prefix()
    client = get_redis_client(db_num)
    
    print(f"\n{'[СИМУЛЯЦИЯ]' if dry_run else '[ДЕЙСТВИЕ]'} Очистка БД {db_num}")
    print(f"Prefix: {prefix}")
    
    keys = scan_celery_keys(client, prefix)
    print(f"Найдено ключей: {len(keys)}")
    
    if dry_run:
        print("\nЭто симуляция. Для реальной очистки используйте: python clear_redis_celery.py --real")
        if keys:
            print("\nПримеры ключей, которые будут удалены:")
            for key in keys[:5]:
                key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                print(f"  - {key_str}")
    else:
        if keys:
            client.delete(*keys)
            print(f"✅ Удалено {len(keys)} ключей")
        else:
            print("Нет ключей для удаления")


def main():
    """Основная функция."""
    import argparse
    parser = argparse.ArgumentParser(description='Проверка и очистка ключей Celery из Redis')
    
    parser.add_argument('--check', action='store_true', 
                       help='Проверить наличие ключей Celery во всех БД')
    parser.add_argument('--clear', type=int, metavar='DB', 
                       help='Очистить ключи Celery из указанной БД (по умолчанию: симуляция)')
    parser.add_argument('--real', action='store_true', 
                       help='Выполнить реальную очистку (по умолчанию: симуляция)')
    
    args = parser.parse_args()
    
    if args.check:
        check_redis_keys()
    elif args.clear:
        clear_celery_keys(args.clear, dry_run=not args.real)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
