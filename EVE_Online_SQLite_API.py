import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def get_type_id(type_id):
    try:
        url_name = f"{settings.SDE_API_URL}/type/simple/{type_id}"
        head = {
            'X-API-KEY': settings.SDE_API_KEY,
            'Content-Type': 'application/json',
        }
        response = requests.get(url_name, headers=head)
        response.raise_for_status()
        data = response.json()
        return data
    except Exception as e:
        logger.error(e)

def get_types_info(type_ids):
    if not type_ids:
        return {}
    try:
        url_name = f"{settings.SDE_API_URL}/types/by-ids"
        head = {
            'X-API-KEY': settings.SDE_API_KEY,
            'Content-Type': 'application/json',
        }

        response = requests.post(url_name, headers=head, json=list(type_ids))
        response.raise_for_status()
        result = response.json()

        # Преобразуем список [{'typeID': x, 'typeName': y}, ...] в словарь {x: {'typeName': y}, ...}
        if isinstance(result, list):
            return {item['typeID']: {'typeName': item['typeName']} for item in result}
        return result if isinstance(result, dict) else {}
    except Exception as e:
        logger.error(f"Ошибка при batch-запросе станций: {e}")
        return {}

def get_station_info(station_id):
    try:
        url_name = f"{settings.SDE_API_URL}/station/{station_id}"
        head = {
            'X-API-KEY': settings.SDE_API_KEY,
            'Content-Type': 'application/json',
        }
        response = requests.get(url_name, headers=head)
        response.raise_for_status()
        data = response.json()
        return data
    except Exception as e:
        logger.error(e)

def get_stations_info(station_ids):
    """
    Получение информации о нескольких станциях за один запрос
    
    Args:
        station_ids: Список ID станций
    
    Returns:
        Словарь {station_id: station_data} или пустой словарь при ошибке
    """
    if not station_ids:
        return {}
    
    try:
        url_name = f"{settings.SDE_API_URL}/stations/by-ids"
        head = {
            'X-API-KEY': settings.SDE_API_KEY,
            'Content-Type': 'application/json',
        }

        response = requests.post(url_name, headers=head, json=list(station_ids))
        response.raise_for_status()
        result = response.json()

        # Преобразуем список [{'stationID': x, 'stationName': y}, ...] в словарь {x: {'stationName': y}, ...}
        if isinstance(result, list):
            return {item['stationID']: {'stationName': item['stationName']} for item in result}
        return result if isinstance(result, dict) else {}
    except Exception as e:
        logger.error(f"Ошибка при batch-запросе станций: {e}")
        return {}


