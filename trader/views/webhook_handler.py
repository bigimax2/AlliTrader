import hashlib
import hmac
import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

logger = logging.getLogger(__name__)


def verify_webhook_signature(request):
    """Проверка подписи webhook от GitHub"""
    signature = request.headers.get('X-Hub-Signature-256')
    if not signature:
        logger.warning('Missing X-Hub-Signature-256 header')
        return False
    
    # Получаем secret token из settings или env
    webhook_secret = getattr(settings, 'WEBHOOK_SECRET_TOKEN', None)
    if not webhook_secret:
        logger.error('WEBHOOK_SECRET_TOKEN not configured')
        return False
    
    # Вычисляем HMAC
    sha_name, signature = signature.split('=')
    if sha_name != 'sha256':
        logger.warning(f'Unsupported signature algorithm: {sha_name}')
        return False
    
    body = request.body
    expected_signature = hmac.new(
        webhook_secret.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(signature, expected_signature):
        logger.warning('Invalid webhook signature')
        return False
    
    return True


@csrf_exempt
def webhook_deploy(request):
    """Endpoint для приема GitHub webhooks"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)
    
    # Проверка подписи
    if not verify_webhook_signature(request):
        logger.warning('Webhook verification failed')
        return JsonResponse({'status': 'error', 'message': 'Invalid signature'}, status=401)
    
    # Парсинг payload
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        logger.error('Invalid JSON in webhook payload')
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    
    # Проверка типа события
    event = request.headers.get('X-GitHub-Event', '')
    if event != 'push':
        logger.info(f'Skipping event: {event}')
        return JsonResponse({'status': 'ok', 'message': f'Event {event} not processed'})
    
    # Проверка ветки
    ref = payload.get('ref', '')
    branch = ref.replace('refs/heads/', '')
    if branch != 'master':
        logger.info(f'Skipping push to non-master branch: {branch}')
        return JsonResponse({'status': 'ok', 'message': f'Branch {branch} not processed'})
    
    # Запуск асинхронной задачи деплоя
    try:
        from trader.tasks import deploy_task
        deploy_task.delay()
        logger.info(f'Deploy task started for branch {branch}')
        return JsonResponse({'status': 'ok', 'message': 'Deploy started'})
    except Exception as e:
        logger.exception(f'Failed to start deploy task: {e}')
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
