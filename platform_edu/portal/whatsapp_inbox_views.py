from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from .models import WhatsAppDonnaContact, WhatsAppDonnaMessage
from .profile_access import get_platform_user
from .whatsapp_outbound import (
    WhatsAppSendError,
    send_template_to_recipient,
    send_text_to_contact,
)

WHATSAPP_DONNA_TEMPLATES = (
    {
        'name': 'test_first_message',
        'label': 'Test first message',
        'language': 'pl',
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


def _require_admin(request):
    platform_user = get_platform_user(request)
    if not platform_user or not platform_user.is_admin:
        return None
    return platform_user


def _message_display_body(msg: WhatsAppDonnaMessage) -> str:
    if msg.body_text:
        return msg.body_text
    if msg.message_type and msg.message_type != 'text':
        return f'({msg.message_type})'
    return ''


def _serialize_message(msg: WhatsAppDonnaMessage) -> dict:
    ts = msg.wa_timestamp or msg.created_at
    return {
        'id': msg.id,
        'direction': msg.direction,
        'body': _message_display_body(msg),
        'status': msg.status or '',
        'at': ts.isoformat() if ts else '',
    }


@login_required
def donna_whatsapp_inbox(request):
    if not _require_admin(request):
        messages.error(request, 'Only admins can open Donna WhatsApp inbox.')
        return redirect('home')

    contacts = list(
        WhatsAppDonnaContact.objects.all().order_by('-last_message_at', '-updated_at')[:300]
    )
    selected = None
    contact_param = (request.GET.get('contact') or '').strip()
    if contact_param.isdigit():
        selected = next((c for c in contacts if c.id == int(contact_param)), None)
        if not selected:
            selected = WhatsAppDonnaContact.objects.filter(pk=int(contact_param)).first()
    elif contacts:
        selected = contacts[0]

    thread = []
    if selected:
        thread = list(
            WhatsAppDonnaMessage.objects.filter(contact=selected)
            .exclude(message_type='status')
            .order_by('wa_timestamp', 'created_at', 'id')[:500]
        )

    return render(
        request,
        'donna_whatsapp_inbox.html',
        {
            'contacts': contacts,
            'selected_contact': selected,
            'thread_messages': thread,
            'whatsapp_templates': WHATSAPP_DONNA_TEMPLATES,
            'country_codes': WHATSAPP_COUNTRY_CODES,
        },
    )


@login_required
@require_GET
def donna_whatsapp_messages_api(request, contact_id: int):
    if not _require_admin(request):
        return JsonResponse({'error': 'Forbidden'}, status=403)

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


@login_required
@require_POST
def donna_whatsapp_send_api(request):
    if not _require_admin(request):
        return JsonResponse({'error': 'Forbidden'}, status=403)

    contact_id = (request.POST.get('contact_id') or '').strip()
    body = (request.POST.get('body') or '').strip()
    if not contact_id.isdigit():
        return JsonResponse({'error': 'Invalid contact'}, status=400)
    if not body:
        return JsonResponse({'error': 'Message is empty'}, status=400)

    contact = get_object_or_404(WhatsAppDonnaContact, pk=int(contact_id))
    try:
        msg = send_text_to_contact(contact, body)
    except WhatsAppSendError as exc:
        return JsonResponse({'error': str(exc)}, status=400)

    return JsonResponse({'ok': True, 'message': _serialize_message(msg)})


@login_required
@require_POST
def donna_whatsapp_send_template_api(request):
    if not _require_admin(request):
        return JsonResponse({'error': 'Forbidden'}, status=403)

    country_code = (request.POST.get('country_code') or '48').strip()
    phone = (request.POST.get('phone') or '').strip()
    template_name = (request.POST.get('template_name') or '').strip()

    allowed = {t['name']: t for t in WHATSAPP_DONNA_TEMPLATES}
    template = allowed.get(template_name)
    if not template:
        return JsonResponse({'error': 'Unknown template'}, status=400)
    if not phone:
        return JsonResponse({'error': 'Phone number is required'}, status=400)

    try:
        contact, msg = send_template_to_recipient(
            country_code=country_code,
            local_number=phone,
            template_name=template['name'],
            language_code=template['language'],
        )
    except WhatsAppSendError as exc:
        return JsonResponse({'error': str(exc)}, status=400)

    return JsonResponse(
        {
            'ok': True,
            'contact_id': contact.id,
            'redirect_url': f'?contact={contact.id}',
            'message': _serialize_message(msg),
        }
    )
