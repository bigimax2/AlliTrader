import os

from bravado.exception import HTTPNotFound, HTTPUnprocessableEntity
from django.apps.registry import apps
try:
    from esi.exceptions import HTTPNotModified
except (ImportError, ModuleNotFoundError):
    HTTPNotModified = None
from esi.models import Token

app_config = apps.get_app_config('eveonline')
if hasattr(app_config, 'esi'):
    esi = app_config.esi
else:
    raise AttributeError("Модуль 'eveonline' не имеет атрибута 'esi'")


# for the love of Bob please add operations you use here. I'm tired of breaking undocumented things.
ESI_OPERATIONS=[
    'get_alliances_alliance_id',
    'get_alliances_alliance_id_corporations',
    'get_corporations_corporation_id',
    'get_characters_character_id',
    'post_characters_affiliation',
    'get_universe_types_type_id',
    'get_universe_factions',
    'post_universe_names',
]


class ObjectNotFound(Exception):
    def __init__(self, obj_id, type_name):
        self.id = obj_id
        self.type = type_name

    def __str__(self):
        return f'{self.type} with ID {self.id} not found.'



class Alliance:
    def __init__(self, alliance_id, **kwargs):
        self.alliance_id = alliance_id
        for key, value in kwargs.items():
            setattr(self, key, value)

class Corporation:
    def __init__(self, corporation_id, **kwargs):
        self.corporation_id = corporation_id
        for key, value in kwargs.items():
            setattr(self, key, value)

class Character:
    def __init__(self, character_id=None, **kwargs):
        self.character_id = character_id
        # Добавляем дополнительные поля из kwargs
        for key, value in kwargs.items():
            setattr(self, key, value)

class CorpRolesPersonage:
    def __init__(self, character_id, **kwargs):
        self.character_id = character_id
        for key, value in kwargs.items():
            setattr(self, key, value)

def corproles(character_id: int):
    required_scopes = ['esi-characters.read_corporation_roles.v1']
    token = Token.get_token(character_id, required_scopes)
    try:
        roles = esi.client.Character.GetCharactersCharacterIdRoles(character_id=character_id, token=token.valid_access_token()).results(force_refresh=True)
        if len(roles['roles']) != 0:
            if 'Director' in roles['roles']:
                model = CorpRolesPersonage(
                    character_id=character_id,
                    director=True,
                )
                return model
    except (HTTPNotFound, HTTPUnprocessableEntity, ObjectNotFound):
        raise ObjectNotFound(character_id, 'character')


def status_character(character_id: int):
    try:
        personage = esi.client.Character.GetCharactersCharacterId(character_id=character_id).results(force_refresh=True)
        pers_get = personage[0]
        model = Character(
            character_id=character_id,
            name=pers_get.name,
            corporation_id=pers_get.corporation_id,
            alliance_id=pers_get.alliance_id if pers_get.alliance_id else None,
            birthday=pers_get.birthday,
        )
        return model
    except (HTTPNotFound, HTTPUnprocessableEntity):
        raise ObjectNotFound(character_id, 'character')



def status_corp(corp_id):
    try:
        corporation = esi.client.Corporation.GetCorporationsCorporationId(corporation_id=corp_id).results(force_refresh=True)
        corp_get = corporation[0]
        model = Corporation(
            corporation_id=corp_id,
            name = corp_get.name,
            member_count = corp_get.member_count,
            alliance_id = corp_get.alliance_id if corp_get.alliance_id else None,
            ceo_id = corp_get.ceo_id,
            creator_id = corp_get.creator_id,
            date_founded = corp_get.date_founded,
            description = corp_get.description,
            home_station_id = corp_get.home_station_id,
            tax_rate = corp_get.tax_rate,
            url = corp_get.url,

            ticker = corp_get.ticker,
        )
        return model
    except (HTTPNotFound, HTTPUnprocessableEntity, ObjectNotFound):
        raise ObjectNotFound(corp_id, 'corporation')

def status_alliance(alliance_id):
    try:
        alliance = esi.client.Alliance.GetAlliancesAllianceId(alliance_id=alliance_id).results(force_refresh=True)
        alli_get = alliance[0]
        model = Alliance(
            alliance_id=alliance_id,
            name = alli_get.name,
            creator_corporation_id = alli_get.creator_corporation_id,
            creator_id = alli_get.creator_id,
            date_founded = alli_get.date_founded,
            executor_corporation_id = alli_get.executor_corporation_id,
            ticker = alli_get.ticker,
        )
        return model
    except (HTTPNotFound, HTTPUnprocessableEntity, ObjectNotFound):
        raise ObjectNotFound(alliance_id, 'alliance')