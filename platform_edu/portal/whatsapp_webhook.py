from __future__ import annotations

import json
import logging

from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .whatsapp_inbound import ingest_whatsapp_webhook_payload, verify_meta_signature

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(['GET', 'POST'])
def donna_whatsapp_webhook(request):
    if request.method == 'GET':
        return _verify_subscription(request)

    return _handle_notification(request)


def _verify_subscription(request):
    verify_token = settings.WHATSAPP_DONNA_VERIFY_TOKEN
    mode = request.GET.get('hub.mode')
    token = request.GET.get('hub.verify_token')
    challenge = request.GET.get('hub.challenge')

    if mode == 'subscribe' and verify_token and token == verify_token and challenge:
        logger.info('WhatsApp Donna webhook verified')
        return HttpResponse(challenge, content_type='text/plain')

    logger.warning('WhatsApp Donna webhook verification failed')
    return HttpResponseForbidden('Verification failed')


def _handle_notification(request):
    app_secret = settings.WHATSAPP_DONNA_APP_SECRET
    signature = request.headers.get('X-Hub-Signature-256')
    logger.info(
        'WhatsApp Donna webhook POST bytes=%s has_signature=%s',
        len(request.body),
        bool(signature),
    )

    if app_secret:
        if not verify_meta_signature(app_secret, request.body, signature):
            logger.warning('WhatsApp Donna webhook signature invalid')
            return HttpResponseForbidden('Invalid signature')
    elif not settings.DEBUG:
        logger.error('WHATSAPP_DONNA_APP_SECRET is required in production')
        return HttpResponseForbidden('Webhook not configured')

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return HttpResponseBadRequest('Invalid JSON')

    try:
        count = ingest_whatsapp_webhook_payload(payload)
        if count:
            logger.info('WhatsApp Donna webhook stored %s update(s)', count)
    except Exception:
        logger.exception('WhatsApp Donna webhook processing failed')
        return HttpResponse('Processing failed', status=500, content_type='text/plain')

    return HttpResponse('EVENT_RECEIVED', content_type='text/plain')
