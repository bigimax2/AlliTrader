from django.core.management.base import BaseCommand
from config.celery_schedule import CELERY_BEAT_SCHEDULE


class Command(BaseCommand):
    help = "Показать все зарегистрированные периодические задачи из CELERY_BEAT_SCHEDULE"

    def handle(self, *args, **options):
        if not CELERY_BEAT_SCHEDULE:
            self.stdout.write(self.style.WARNING("CELERY_BEAT_SCHEDULE пуст."))
            return

        self.stdout.write(f"🔍 Найдено {len(CELERY_BEAT_SCHEDULE)} задач:\n")
        for name, task in CELERY_BEAT_SCHEDULE.items():
            self.stdout.write(self.style.SUCCESS(f"🔹 {name}"))
            self.stdout.write(f"   Задача: {task['task']}")
            self.stdout.write(f"   Расписание: {task['schedule']}")
            if 'kwargs' in task:
                self.stdout.write(f"   Параметры: {task['kwargs']}")
            if 'queue' in task:
                self.stdout.write(f"   Очередь: {task['queue']}")
            self.stdout.write("")