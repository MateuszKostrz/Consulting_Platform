from __future__ import annotations

import logging
from typing import Final

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class WhatsAppTranslateError(Exception):
    pass


LANGUAGE_CODES: Final[dict[str, str]] = {
    'pl': 'Polish',
    'en': 'English',
    'es': 'Spanish',
    'de': 'German',
    'ro': 'Romanian',
}

ALIAS_TO_CODE: Final[dict[str, str]] = {
    'esp': 'es',
}


def normalize_lang_code(code: str | None) -> str:
    raw = (code or '').strip().lower()
    if not raw or raw in ('none', 'off', 'no', 'skip'):
        return ''
    raw = ALIAS_TO_CODE.get(raw, raw)
    if raw not in LANGUAGE_CODES:
        raise WhatsAppTranslateError(f'Unsupported language: {code}')
    return raw


def translate_text(
    text: str,
    *,
    target: str,
    source: str | None = None,
) -> dict[str, str]:
    body = (text or '').strip()
    if not body:
        raise WhatsAppTranslateError('Nothing to translate.')
    if len(body) > 4000:
        raise WhatsAppTranslateError('Message is too long to translate.')

    target_code = normalize_lang_code(target)
    source_code = normalize_lang_code(source) if source else ''
    if source_code and source_code == target_code:
        return {'translation': body, 'provider': 'none', 'target': target_code}

    api_key = (getattr(settings, 'OPENAI_API_KEY', None) or '').strip()
    if api_key:
        try:
            return _openai_translate(api_key, body, target_code=target_code, source_code=source_code)
        except WhatsAppTranslateError:
            raise
        except Exception:
            logger.exception('OpenAI translate failed, falling back')

    try:
        return _mymemory_translate(body, target_code=target_code, source_code=source_code)
    except requests.RequestException as exc:
        logger.exception('MyMemory translate failed')
        raise WhatsAppTranslateError('Could not reach translation service.') from exc


def translate_to_polish(text: str) -> dict[str, str]:
    return translate_text(text, target='pl')


def translate_from_polish(text: str, target: str) -> dict[str, str]:
    return translate_text(text, target=target, source='pl')


def _openai_translate(
    api_key: str,
    body: str,
    *,
    target_code: str,
    source_code: str,
) -> dict[str, str]:
    target_name = LANGUAGE_CODES[target_code]
    if source_code:
        source_name = LANGUAGE_CODES[source_code]
        system = (
            f'Translate the message from {source_name} into {target_name}. '
            'Reply with only the translation, no quotes or commentary.'
        )
    else:
        system = (
            f'Translate the customer WhatsApp message into {target_name}. '
            'Reply with only the translation, no quotes or commentary.'
        )
    response = requests.post(
        'https://api.openai.com/v1/chat/completions',
        headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
        json={
            'model': 'gpt-4o-mini',
            'temperature': 0.2,
            'messages': [
                {'role': 'system', 'content': system},
                {'role': 'user', 'content': body},
            ],
        },
        timeout=45,
    )
    try:
        data = response.json()
    except ValueError as exc:
        raise WhatsAppTranslateError('Invalid response from translation service.') from exc
    if not response.ok:
        err = (data.get('error') or {}).get('message') or response.text
        raise WhatsAppTranslateError(err[:300] or 'Translation failed.')
    choices = data.get('choices') or []
    content = ((choices[0] or {}).get('message') or {}).get('content') or ''
    translation = content.strip()
    if not translation:
        raise WhatsAppTranslateError('Empty translation.')
    return {'translation': translation, 'provider': 'openai', 'target': target_code}


def _mymemory_translate(body: str, *, target_code: str, source_code: str) -> dict[str, str]:
    source = source_code or 'Autodetect'
    langpair = f'{source}|{target_code}'
    response = requests.get(
        'https://api.mymemory.translated.net/get',
        params={'q': body, 'langpair': langpair},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    if (data.get('responseStatus') or 0) != 200:
        detail = data.get('responseDetails') or 'Translation failed.'
        raise WhatsAppTranslateError(str(detail)[:300])
    translation = (data.get('responseData') or {}).get('translatedText') or ''
    translation = translation.strip()
    if not translation:
        raise WhatsAppTranslateError('Empty translation.')
    return {'translation': translation, 'provider': 'mymemory', 'target': target_code}