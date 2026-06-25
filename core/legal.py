from functools import lru_cache
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET

from django.conf import settings


LEGAL_DOCUMENTS = {
    'privacy-policy': {
        'title': 'Политика обработки персональных данных',
        'version': 'v1-2026',
        'effective_date': '2026-01-01',
        'filename': 'Маэстро_Политика_обработик_ПДн_v1_2026.docx',
    },
    'cookie-policy': {
        'title': 'Условия использования cookie',
        'version': 'v1-2026',
        'effective_date': '2026-01-01',
        'filename': 'Условия использования cookie (v1 2026).docx',
    },
    'terms-of-use': {
        'title': 'Пользовательское соглашение',
        'version': 'v1-2026',
        'effective_date': '2026-01-01',
        'filename': 'Маэстро_пользовательское_соглашение_v1_2026.docx',
    },
    'content-rules': {
        'title': 'Правила использования материалов на сайте',
        'version': 'v1-2026',
        'effective_date': '2026-01-01',
        'filename': 'Маэстро_Правила_использования_материала_на_сайте_v1_2026.docx',
    },
    'personal-data-consent': {
        'title': 'Согласие на обработку персональных данных',
        'version': 'v1-2026',
        'effective_date': '2026-01-01',
        'filename': 'Маэстро_Согласие_на_обработку_персональных_данных_v1_2026.docx',
    },
}

REQUIRED_LEGAL_DOCUMENT_SLUGS = (
    'terms-of-use',
    'content-rules',
    'privacy-policy',
    'personal-data-consent',
)

COOKIE_POLICY_SLUG = 'cookie-policy'


def get_document(slug):
    return LEGAL_DOCUMENTS.get(slug)


def get_required_documents():
    return {slug: LEGAL_DOCUMENTS[slug] for slug in REQUIRED_LEGAL_DOCUMENT_SLUGS}


def get_cookie_policy():
    return LEGAL_DOCUMENTS[COOKIE_POLICY_SLUG]


def get_client_ip(request):
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def get_user_agent(request):
    return request.META.get('HTTP_USER_AGENT', '')


def user_has_required_legal_acceptances(user):
    if not user.is_authenticated:
        return False

    from accounts.models import LegalAcceptance

    accepted = set(
        LegalAcceptance.objects.filter(
            user=user,
            document_slug__in=REQUIRED_LEGAL_DOCUMENT_SLUGS,
        ).values_list('document_slug', 'document_version')
    )
    return all(
        (slug, LEGAL_DOCUMENTS[slug]['version']) in accepted
        for slug in REQUIRED_LEGAL_DOCUMENT_SLUGS
    )


def user_has_cookie_consent(user):
    if not user.is_authenticated:
        return False

    from accounts.models import CookieConsent

    return CookieConsent.objects.filter(
        user=user,
        policy_version=get_cookie_policy()['version'],
    ).exists()


@lru_cache(maxsize=None)
def get_document_text(slug):
    document = get_document(slug)
    if document is None:
        raise KeyError(slug)

    path = Path(settings.BASE_DIR) / 'docs' / 'maestro' / document['filename']
    return _read_docx_text(path)


def _read_docx_text(path):
    paragraphs = []
    with ZipFile(path) as docx:
        xml = docx.read('word/document.xml')

    root = ET.fromstring(xml)
    namespace = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    for paragraph in root.findall('.//w:p', namespace):
        pieces = []
        for text in paragraph.findall('.//w:t', namespace):
            if text.text:
                pieces.append(text.text)
        paragraph_text = ''.join(pieces).strip()
        if paragraph_text:
            paragraphs.append(paragraph_text)

    return paragraphs
