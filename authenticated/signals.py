from django.contrib.auth.models import User as Us, User
from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from .models import State
from .tasks import assign_states_task



def assign_states_periodically(profile_in=None):
    """
    Периодически назначает статус (State) профилям пользователей
    на основе принадлежности их основного персонажа к корпорации или альянсу.
    Если не найдено совпадений — назначается статус 'Guest'.

    :param profile_in: Опционально. ID пользователя, для которого нужно обновить статус.
                       Если не указан — обновляются все пользователи с профилями и персонажами.
    """

    # Получаем всех пользователей, у которых есть профиль (userprofile)
    # и основной персонаж (main_character), при этом используем select_related
    # для оптимизации запросов к связанным объектам (профиль и персонаж)
    users_with_profiles = Us.objects.filter(
        userprofile__isnull=False,  # У пользователя есть профиль
        userprofile__main_character__isnull=False  # Профиль имеет основного персонажа
    ).select_related('userprofile', 'userprofile__main_character')

    # Если передан конкретный профиль (по ID), фильтруем только по нему
    if profile_in is not None:
        users_with_profiles = Us.objects.filter(id=profile_in)

    # Получаем статус 'Guest' — он будет использован по умолчанию,
    # если не удастся найти подходящий статус по персонажу, корпорации или альянсу
    guest_state = State.objects.get(name='Guest')

    # Перебираем всех подходящих пользователей
    for user in users_with_profiles:
        profile = user.userprofile        # Получаем профиль пользователя
        main_char = profile.main_character  # Получаем основного персонажа (EveCharacter)
        main_corp = main_char.corp        # Получаем корпорацию персонажа (EveCorporation)
        main_alliance = main_corp.alliance  # Получаем альянс корпорации (EveAlliance), если есть

        # Шаг 1: Ищем статус, в котором данный персонаж указан как член
        state = State.objects.filter(member_characters=main_char).first()

        if not state:
            # Шаг 2: Если по персонажу не нашли — ищем статус по корпорации
            state = State.objects.filter(member_corporations=main_corp).first()

        if not state and main_alliance:
            # Шаг 3: Если корпорация в альянсе — ищем статус по альянсу
            state = State.objects.filter(member_alliance=main_alliance).first()

        if not state:
            # Шаг 4: Если ничего не нашли — назначаем статус 'Guest'
            state = guest_state

        # Назначаем найденный (или гостевой) статус профилю и сохраняем
        profile.state = state
        profile.save()


@receiver(m2m_changed, sender=State.member_alliance.through)
def on_state_permissions_change_alliance(sender, instance, action, **kwargs):
    if action.startswith('post_'):
        print(f"Изменены разрешения у состояния '{instance.name}'. Перепроверка пользователей.")
        assign_states_task.delay()

@receiver(m2m_changed, sender=State.member_corporations.through)
def on_state_permissions_change_corporation(sender, instance, action, **kwargs):
    if action.startswith('post_'):
        print(f"Изменены разрешения у состояния '{instance.name}'. Перепроверка пользователей.")
        assign_states_task.delay()

@receiver(m2m_changed, sender=State.member_characters.through)
def on_state_permissions_change_characters(sender, instance, action, **kwargs):
    if action.startswith('post_'):
        print(f"Изменены разрешения у состояния '{instance.name}'. Перепроверка пользователей.")
        assign_states_task.delay()

