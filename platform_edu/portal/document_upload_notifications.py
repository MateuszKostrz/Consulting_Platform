"""Email consultants when a student uploads a home-page document."""

from __future__ import annotations

import logging

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from .constants import HOME_DOCUMENT_UPLOAD_NOTIFY_EMAILS
from .models import StudentDocument

logger = logging.getLogger(__name__)


def _student_display_name(document: StudentDocument) -> str:
    student = document.student
    name = f'{student.first_name} {student.last_name}'.strip()
    if name and student.email:
        return f'{name} ({student.email})'
    return name or student.email or f'Student #{student.pk}'


def notify_consultants_of_student_document_upload(document: StudentDocument) -> None:
    recipients = [email for email in HOME_DOCUMENT_UPLOAD_NOTIFY_EMAILS if email]
    if not recipients:
        return

    uploaded_at = timezone.localtime(document.created_at)
    date_label = uploaded_at.strftime('%Y-%m-%d %H:%M %Z')

    subject = 'New document uploaded'
    message = (
        'A new document was uploaded.\n\n'
        f'User: {_student_display_name(document)}\n'
        f'Date: {date_label}\n'
        f'Document type: {document.get_document_type_display()}\n'
    )

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipients,
            fail_silently=False,
        )
    except Exception:
        logger.exception(
            'Failed to send home document upload notification for document %s',
            document.pk,
        )
