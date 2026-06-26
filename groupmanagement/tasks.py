from core.app_task import app_task
from .models import NiceGroup
from authenticated.models import UserProfile
from eveonline.models import EveCharacter, EveCorporation, EveAlliance
import logging

logger = logging.getLogger(__name__)


@app_task
def check_nicegroup_user_states():
    """
    Периодически проверяет пользователей в группах NiceGroup.
    Если у пользователя нет state, который разрешает доступ через его персонажа, корп или альянс —
    удаляет его из связанной основной группы (Group).
    """
    for nice_group in NiceGroup.objects.prefetch_related(
        'group__user_set__userprofile__main_character'
    ).all():

        for user in nice_group.users.all():
            try:
                profile = user.userprofile
                state = profile.state
                char = profile.main_character

                if not char:
                    # Нет персонажа — нет права быть в группе
                    nice_group.remove_user(user)
                    logger.info(f"Удалён: нет персонажа — {user.username}")
                    continue

                # Проверяем, разрешён ли доступ через state
                if not _has_state_access(state, char):
                    nice_group.remove_user(user)
                    logger.info(f"Удалён: нет доступа по state — {user.username}")

            except UserProfile.DoesNotExist:
                nice_group.remove_user(user)
                logger.info(f"Удалён: нет профиля — {user.username}")
            except Exception as e:
                logger.error(f"Ошибка при проверке пользователя {user.username}: {e}")


def _has_state_access(state, character: EveCharacter) -> bool:
    """
    Проверяет, имеет ли персонаж доступ к состоянию через:
    - прямое включение в member_characters
    - корпорацию
    - альянс
    """
    # 1. Прямое включение персонажа
    if character in state.member_characters.all():
        return True

    # 2. Корпорация
    corp_id = getattr(character.corp, 'corporation_id', None)
    if corp_id and EveCorporation.objects.filter(
        corporation_id=corp_id,
        corporation_id__in=state.member_corporations.values_list('corporation_id', flat=True)
    ).exists():
        return True

    # 3. Альянс (если есть)
    alliance_id = getattr(character.corp.alliance, 'alliance_id', None) if character.corp.alliance else None
    if alliance_id and EveAlliance.objects.filter(
        alliance_id=alliance_id,
        alliance_id__in=state.member_alliance.values_list('alliance_id', flat=True)
    ).exists():
        return True

    return False
