import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Main.settings')
import django
django.setup()

from traders.models import TypeSearchResult
print('Total items:', TypeSearchResult.objects.count())
items = TypeSearchResult.objects.all()[:5]
for i in items:
    print(f'{i.type_id}: {i.type_name}')
