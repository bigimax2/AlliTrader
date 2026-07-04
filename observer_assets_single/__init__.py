"""
Trader app для AlliTrader
"""

# Webhook handler импортируется напрямую в urls.py, а не через __init__.py
# Это избежание проблем с AppRegistryNotReady при импорте моделей
