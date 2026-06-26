
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from functools import wraps

from django.shortcuts import redirect
from django.urls import reverse


def app_access_required(app_label):
    """
    Декоратор: проверяет, имеет ли State пользователя доступ к приложению.
    """
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            try:
                state = request.user.userprofile.state
            except:
                return redirect(reverse('authenticated:login'))


            if not state.has_access_to_app(app_label):
                return redirect(reverse('authenticated:login'))

            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator