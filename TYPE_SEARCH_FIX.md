# Инструкция по исправлению ошибки с TypeSearchResult

## Проблема
На сервере возникает ошибка: `1054, "Unknown column 'observer_assets_all_typesearchresult.character_id' in 'SELECT'"`

## Решение

### 1. Применить миграцию
На сервере выполнить команды:
```bash
python manage.py makemigrations observer_assets_all
python manage.py migrate observer_assets_all
```

Или если миграция уже создана:
```bash
python manage.py migrate observer_assets_all
```

### 2. Проверка таблицы
После применения миграции в таблице `observer_assets_all_typesearchresult` должна быть колонка `character_id` (внешний ключ к `eveonline_evecharacter.character_id`).

### 3. Что было исправлено в коде

#### observer_assets_all/views.py:
- ✅ Добавлена обработка отсутствия профиля пользователя (`UserProfile.DoesNotExist`)
- ✅ Добавлена обработка отсутствия персонажа (`EveCharacter.DoesNotExist`) 
- ✅ Добавлен fallback для фильтрации: сначала пытаемся использовать `character__character_id`, если не удалось - используем `character_id`
- ✅ Исправлено присваивание `result_data = {}` вместо `None`

## Миграции

Созданы файлы:
- `observer_assets_all/migrations/0001_initial.py` - создание таблицы TypeSearchResult с полем character
- `observer_assets_all/migrations/__init__.py` - пустой файл для модуля

## Дополнительно

Если на сервере уже есть таблица `observer_assets_all_typesearchresult` без поля `character`, можно:

### Вариант A: Добавить поле вручную (SQL)
```sql
ALTER TABLE observer_assets_all_typesearchresult 
ADD COLUMN character_id BIGINT UNSIGNED NULL;

ALTER TABLE observer_assets_all_typesearchresult 
ADD CONSTRAINT observer_assets_all_typesearchresult_character_id_fk_eveonline_evecharacter 
FOREIGN KEY (character_id) REFERENCES eveonline_evecharacter (character_id) 
ON DELETE CASCADE;
```

### Вариант B: Обновить существующую миграцию
1. Удалить старую миграцию
2. Обновить код views.py (уже сделано)
3. Создать новую миграцию
4. Применить миграцию
