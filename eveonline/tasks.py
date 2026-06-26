import requests
from core.app_task import app_task
from esi.models import Token

from django.apps import apps
from datetime import datetime


@app_task(bind=True, max_retries=3)
def check_corp_roles(self, character_id=None):
    from eveonline.models import EveCharacter, RoleCharacters
    """
    Проверяет корпоративные роли для одного или всех персонажей.
    Обновляет RoleCharacters (ceo, director).
    """
    characters = EveCharacter.objects.select_related('corp')
    if character_id:
        characters = characters.filter(character_id=character_id)

    if not characters.exists():
        if character_id:
            log(f"[check_corp_roles] Персонаж {character_id} не найден.")
        return

    esi = apps.get_app_config('eveonline').esi
    required_scopes = ['esi-characters.read_corporation_roles.v1']

    for character in characters:
        try:
            token = Token.get_token(character.character_id, required_scopes)
            if not token:
                log(f"[check_corp_roles] Нет токена с правами read_corporation_roles: {character.character_id}")
                continue

            roles_data, response = esi.client.Character.GetCharactersCharacterIdRoles(
                character_id=character.character_id,
                token=token
            ).result(return_response=True,force_refresh=True)


            # Проверяем наличие роли 'Director' в любой из групп ролей
            # roles_data - это объект с атрибутами (roles_at_base, roles_at_hq, roles_at_other, roles)
            is_director = (
                hasattr(roles_data, 'roles_at_base') and 'Director' in roles_data.roles_at_base or
                hasattr(roles_data, 'roles_at_hq') and 'Director' in roles_data.roles_at_hq or
                hasattr(roles_data, 'roles_at_other') and 'Director' in roles_data.roles_at_other or
                hasattr(roles_data, 'roles') and 'Director' in roles_data.roles  # Для обратной совместимости
            )
            is_ceo = character.corp.ceo_id == character.character_id

            RoleCharacters.objects.update_or_create(
                personage_id=character.character_id,
                defaults={'ceo': is_ceo, 'director': is_director}
            )

            name = character.name if hasattr(character, 'name') else f"ID={character.character_id}"
            log(f"[check_corp_roles] Обновлено: {name} → director={is_director}, ceo={is_ceo}")

        except requests.HTTPError as e:
            status = e.response.status_code
            name = getattr(character, 'name', character.character_id)
            if 400 <= status < 500:
                log(f"[check_corp_roles] Ошибка клиента ESI для {name}: {e}")
            else:
                log(f"[check_corp_roles] Серверная ошибка ESI для {name}, повтор...")
                self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
                return
        except Exception as e:
            name = getattr(character, 'name', character.character_id)
            log(f"[check_corp_roles] Ошибка при обработке {name}: {e}")
            continue



# Логгер (можно заменить на logging, если настроен)
def log(msg):
    print(f"[{datetime.now()}] {msg}")


@app_task
def update_eve_character(character_id: int):
    from eveonline.models import EveCharacter
    """
    Обновляет данные одного персонажа по character_id.
    """
    esi = apps.get_app_config('eveonline').esi
    try:
        log(f"Обновление персонажа: {character_id}")
        char_data = esi.client.Character.GetCharactersCharacterId(
            character_id=character_id
        ).results()

        character, created = EveCharacter.objects.update_or_create(
            character_id=character_id,
            defaults={
                "name": char_data["name"],
                "birthday": char_data.get("birthday"),
                "security_status": char_data.get("security_status"),
                "corporation_id": char_data.get("corporation_id"),
                "alliance_id": char_data.get("alliance_id"),
            }
        )

        log(f"{'Создан' if created else 'Обновлён'} персонаж: {character.name}")
        return {
            "success": True,
            "type": "character",
            "id": character_id,
            "name": character.name,
            "corporation_id": character.corp.corporation_id,
            "alliance_id": character.alliance_id,
        }

    except Exception as e:
        log(f"Ошибка при обновлении персонажа {character_id}: {e}")
        return {
            "success": False,
            "type": "character",
            "id": character_id,
            "error": str(e)
        }


@app_task
def update_eve_corporation(corporation_id: int):
    from eveonline.models import EveCorporation
    """
    Обновляет данные одной корпорации по corporation_id.
    """
    esi = apps.get_app_config('eveonline').esi
    try:
        log(f"Обновление корпорации: {corporation_id}")
        corp_data = esi.client.Corporation.GetCorporationsCorporationId(
            corporation_id=corporation_id
        ).results()

        alliance_id = corp_data.get("alliance_id")

        corporation, created = EveCorporation.objects.update_or_create(
            corporation_id=corporation_id,
            defaults={
                "name": corp_data["name"],
                "ticker": corp_data["ticker"],
                "member_count": corp_data["member_count"],
                "ceo_id": corp_data["ceo_id"],
                "date_founded": corp_data["date_founded"],
                "description": corp_data.get("description"),
                "tax_rate": corp_data.get("tax_rate"),
                "url": corp_data.get("url"),
                "alliance_id": alliance_id,
            }
        )

        log(f"{'Создана' if created else 'Обновлена'} корпорация: {corporation.name}")
        return {
            "success": True,
            "type": "corporation",
            "id": corporation_id,
            "name": corporation.name,
            "alliance_id": alliance_id,
        }

    except Exception as e:
        log(f"Ошибка при обновлении корпорации {corporation_id}: {e}")
        return {
            "success": False,
            "type": "corporation",
            "id": corporation_id,
            "error": str(e)
        }


@app_task
def update_eve_alliance(alliance_id: int):
    from eveonline.models import EveAlliance
    """
    Обновляет данные одного альянса по alliance_id.
    """
    esi = apps.get_app_config('eveonline').esi
    try:
        log(f"Обновление альянса: {alliance_id}")
        alliance_data = esi.client.Alliance.GetAlliancesAllianceId(
            alliance_id=alliance_id
        ).results()

        alliance, created = EveAlliance.objects.update_or_create(
            alliance_id=alliance_id,
            defaults={
                "name": alliance_data["name"],
                "ticker": alliance_data["ticker"],
                "creator_id": alliance_data["creator_id"],
                "creator_corporation_id": alliance_data["creator_corporation_id"],
                "executor_corporation_id": alliance_data["executor_corporation_id"],
                "date_founded": alliance_data["date_founded"],
            }
        )

        log(f"{'Создан' if created else 'Обновлён'} альянс: {alliance.name}")
        return {
            "success": True,
            "type": "alliance",
            "id": alliance_id,
            "name": alliance.name,
        }

    except Exception as e:
        log(f"Ошибка при обновлении альянса {alliance_id}: {e}")
        return {
            "success": False,
            "type": "alliance",
            "id": alliance_id,
            "error": str(e)
        }



@app_task
def update_eve_entities():
    from eveonline.models import EveCharacter, EveCorporation
    print(f"[{datetime.now()}] Запуск Celery задачи: update_eve_entities")

    tokens = Token.objects.filter(scopes__name__contains="publicData").select_related('user')

    updated_chars = 0
    updated_corps = set()
    updated_alliances = set()
    esi = apps.get_app_config('eveonline').esi
    for token in tokens:
        character_id = token.character_id
        try:
            char_data = esi.client.Character.GetCharactersCharacterId(
                character_id=token.character_id
            ).results()

            character, _ = EveCharacter.objects.update_or_create(
                character_id=token.character_id,
                defaults={
                    "name": char_data["name"],
                    "birthday": char_data.get("birthday"),
                    "security_status": char_data.get("security_status"),
                    "corporation_id": char_data.get("corporation_id"),
                    "alliance_id": char_data.get("alliance_id"),
                }
            )
            updated_chars += 1

            corp_id = char_data.get("corporation_id")
            if corp_id and corp_id not in updated_corps:
                corp_data = esi.client.Corporation.GetCorporationsCorporationId(
                    corporation_id=corp_id
                ).results()

                alliance_id = corp_data.get("alliance_id")

                EveCorporation.objects.update_or_create(
                    corporation_id=corp_id,
                    defaults={
                        "name": corp_data["name"],
                        "ticker": corp_data["ticker"],
                        "member_count": corp_data["member_count"],
                        "ceo_id": corp_data["ceo_id"],
                        "date_founded": corp_data["date_founded"],
                        "description": corp_data.get("description"),
                        "tax_rate": corp_data.get("tax_rate"),
                        "url": corp_data.get("url"),
                        "alliance_id": alliance_id,
                    }
                )
                updated_corps.add(corp_id)

                if alliance_id and alliance_id not in updated_alliances:
                    alliance_data = esi.client.Alliance.GetAlliancesAllianceId(
                        alliance_id=alliance_id
                    ).results()
                    from eveonline.models import EveAlliance
                    EveAlliance.objects.update_or_create(
                        alliance_id=alliance_id,
                        defaults={
                            "name": alliance_data["name"],
                            "ticker": alliance_data["ticker"],
                            "creator_id": alliance_data["creator_id"],
                            "creator_corporation_id": alliance_data["creator_corporation_id"],
                            "executor_corporation_id": alliance_data["executor_corporation_id"],
                            "date_founded": alliance_data["date_founded"],
                        }
                    )
                    updated_alliances.add(alliance_id)

        except Exception as e:
            print(f"Ошибка при обновлении {token.character_id}: {e}")
            continue

    print(f"Обновлено: {updated_chars} персонажей, {len(updated_corps)} корпораций, {len(updated_alliances)} альянсов")
