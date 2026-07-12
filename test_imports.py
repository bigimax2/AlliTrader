import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Main.settings')
django.setup()

# Проверка импортов
try:
    from observer_assets_all.views import get_all_users_assets, assets_overview
    print("Views import OK")
except Exception as e:
    print(f"Views import error: {e}")

try:
    from observer_assets_all.models import TypeSearchResult
    print("Models import OK")
except Exception as e:
    print(f"Models import error: {e}")

# Проверка шаблона
try:
    with open('observer_assets_all/templates/assets_overview.html', 'r', encoding='utf-8') as f:
        content = f.read()
        print(f"Template file OK, size: {len(content)} bytes")
except Exception as e:
    print(f"Template file error: {e}")
