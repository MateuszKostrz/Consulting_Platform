from __future__ import annotations

import hashlib
import hmac
import logging
from datetime import datetime, timezone as dt_timezone

from django.db import transaction
from django.utils import timezone

from .models import WhatsAppDonnaContact, WhatsAppDonnaMessage

logger = logging.getLogger(__name__)


def verify_meta_signature(app_secret: str, raw_body: bytes, signature_header: str | None) -> bool:
    if not app_secret:
        return False
    if not signature_header or not signature_header.startswith('sha256='):
        return False
    digest = hmac.new(app_secret.encode('utf-8'), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature_header[7:], digest)


def _wa_ts_to_datetime(ts: str | int | None):
    if ts in (None, ''):
        return None
    try:
        return datetime.fromtimestamp(int(ts), tz=dt_timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


def _message_body(msg: dict) -> str:
    msg_type = msg.get('type') or ''
    if msg_type == 'text':
        return (msg.get('text') or {}).get('body') or ''
    if msg_type == 'button':
        return (msg.get('button') or {}).get('text') or ''
    if msg_type == 'interactive':
        interactive = msg.get('interactive') or {}
        if interactive.get('type') == 'button_reply':
            return (interactive.get('button_reply') or {}).get('title') or ''
        if interactive.get('type') == 'list_reply':
            return (interactive.get('list_reply') or {}).get('title') or ''
    return ''


def _get_or_create_contact(wa_id: str, profile_name: str = '') -> WhatsAppDonnaContact:
    contact, created = WhatsAppDonnaContact.objects.get_or_create(
        wa_id=wa_id,
        defaults={'profile_name': profile_name},
    )
    if profile_name and contact.profile_name != profile_name:
        contact.profile_name = profile_name
        contact.save(update_fields=['profile_name', 'updated_at'])
    return contact


def _touch_contact(contact: WhatsAppDonnaContact, message_dt):
    when = message_dt or timezone.now()
    if not contact.last_message_at or when > contact.last_message_at:
        contact.last_message_at = when
        contact.save(update_fields=['last_message_at', 'updated_at'])


def _upsert_inbound(contact: WhatsAppDonnaContact, msg: dict, profile_names: dict[str, str]):
    wamid = msg.get('id')
    if not wamid:
        return
    wa_id = str(msg.get('from') or contact.wa_id)
    if wa_id != contact.wa_id:
        contact = _get_or_create_contact(wa_id, profile_names.get(wa_id, ''))

    msg_dt = _wa_ts_to_datetime(msg.get('timestamp'))
    defaults = {
        'contact': contact,
        'direction': WhatsAppDonnaMessage.Direction.INBOUND,
        'message_type': msg.get('type') or '',
        'body_text': _message_body(msg),
        'raw_payload': msg,
        'wa_timestamp': msg_dt,
    }
    WhatsAppDonnaMessage.objects.update_or_create(wamid=wamid, defaults=defaults)
    _touch_contact(contact, msg_dt)


def _apply_status(status: dict):
    wamid = status.get('id')
    if not wamid:
        return
    new_status = status.get('status') or ''
    updated = WhatsAppDonnaMessage.objects.filter(wamid=wamid).update(
        status=new_status,
        updated_at=timezone.now(),
    )
    if not updated:
        recipient = str(status.get('recipient_id') or '')
        if not recipient:
            return
        contact = _get_or_create_contact(recipient)
        msg_dt = _wa_ts_to_datetime(status.get('timestamp'))
        WhatsAppDonnaMessage.objects.create(
            contact=contact,
            wamid=wamid,
            direction=WhatsAppDonnaMessage.Direction.OUTBOUND,
            message_type='status',
            body_text='',
            status=new_status,
            raw_payload=status,
            wa_timestamp=msg_dt,
        )
        _touch_contact(contact, msg_dt)


@transaction.atomic
def ingest_whatsapp_webhook_payload(payload: dict) -> int:
    """Parse Meta WhatsApp webhook JSON; return number of records touched."""
    if payload.get('object') != 'whatsapp_business_account':
        return 0

    touched = 0
    for entry in payload.get('entry') or []:
        for change in entry.get('changes') or []:
            value = change.get('value') or {}
            if value.get('messaging_product') != 'whatsapp':
                continue

            profile_names = {
                str(item.get('wa_id')): (item.get('profile') or {}).get('name', '')
                for item in (value.get('contacts') or [])
                if item.get('wa_id')
            }

            for msg in value.get('messages') or []:
                wa_id = str(msg.get('from') or '')
                if not wa_id:
                    continue
                name = profile_names.get(wa_id, '')
                contact = _get_or_create_contact(wa_id, name)
                _upsert_inbound(contact, msg, profile_names)
                touched += 1

            for status in value.get('statuses') or []:
                _apply_status(status)
                touched += 1

    return touched
