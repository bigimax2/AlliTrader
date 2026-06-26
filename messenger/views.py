import logging
import requests
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt

from messenger.models import MemberMessenger, MessengerServer

# Настройка логгера
logger = logging.getLogger(__name__)

@login_required
def render_messenger_template(request):
    messenger_user = MemberMessenger.objects.filter(user=request.user).first()


    # Ищем разрешённые серверы через ServerAccessGroup с учётом group=None и state=None
    accessible_servers = MessengerServer.objects.accessible_by_user(request.user)

    # Проверяем, есть ли доступ
    invite_access = bool(accessible_servers and messenger_user)

    '''
    return render(request, 'messenger_service.html', {
        'messenger_user': messenger_user,'invite_access': invite_access,
    })
    '''
    return render(request, 'plug.html')

@login_required
@csrf_exempt
def registration_user_messenger(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Метод не поддерживается'}, status=405)

    display_name = request.user.username
    is_superuser_flag = request.user.is_superuser

    logger.info(f"Попытка регистрации пользователя в мессенджере: {display_name} (суперпользователь: {is_superuser_flag})")

    try:
        response = requests.post(
            'http://127.0.0.1:8000/api/create-user/',
            json={'username': display_name, 'is_superuser_flag': is_superuser_flag},
            timeout=10
        )
        response.raise_for_status()

        if response.status_code == 201:
            data = response.json()
            logger.info(f"Пользователь успешно создан в мессенджере: ID={data['user']['id']}")

            messenger_user, created = MemberMessenger.objects.update_or_create(
                user=request.user,
                defaults={
                    'refresh_token': data['refresh'],
                    'access_token': data['access'],
                    'token': data['api_token']['token'],
                    'messenger_user': data['user']['username'],
                    'messenger_user_id': data['user']['id'],
                }
            )

            logger.info(f"Данные пользователя сохранены в БД: {messenger_user}, created={created}")

            messages.success(request, 'Пользователь успешно зарегистрирован в мессенджере')
        else:
            logger.warning(f"Ошибка при регистрации на стороне мессенджера: статус {response.status_code}")
            messages.error(request, 'Ошибка при регистрации на стороне мессенджера')

    except requests.exceptions.RequestException as e:
        logger.error(f"Не удалось подключиться к серверу мессенджера: {str(e)}")
        messages.error(request, 'Не удалось подключиться к серверу мессенджера')

    except Exception as e:
        logger.critical(f"Внутренняя ошибка сервера при регистрации пользователя: {str(e)}", exc_info=True)
        messages.error(request, 'Внутренняя ошибка сервера')

    # Перенаправляем обратно на ту же страницу
    return redirect('messenger:render_messenger_template')  # Убедитесь, что имя URL правильное


@login_required
@csrf_exempt
def create_server_messenger(request):
    if request.method != 'POST':
        logger.warning("Неподдерживаемый метод запроса к create_server_messenger")
        messages.error(request, "Метод не поддерживается")
        return redirect('messenger:render_messenger_template')

    # Проверка прав и существования пользователя
    if not request.user.is_superuser:
        logger.warning(f"Попытка создания сервера без прав суперпользователя: пользователь {request.user}")
        messages.error(request, "Доступ запрещён: требуется права суперпользователя")
        return redirect('messenger:render_messenger_template')

    messenger_user = MemberMessenger.objects.filter(user=request.user).first()
    if not messenger_user:
        logger.warning(f"Пользователь не зарегистрирован в мессенджере: {request.user}")
        messages.error(request, "Пользователь не зарегистрирован в мессенджере")
        return redirect('messenger:render_messenger_template')

    access_token = messenger_user.access_token
    messenger_user_id = messenger_user.messenger_user_id

    logger.info(f"Инициализация создания сервера для пользователя мессенджера: {messenger_user_id}")

    def send_create_request(token):
        headers = {"Authorization": f"Bearer {token}", 'Content-Type': 'application/json'}
        data = {'messenger_user_id': messenger_user_id}
        logger.debug(f"Отправка запроса на создание сервера с токеном: {token[:10]}...")
        return requests.post(
            'http://127.0.0.1:8000/api/create-server/',
            headers=headers,
            json=data,
            timeout=10
        )

    try:
        response = send_create_request(access_token)

        if response.status_code == 401:  # Токен истёк
            logger.warning(f"Токен доступа истёк для пользователя {messenger_user_id}. Попытка обновления.")
            try:
                new_access_token = refresh_token(messenger_user_id, messenger_user.refresh_token)
                response = send_create_request(new_access_token)
            except Exception as e:
                logger.error(f"Не удалось обновить токен доступа: {str(e)}")
                messages.error(request, "Не удалось обновить токен доступа")
                return redirect('messenger:render_messenger_template')

        try:
            json_data = response.json()
        except Exception:
            logger.error(f"Некорректный JSON-ответ от сервера: {response.text}")
            messages.error(request, "Ошибка: некорректный ответ от сервера")
            return redirect('messenger:render_messenger_template')

        if response.status_code == 201:
            redirect_url = json_data.get('invite_link')
            server = json_data.get('server')

            if redirect_url and server:
                # Сохраняем сервер в БД
                default = {
                    'name': server['name'],
                    'created_at': server['created_at'],
                    'invite_link': redirect_url,
                    'invite_token': json_data.get('invite_token'),
                    'owner': request.user,
                }
                server_obj, created = MessengerServer.objects.update_or_create(
                    server_id=server['id'], defaults=default
                )
                logger.info(f"Сервер сохранён в БД: {server_obj}, created={created}")

                # Обновляем link_url у пользователя
                messenger_user.link_url = redirect_url
                messenger_user.save(update_fields=['link_url'])
                logger.info(f"Обновлён link_url для пользователя {messenger_user_id}")

                messages.success(request, f"Сервер '{server['name']}' успешно создан!")
            else:
                logger.warning("Ответ содержит статус 201, но отсутствуют данные сервера")
                messages.warning(request, "Сервер создан, но данные неполные")
        else:
            # Обработка ошибок от API
            error_msg = json_data.get('error', json_data.get('detail', 'Неизвестная ошибка'))
            logger.warning(f"Ошибка при создании сервера: {error_msg}")
            messages.error(request, f"Ошибка при создании сервера: {error_msg}")

    except requests.exceptions.Timeout:
        logger.error("Таймаут при подключении к серверу мессенджера")
        messages.error(request, "Таймаут при подключении к серверу мессенджера")

    except requests.exceptions.ConnectionError:
        logger.error("Нет соединения с сервером мессенджера")
        messages.error(request, "Нет соединения с сервером мессенджера")

    except Exception as e:
        logger.critical(f"Внутренняя ошибка при создании сервера: {str(e)}", exc_info=True)
        messages.error(request, "Внутренняя ошибка сервера")

    return redirect('messenger:render_messenger_template')


def refresh_token(messenger_user_id, old_refresh_token):
    """
    Обновляет access_token через refresh токен.
    Возвращает новый access_token.
    """
    logger.info(f"Запрос на обновление access_token для пользователя {messenger_user_id}")
    try:
        response = requests.post(
            'http://127.0.0.1:8000/api/token/refresh/',
            json={'refresh': old_refresh_token},
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        response.raise_for_status()
        tokens = response.json()

        # Обновляем access_token в базе данных
        messenger_user = MemberMessenger.objects.filter(messenger_user_id=messenger_user_id).first()
        if messenger_user:
            messenger_user.access_token = tokens['access']
            messenger_user.save(update_fields=['access_token'])
            logger.info(f"Access token успешно обновлён и сохранён в БД для пользователя {messenger_user_id}")
        else:
            logger.warning(f"Пользователь с messenger_user_id={messenger_user_id} не найден при обновлении токена")

        return tokens['access']

    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка сети при обновлении токена: {str(e)}")
        raise Exception(f"Ошибка при обновлении токена: {str(e)}")
    except KeyError:
        logger.error("Ответ сервера не содержит нового access токена")
        raise Exception("Ответ сервера не содержит нового access токена")

@login_required
@csrf_exempt
def connection_to_messenger(request):
    if request.method != 'POST':
        logger.warning("Неподдерживаемый метод запроса к connection_to_messenger")
        messages.error(request, "Метод не поддерживается")
        return redirect('messenger:render_messenger_template')

    # Получаем пользователя в мессенджере
    messenger_user = MemberMessenger.objects.filter(user=request.user).first()
    if not messenger_user:
        logger.warning(f"Пользователь не зарегистрирован в мессенджере: {request.user}")
        messages.error(request, "Пользователь не зарегистрирован в мессенджере")
        return redirect('messenger:render_messenger_template')


    # Ищем разрешённые серверы через ServerAccessGroup с учётом group=None и state=None
    accessible_servers = MessengerServer.objects.accessible_by_user(request.user)

    # Если нет доступных серверов
    if not accessible_servers.exists():
        logger.warning(f"Доступ к серверам запрещён по группе или состоянию: {request.user}")
        messages.error(request, "У вас нет доступа к какому-либо мессенджеру")
        return redirect('messenger:render_messenger_template')

    # Выбираем первый доступный сервер (или можно передать выбор в интерфейс)
    server = accessible_servers.first()  # Или реализовать выбор через POST

    # Логируем успешный доступ
    logger.info(f"Пользователь {request.user} подключился к серверу {server.name}")

    # Формируем ссылку для подключения
    invite_access = f"{server.invite_link}?access={messenger_user.access_token}&refresh={messenger_user.refresh_token}"

    return HttpResponseRedirect(invite_access)