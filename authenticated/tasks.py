from core.app_task import app_task

from authenticated.models import UserProfile
from django.contrib.auth.models import User
from authenticated.models import State


@app_task()
def assign_states_task(profile_id=None):
    """
    Асинхронная задача для назначения статусов пользователям.
    Выполняет ту же логику, что и assign_states_periodically(),
    но может выполняться в фоновом режиме Celery.
    """
    users_with_profiles = User.objects.filter(
        userprofile__isnull=False,
        userprofile__main_character__isnull=False
    ).select_related('userprofile', 'userprofile__main_character')

    if profile_id is not None:
        users_with_profiles = User.objects.filter(id=profile_id)

    guest_state = State.objects.get(name='Guest')

    for user in users_with_profiles:
        profile = user.userprofile
        main_char = profile.main_character
        main_corp = main_char.corp
        main_alliance = main_corp.alliance

        state = State.objects.filter(member_characters=main_char).first()

        if not state:
            state = State.objects.filter(member_corporations=main_corp).first()

        if not state and main_alliance:
            state = State.objects.filter(member_alliance=main_alliance).first()

        if not state:
            state = guest_state

        profile.state = state
        profile.save()
