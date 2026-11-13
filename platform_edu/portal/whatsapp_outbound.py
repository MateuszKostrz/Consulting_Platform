from __future__ import annotations

import logging
import uuid

import requests
from django.conf import settings
from django.utils import timezone

from .models import WhatsAppDonnaContact, WhatsAppDonnaMessage

logger = logging.getLogger(__name__)


class WhatsAppSendError(Exception):
    pass


def _graph_messages_url() -> str:
    phone_id = (settings.WHATSAPP_DONNA_PHONE_NUMBER_ID or '').strip()
    if not phone_id:
        raise WhatsAppSendError('WHATSAPP_DONNA_PHONE_NUMBER_ID is not configured.')
    version = getattr(settings, 'META_API_VERSION', 'v25.0')
    return f'https://graph.facebook.com/{version}/{phone_id}/messages'


def send_whatsapp_text(*, to_wa_id: str, body: str) -> str:
    """Send a session text message; return Meta wamid."""
    token = (settings.WHATSAPP_DONNA_API or '').strip()
    if not token:
        raise WhatsAppSendError('WHATSAPP_DONNA_API is not configured.')
    if not body.strip():
        raise WhatsAppSendError('Message text is empty.')

    payload = {
        'messaging_product': 'whatsapp',
        'to': str(to_wa_id),
        'type': 'text',
        'text': {'body': body.strip()},
    }
    try:
        response = requests.post(
            _graph_messages_url(),
            json=payload,
            headers={'Authorization': f'Bearer {token}'},
            timeout=30,
        )
    except requests.RequestException as exc:
        logger.exception('WhatsApp send request failed')
        raise WhatsAppSendError('Could not reach Meta API.') from exc

    try:
        data = response.json()
    except ValueError:
        data = {}

    if not response.ok:
        err = data.get('error') or {}
        msg = err.get('message') or response.text or 'Send failed.'
        raise WhatsAppSendError(msg)

    messages = data.get('messages') or []
    wamid = (messages[0] or {}).get('id') if messages else ''
    if not wamid:
        wamid = f'local-{uuid.uuid4().hex}'
    return wamid


def record_outbound_text(contact: WhatsAppDonnaContact, body: str, wamid: str) -> WhatsAppDonnaMessage:
    now = timezone.now()
    msg, _created = WhatsAppDonnaMessage.objects.update_or_create(
        wamid=wamid,
        defaults={
            'contact': contact,
            'direction': WhatsAppDonnaMessage.Direction.OUTBOUND,
            'message_type': 'text',
            'body_text': body.strip(),
            'status': 'accepted',
            'raw_payload': {'source': 'donna_inbox'},
            'wa_timestamp': now,
        },
    )
    contact.last_message_at = now
    contact.save(update_fields=['last_message_at', 'updated_at'])
    return msg


def send_text_to_contact(contact: WhatsAppDonnaContact, body: str) -> WhatsAppDonnaMessage:
    wamid = send_whatsapp_text(to_wa_id=contact.wa_id, body=body)
    return record_outbound_text(contact, body, wamid)


def normalize_whatsapp_recipient(country_code: str, local_number: str) -> str:
    cc = ''.join(ch for ch in (country_code or '') if ch.isdigit())
    local = ''.join(ch for ch in (local_number or '') if ch.isdigit())
    if local.startswith('0'):
        local = local.lstrip('0') or local
    if not cc or not local:
        raise WhatsAppSendError('Enter a valid country code and phone number.')
    if len(cc + local) < 8:
        raise WhatsAppSendError('Phone number looks too short.')
    return cc + local


def _post_whatsapp_payload(payload: dict) -> tuple[str, dict]:
    token = (settings.WHATSAPP_DONNA_API or '').strip()
    if not token:
        raise WhatsAppSendError('WHATSAPP_DONNA_API is not configured.')
    try:
        response = requests.post(
            _graph_messages_url(),
            json=payload,
            headers={'Authorization': f'Bearer {token}'},
            timeout=30,
        )
    except requests.RequestException as exc:
        logger.exception('WhatsApp send request failed')
        raise WhatsAppSendError('Could not reach Meta API.') from exc

    try:
        data = response.json()
    except ValueError:
        data = {}

    if not response.ok:
        err = data.get('error') or {}
        msg = err.get('message') or response.text or 'Send failed.'
        raise WhatsAppSendError(msg)

    messages = data.get('messages') or []
    wamid = (messages[0] or {}).get('id') if messages else ''
    if not wamid:
        wamid = f'local-{uuid.uuid4().hex}'
    return wamid, data


def send_whatsapp_template(*, to_wa_id: str, template_name: str, language_code: str) -> str:
    payload = {
        'messaging_product': 'whatsapp',
        'to': str(to_wa_id),
        'type': 'template',
        'template': {
            'name': template_name,
            'language': {'code': language_code},
        },
    }
    wamid, _data = _post_whatsapp_payload(payload)
    return wamid


def record_outbound_template(
    contact: WhatsAppDonnaContact,
    *,
    template_name: str,
    language_code: str,
    wamid: str,
) -> WhatsAppDonnaMessage:
    now = timezone.now()
    label = f'[Template: {template_name} ({language_code})]'
    msg, _created = WhatsAppDonnaMessage.objects.update_or_create(
        wamid=wamid,
        defaults={
            'contact': contact,
            'direction': WhatsAppDonnaMessage.Direction.OUTBOUND,
            'message_type': 'template',
            'body_text': label,
            'status': 'accepted',
            'raw_payload': {
                'source': 'donna_inbox',
                'template_name': template_name,
                'language_code': language_code,
            },
            'wa_timestamp': now,
        },
    )
    contact.last_message_at = now
    contact.save(update_fields=['last_message_at', 'updated_at'])
    return msg


def send_template_to_recipient(
    *,
    country_code: str,
    local_number: str,
    template_name: str,
    language_code: str,
) -> tuple[WhatsAppDonnaContact, WhatsAppDonnaMessage]:
    wa_id = normalize_whatsapp_recipient(country_code, local_number)
    contact, _created = WhatsAppDonnaContact.objects.get_or_create(wa_id=wa_id)
    wamid = send_whatsapp_template(
        to_wa_id=wa_id,
        template_name=template_name,
        language_code=language_code,
    )
    msg = record_outbound_template(
        contact,
        template_name=template_name,
        language_code=language_code,
        wamid=wamid,
    )
    return contact, msg
