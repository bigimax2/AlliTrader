import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Main.settings')

import django
django.setup()

from traders.tasks import get_prices

# Запуск напрямую - точки остановки будут работать!
result = get_prices()
print(f"Result: {result}")
