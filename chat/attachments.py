import mimetypes
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError


ALLOWED_ATTACHMENT_EXTENSIONS = {
    '.pdf', '.doc', '.docx', '.odt', '.rtf', '.txt', '.csv',
    '.jpg', '.jpeg', '.png', '.gif', '.webp',
    '.mp3', '.m4a', '.aac', '.ogg', '.wav', '.flac',
    '.mp4', '.m4v', '.mov', '.webm', '.avi', '.mkv',
}

ATTACHMENT_ACCEPT = ','.join(sorted(ALLOWED_ATTACHMENT_EXTENSIONS))


def attachment_limits():
    return {
        'max_size': settings.CHAT_ATTACHMENT_MAX_SIZE_MB * 1024 * 1024,
        'max_count': settings.CHAT_ATTACHMENT_MAX_COUNT,
    }


def safe_attachment_name(name):
    return str(name).replace('\\', '/').rsplit('/', 1)[-1]


def validate_attachments(files, *, context='одно сообщение'):
    limits = attachment_limits()
    if len(files) > limits['max_count']:
        raise ValidationError(
            f'Можно прикрепить не более {limits["max_count"]} файлов за {context}.'
        )

    total_size = sum(upload.size for upload in files)
    if total_size > settings.DATA_UPLOAD_MAX_MEMORY_SIZE:
        raise ValidationError('Общий размер вложений превышает допустимый размер запроса.')

    for upload in files:
        safe_name = safe_attachment_name(upload.name)
        extension = Path(safe_name).suffix.lower()
        if (
            not safe_name
            or len(safe_name) > 255
            or any(ord(character) < 32 or ord(character) == 127 for character in safe_name)
        ):
            raise ValidationError(
                'Название файла некорректно или содержит более 255 символов.'
            )
        if extension not in ALLOWED_ATTACHMENT_EXTENSIONS:
            raise ValidationError(f'Формат файла «{extension or "без расширения"}» не разрешён.')
        if upload.size <= 0:
            raise ValidationError(f'Файл «{safe_name}» пуст.')
        if upload.size > limits['max_size']:
            raise ValidationError(
                f'Файл «{safe_name}» превышает лимит '
                f'{settings.CHAT_ATTACHMENT_MAX_SIZE_MB} МБ.'
            )


def normalized_content_type(upload):
    extension = Path(upload.name).suffix.lower()
    guessed_type = mimetypes.guess_type(f'file{extension}')[0]
    return guessed_type or 'application/octet-stream'
