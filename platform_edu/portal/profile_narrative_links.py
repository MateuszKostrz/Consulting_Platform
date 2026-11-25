from __future__ import annotations

from typing import Any

NARRATIVE_LINK_SECTIONS: tuple[tuple[str, str], ...] = (
    ('personal_statement', 'Personal Statement'),
    ('cv', 'CV'),
    ('application_essays', 'Application Essays'),
)

SECTION_DEFAULT_TITLE: dict[str, str] = {
    'personal_statement': 'Personal Statement',
    'cv': 'CV',
    'application_essays': 'Application Essays',
}

LEGACY_URL_FIELD: dict[str, str] = {
    'personal_statement': 'personal_statement_google_doc_url',
    'cv': 'cv_google_doc_url',
    'application_essays': 'application_essays_google_doc_url',
}

MAX_LINKS_PER_SECTION = 25


def _clean_link_item(raw: dict[str, Any] | None, *, section_key: str) -> dict[str, str] | None:
    if not isinstance(raw, dict):
        return None
    title = str(raw.get('title') or '').strip()
    url = str(raw.get('url') or '').strip()
    if not title and not url:
        return None
    if not title:
        title = SECTION_DEFAULT_TITLE.get(section_key, 'Document')
    return {'title': title[:200], 'url': url[:500]}


def links_from_document_links_json(
    document_links: dict | None,
    *,
    section_key: str,
    legacy_url: str = '',
) -> list[dict[str, str]]:
    data = document_links if isinstance(document_links, dict) else {}
    items = data.get(section_key) or []
    out: list[dict[str, str]] = []
    if isinstance(items, list):
        for raw in items[:MAX_LINKS_PER_SECTION]:
            cleaned = _clean_link_item(raw, section_key=section_key)
            if cleaned:
                out.append(cleaned)
    if not out and (legacy_url or '').strip():
        default_title = SECTION_DEFAULT_TITLE.get(section_key, 'Document')
        out.append({'title': default_title, 'url': legacy_url.strip()})
    return out


def build_document_links_payload(narrative) -> dict[str, list[dict[str, str]]]:
    payload: dict[str, list[dict[str, str]]] = {}
    for section_key, _label in NARRATIVE_LINK_SECTIONS:
        legacy_field = LEGACY_URL_FIELD[section_key]
        legacy_url = getattr(narrative, legacy_field, '') or ''
        payload[section_key] = links_from_document_links_json(
            narrative.document_links,
            section_key=section_key,
            legacy_url=legacy_url,
        )
    return payload


def sync_legacy_url_fields(narrative) -> None:
    for section_key, field in LEGACY_URL_FIELD.items():
        links = links_from_document_links_json(
            narrative.document_links,
            section_key=section_key,
            legacy_url='',
        )
        first_url = links[0]['url'] if links else ''
        setattr(narrative, field, first_url)


def parse_narrative_links_post(post, section_key: str) -> list[dict[str, str]]:
    """Parse link_{section_key}_{i}_title / _url fields from POST."""
    links: list[dict[str, str]] = []
    for index in range(MAX_LINKS_PER_SECTION):
        title_key = f'link_{section_key}_{index}_title'
        url_key = f'link_{section_key}_{index}_url'
        if title_key not in post and url_key not in post:
            if index > 0:
                break
            continue
        title = post.get(title_key, '').strip()
        url = post.get(url_key, '').strip()
        if not title and not url:
            continue
        if url and not url.startswith(('http://', 'https://')):
            url = ''
        if not title:
            title = SECTION_DEFAULT_TITLE.get(section_key, 'Document')
        links.append({'title': title[:200], 'url': url[:500]})
    return links


def save_narrative_links_from_post(narrative, post) -> None:
    payload: dict[str, list[dict[str, str]]] = {}
    for section_key, _label in NARRATIVE_LINK_SECTIONS:
        payload[section_key] = parse_narrative_links_post(post, section_key)
    narrative.document_links = payload
    sync_legacy_url_fields(narrative)