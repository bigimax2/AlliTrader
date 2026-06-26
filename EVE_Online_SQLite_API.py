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