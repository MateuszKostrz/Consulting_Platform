from __future__ import annotations

import json
from datetime import timedelta

from django.db.models import OuterRef, Subquery
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .models import WhatsAppDonnaContact, WhatsAppDonnaMessage
from .whatsapp_inbox_auth import (
    is_whatsapp_inbox_authenticated,
    login_whatsapp_inbox,
    logout_whatsapp_inbox,
    require_whatsapp_inbox,
    require_whatsapp_inbox_json,
    verify_whatsapp_inbox_login,
)
from .whatsapp_outbound import (
    WhatsAppSendError,
    send_template_to_recipient,
    send_text_to_contact,
)
from .whatsapp_translate import WhatsAppTranslateError, normalize_lang_code, translate_from_polish, translate_text

WHATSAPP_DONNA_TEMPLATES = (
    {
        'name': 'test_first_message',
        'label': 'Test message (PL)',
        'language': 'pl',
    },
    {
        'name': 'black_week_first_message_en',
        'label': 'Black Friday first message (EN)',
        'language': 'en',
    },
)

WHATSAPP_COUNTRY_CODES = (
    ('48', 'Poland (+48)'),
    ('1', 'United States (+1)'),
    ('44', 'United Kingdom (+44)'),
    ('49', 'Germany (+49)'),
    ('33', 'France (+33)'),
    ('39', 'Italy (+39)'),
    ('34', 'Spain (+34)'),
    ('31', 'Netherlands (+31)'),
    ('43', 'Austria (+43)'),
    ('41', 'Switzerland (+41)'),
    ('420', 'Czechia (+420)'),
    ('421', 'Slovakia (+421)'),
    ('370', 'Lithuania (+370)'),
    ('371', 'Latvia (+371)'),
    ('372', 'Estonia (+372)'),
    ('380', 'Ukraine (+380)'),
)


def _last_message_subquery():
    return (
        WhatsAppDonnaMessage.objects.filter(contact=OuterRef('pk'))
        .exclude(message_type='status')
        .order_by('-wa_timestamp', '-created_at', '-id')
    )


def _contacts_queryset():
    return (
        WhatsAppDonnaContact.objects.annotate(
            last_msg_direction=Subquery(_last_message_subquery().values('direction')[:1]),
        )
        .order_by('-last_message_at', '-updated_at')[:300]
    )


def _contact_needs_reply(last_direction: str | None) -> bool:
    return last_direction == WhatsAppDonnaMessage.Direction.INBOUND


def _serialize_contact(contact: WhatsAppDonnaContact) -> dict:
    last_dir = getattr(contact, 'last_msg_direction', None)
    return {
        'id': contact.id,
        'name': contact.profile_name or contact.wa_id,
        'wa_id': contact.wa_id,
        'needs_reply': _contact_needs_reply(last_dir),
    }


def _message_display_body(msg: WhatsAppDonnaMessage) -> str:
    if msg.body_text:
        return msg.body_text
    if msg.message_type and msg.message_type != 'text':
        return f'({msg.message_type})'
    return ''


def _message_delivery_error(msg: WhatsAppDonnaMessage) -> str:
    payload = msg.raw_payload if isinstance(msg.raw_payload, dict) else {}
    for err in payload.get('errors') or []:
        if not isinstance(err, dict):
            continue
        detail = (err.get('error_data') or {}).get('details') or err.get('message')
        if detail:
            return str(detail)
    return ''


def _can_send_session_text(contact: WhatsAppDonnaContact) -> tuple[bool, str]:
    last_in = (
        WhatsAppDonnaMessage.objects.filter(
            contact=contact,
            direction=WhatsAppDonnaMessage.Direction.INBOUND,
        )
        .exclude(message_type='status')
        .order_by('-wa_timestamp', '-created_at', '-id')
        .first()
    )
    if not last_in:
        return False, (
            'This number has never messaged your WhatsApp. Use + New template, '
            'or ask them to send any message to your business number first.'
        )
    when = last_in.wa_timestamp or last_in.created_at
    if timezone.now() - when > timedelta(hours=24):
        return False, (
            'More than 24 hours since their last reply. Use + New template — '
            'the chat box only works inside Meta’s 24-hour window.'
        )
    return True, ''


def _serialize_message(msg: WhatsAppDonnaMessage) -> dict:
    ts = msg.wa_timestamp or msg.created_at
    return {
        'id': msg.id,
        'direction': msg.direction,
        'body': _message_display_body(msg),
        'status': msg.status or '',
        'delivery_error': _message_delivery_error(msg),
        'at': ts.isoformat() if ts else '',
    }


@require_http_methods(['GET', 'POST'])
def donna_whatsapp_login(request):
    if is_whatsapp_inbox_authenticated(request):
        return redirect('donna-whatsapp-inbox')

    error = ''
    next_url = (request.GET.get('next') or request.POST.get('next') or '').strip()
    if next_url and not next_url.startswith('/donna/whatsapp'):
        next_url = reverse('donna-whatsapp-inbox')

    if request.method == 'POST':
        email = (request.POST.get('email') or '').strip()
        password = request.POST.get('password') or ''
        if verify_whatsapp_inbox_login(email, password):
            login_whatsapp_inbox(request)
            return redirect(next_url or reverse('donna-whatsapp-inbox'))
        error = 'Invalid email or password.'

    return render(
        request,
        'donna_whatsapp_login.html',
        {'error': error, 'next_url': next_url},
    )


@require_http_methods(['GET', 'POST'])
def donna_whatsapp_logout(request):
    logout_whatsapp_inbox(request)
    return redirect('donna-whatsapp-login')


@require_whatsapp_inbox
def donna_whatsapp_inbox(request):
    contacts = list(_contacts_queryset())
    selected = None
    contact_param = (request.GET.get('contact') or '').strip()
    if contact_param.isdigit():
        selected = next((c for c in contacts if c.id == int(contact_param)), None)
        if not selected:
            selected = WhatsAppDonnaContact.objects.filter(pk=int(contact_param)).first()

    thread = []
    if selected:
        thread = list(
            WhatsAppDonnaMessage.objects.filter(contact=selected)
            .exclude(message_type='status')
            .order_by('wa_timestamp', 'created_at', 'id')[:500]
        )

    session_text_ok = True
    session_text_hint = ''
    if selected:
        session_text_ok, session_text_hint = _can_send_session_text(selected)

    initial_thread = None
    selected_needs_reply = False
    if selected:
        last_dir = (
            WhatsAppDonnaMessage.objects.filter(contact=selected)
            .exclude(message_type='status')
            .order_by('-wa_timestamp', '-created_at', '-id')
            .values_list('direction', flat=True)
            .first()
        )
        selected_needs_reply = _contact_needs_reply(last_dir)

    if selected:
        initial_thread = {
            'contact': {
                'id': selected.id,
                'name': selected.profile_name or selected.wa_id,
                'wa_id': selected.wa_id,
                'needs_reply': selected_needs_reply,
            },
            'messages': [_serialize_message(m) for m in thread],
            'session_text_ok': session_text_ok,
            'session_text_hint': session_text_hint,
        }

    return render(
        request,
        'donna_whatsapp_inbox.html',
        {
            'contacts': contacts,
            'selected_contact': selected,
            'thread_messages': thread,
            'initial_thread': initial_thread,
            'whatsapp_templates': WHATSAPP_DONNA_TEMPLATES,
            'country_codes': WHATSAPP_COUNTRY_CODES,
            'session_text_ok': session_text_ok,
            'session_text_hint': session_text_hint,
            'selected_needs_reply': selected_needs_reply,
        },
    )


@require_whatsapp_inbox_json
@require_GET
def donna_whatsapp_thread_api(request, contact_id: int):
    contact = get_object_or_404(WhatsAppDonnaContact, pk=contact_id)
    thread = list(
        WhatsAppDonnaMessage.objects.filter(contact=contact)
        .exclude(message_type='status')
        .order_by('wa_timestamp', 'created_at', 'id')[:500]
    )
    session_text_ok, session_text_hint = _can_send_session_text(contact)
    last_dir = (
        WhatsAppDonnaMessage.objects.filter(contact=contact)
        .exclude(message_type='status')
        .order_by('-wa_timestamp', '-created_at', '-id')
        .values_list('direction', flat=True)
        .first()
    )
    return JsonResponse(
        {
            'contact': {
                'id': contact.id,
                'name': contact.profile_name or contact.wa_id,
                'wa_id': contact.wa_id,
                'needs_reply': _contact_needs_reply(last_dir),
            },
            'messages': [_serialize_message(m) for m in thread],
            'session_text_ok': session_text_ok,
            'session_text_hint': session_text_hint,
        }
    )


@require_whatsapp_inbox_json
@require_GET
def donna_whatsapp_messages_api(request, contact_id: int):
    contact = get_object_or_404(WhatsAppDonnaContact, pk=contact_id)
    qs = (
        WhatsAppDonnaMessage.objects.filter(contact=contact)
        .exclude(message_type='status')
        .order_by('wa_timestamp', 'created_at', 'id')
    )
    since_id = (request.GET.get('since_id') or '').strip()
    if since_id.isdigit():
        qs = qs.filter(id__gt=int(since_id))

    return JsonResponse(
        {
            'contact_id': contact.id,
            'messages': [_serialize_message(m) for m in qs[:500]],
        }
    )


@require_whatsapp_inbox_json
@require_POST
def donna_whatsapp_send_api(request):
    contact_id = (request.POST.get('contact_id') or '').strip()
    body = (request.POST.get('body') or '').strip()
    if not contact_id.isdigit():
        return JsonResponse({'error': 'Invalid contact'}, status=400)
    if not body:
        return JsonResponse({'error': 'Message is empty'}, status=400)

    contact = get_object_or_404(WhatsAppDonnaContact, pk=int(contact_id))
    can_send, session_error = _can_send_session_text(contact)
    if not can_send:
        return JsonResponse({'error': session_error}, status=400)

    translate_to_raw = (request.POST.get('translate_to') or '').strip()
    try:
        translate_to = normalize_lang_code(translate_to_raw)
    except WhatsAppTranslateError as exc:
        return JsonResponse({'error': str(exc)}, status=400)
    if translate_to:
        try:
            translated = translate_from_polish(body, translate_to)
            body = translated['translation']
        except WhatsAppTranslateError as exc:
            return JsonResponse({'error': str(exc)}, status=400)

    try:
        msg = send_text_to_contact(contact, body)
    except WhatsAppSendError as exc:
        return JsonResponse({'error': str(exc)}, status=400)

    return JsonResponse({'ok': True, 'message': _serialize_message(msg)})


@require_whatsapp_inbox_json
@require_POST
def donna_whatsapp_send_template_api(request):
    country_code = (request.POST.get('country_code') or '48').strip()
    phone = (request.POST.get('phone') or '').strip()
    template_name = (request.POST.get('template_name') or '').strip().lower()
    allowed = {t['name']: t for t in WHATSAPP_DONNA_TEMPLATES}
    template = allowed.get(template_name)
    if not template:
        return JsonResponse({'error': 'Unknown template'}, status=400)
    name = template['name']
    language = template['language']
    if not phone:
        return JsonResponse({'error': 'Phone number is required'}, status=400)

    try:
        contact, msg = send_template_to_recipient(
            country_code=country_code,
            local_number=phone,
            template_name=name,
            language_code=language,
        )
    except WhatsAppSendError as exc:
        return JsonResponse({'error': str(exc)}, status=400)

    return JsonResponse(
        {
            'ok': True,
            'contact_id': contact.id,
            'contact': {
                'id': contact.id,
                'name': contact.profile_name or contact.wa_id,
                'wa_id': contact.wa_id,
            },
            'redirect_url': f'{reverse("donna-whatsapp-inbox")}?contact={contact.id}',
            'message': _serialize_message(msg),
        }
    )


@require_whatsapp_inbox_json
@require_POST
def donna_whatsapp_translate_api(request):
    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except (json.JSONDecodeError, UnicodeDecodeError):
        payload = {}
    text = (payload.get('text') or request.POST.get('text') or '').strip()
    if not text:
        return JsonResponse({'error': 'Missing text'}, status=400)
    target = (payload.get('target') or request.POST.get('target') or 'pl').strip()
    source = (payload.get('source') or request.POST.get('source') or '').strip() or None
    try:
        result = translate_text(text, target=target, source=source)
    except WhatsAppTranslateError as exc:
        return JsonResponse({'error': str(exc)}, status=400)
    return JsonResponse(result)


@require_whatsapp_inbox_json
@require_POST
def donna_whatsapp_delete_contact_api(request):
    contact_id = (request.POST.get('contact_id') or '').strip()
    if not contact_id.isdigit():
        return JsonResponse({'error': 'Invalid contact'}, status=400)

    contact = get_object_or_404(WhatsAppDonnaContact, pk=int(contact_id))
    contact.delete()
    return JsonResponse({'ok': True, 'redirect_url': reverse('donna-whatsapp-inbox')})
