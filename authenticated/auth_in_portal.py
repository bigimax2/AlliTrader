from django.contrib.auth import login
from django.contrib.auth.models import User
from django.db import transaction

from eveonline.models import EveCharacter, EveAlliance, EveCorporation, RoleCharacters
from eveonline.providers import status_character, status_corp, status_alliance, corproles
from eveonline.tasks import check_corp_roles
from .models import OwnershipRecord, UserProfile
from .signals import assign_states_periodically


def authinportal(request, token=None):
    if not token:
        return False

    try:
        character = status_character(token.character_id)
        corporation = status_corp(character.corporation_id)
        alliance = status_alliance(corporation.alliance_id) if corporation.alliance_id else None

        # Пытаемся найти персонажа в системе
        try:
            character_in_portal = EveCharacter.objects.get(character_id=character.character_id)
            owner = OwnershipRecord.objects.filter(character_id=character_in_portal.character_id).first()
            if not owner:
                # Это ошибка — нет владельца, но персонаж есть
                # Нужно решить, что делать
                return False
            user = User.objects.get(username=owner.user.username)
            check_corp_roles.delay(character.character_id)
            login(request, user)
            return True

        except EveCharacter.DoesNotExist:
            # Новый персонаж — создаём всё
            with transaction.atomic():
                if alliance:
                    create_alliance(alliance)
                create_corporation(corporation)

                if request.user.is_authenticated:
                    user_in_portal = request.user
                else:
                    user_in_portal = create_user(token.character_name)

                token.user_id = user_in_portal.id
                token.save()

                personage_in_portal = create_personage(character, user_in_portal)

                if not UserProfile.objects.filter(user_id=user_in_portal.id).exists():
                    create_main_personage(user_in_portal, personage_in_portal)

                check_corp_roles.delay(character.character_id)

                if request.user.is_anonymous:
                    login(request, user_in_portal)

            return True

    except Exception as e:
        import logging
        logging.getLogger("auth").error(f"Auth failed: {e}", exc_info=True)
        return False

def create_user(user_name):
    user_cleaned = user_name.replace(' ', '_').replace('`', '')
    user = User.objects.create_user(username=user_cleaned)
    user.set_unusable_password()
    user.save()
    return user

def create_personage(personage, user_in_portal):

    default = {
        'character_id': personage.character_id,
        'name': personage.name,
        'corp_id':personage.corporation_id,
        'birthday': personage.birthday,
        'alliance_id': personage.alliance_id,
    }
    character, status = EveCharacter.objects.update_or_create(
        character_id=personage.character_id,
        defaults=default
    )
    owner_record, created = OwnershipRecord.objects.get_or_create(
        character_id=personage.character_id,defaults={'user_id': user_in_portal.id}
    )

    return character

def create_alliance(alliance):
    default = {
        'alliance_id': alliance.alliance_id,
        'creator_corporation_id': alliance.creator_corporation_id,
        'creator_id': alliance.creator_id,
        'date_founded': alliance.date_founded,
        'executor_corporation_id': alliance.executor_corporation_id,
        'name': alliance.name,
        'ticker': alliance.ticker,
    }
    alliance_in_portal, status = EveAlliance.objects.update_or_create(alliance_id=alliance.alliance_id, defaults=default)
    return alliance_in_portal

def create_corporation(corporation):
    default = {
        'corporation_id': corporation.corporation_id,
        'name': corporation.name,
        'alliance_id': corporation.alliance_id,
        'ceo_id': corporation.ceo_id,
        'creator_id': corporation.creator_id,
        'date_founded': corporation.date_founded,
        'description': corporation.description,
        'home_station_id': corporation.home_station_id,
        'member_count': corporation.member_count,
        'tax_rate': corporation.tax_rate,
        'url': corporation.url,

        'ticker': corporation.ticker,
    }
    corporation_in_portal, status = EveCorporation.objects.update_or_create(corporation_id=corporation.corporation_id, defaults=default)
    return corporation_in_portal


def create_main_personage(user, personage):
    try:
        profile = UserProfile.objects.get(user_id=user.id)
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user_id=user.id)
        profile.main_character_id = personage.character_id
        profile.save()
        assign_states_periodically(user.id)

        return profile
