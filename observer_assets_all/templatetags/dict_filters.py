from django import template

register = template.Library()

@register.filter(name='get_item')
def get_item(dictionary, key):
    """Получает значение из словаря по ключу"""
    return dictionary.get(key)
