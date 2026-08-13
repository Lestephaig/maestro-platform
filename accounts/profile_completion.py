from django.core.exceptions import ObjectDoesNotExist


ROLE_REQUIREMENTS = {
    'performer': (
        ('user.first_name', 'Имя'),
        ('user.last_name', 'Фамилия'),
        ('bio', 'Биография'),
        ('country', 'Страна'),
        ('city', 'Город'),
    ),
    'agent': (
        ('user.first_name', 'Имя'),
        ('user.last_name', 'Фамилия'),
        ('country', 'Страна'),
        ('city', 'Город'),
        ('bio', 'О себе'),
    ),
    'client': (
        ('company_name', 'Название'),
        ('country', 'Страна'),
        ('city', 'Город'),
        ('address', 'Адрес'),
        ('contact_person', 'Контактное лицо'),
    ),
}

PROFILE_ATTRIBUTES = {
    'performer': 'performer_profile',
    'agent': 'agent_profile',
    'client': 'client_profile',
}

PROFILE_COMPLETION_FIELDS = {
    'performer': (
        'user.first_name', 'user.last_name', 'performer_type', 'birth_date',
        'education', 'achievements', 'bio', 'country', 'city', 'video_url',
        'photo', 'photo_position',
    ),
    'agent': (
        'user.first_name', 'user.last_name', 'agency_name', 'bio', 'country',
        'city', 'specialization', 'experience_years', 'website',
    ),
    'client': (
        'company_name', 'country', 'city', 'address', 'venue_type',
        'hall_capacity', 'has_stage', 'contact_person', 'website', 'stage_size',
        'microphones_count', 'sound_system', 'mixing_console',
        'lighting_equipment', 'video_equipment', 'has_internet', 'power_supply',
        'has_green_rooms',
    ),
}


def _has_value(value):
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def get_profile_completion(user):
    """Calculate completion from the informational fields available to a role."""
    profile_attribute = PROFILE_ATTRIBUTES.get(user.role)
    field_paths = list(PROFILE_COMPLETION_FIELDS.get(user.role, ()))
    if not profile_attribute or not field_paths:
        return {'completed': 0, 'total': 0, 'percentage': 100, 'level': 'complete'}

    try:
        profile = getattr(user, profile_attribute)
    except ObjectDoesNotExist:
        return {'completed': 0, 'total': 0, 'percentage': 100, 'level': 'complete'}

    if user.role == 'performer':
        if profile.performer_type == profile.PERFORMER_TYPE_VOCALIST:
            field_paths.append('voice_type')
        elif profile.performer_type in (
            profile.PERFORMER_TYPE_INSTRUMENTALIST,
            profile.PERFORMER_TYPE_CONCERTMASTER,
        ):
            field_paths.append('instrument')

    completed = 0
    for path in field_paths:
        owner, field_name = (user, path[5:]) if path.startswith('user.') else (profile, path)
        completed += int(_has_value(getattr(owner, field_name, None)))

    total = len(field_paths)
    percentage = round(completed / total * 100) if total else 100
    if percentage < 50:
        level = 'low'
    elif percentage < 80:
        level = 'medium'
    elif percentage < 100:
        level = 'high'
    else:
        level = 'complete'
    return {
        'completed': completed,
        'total': total,
        'percentage': percentage,
        'level': level,
    }


def get_missing_profile_fields(user):
    """Return user-facing labels for required, currently empty profile fields."""
    requirements = ROLE_REQUIREMENTS.get(user.role)
    profile_attribute = PROFILE_ATTRIBUTES.get(user.role)
    if not requirements or not profile_attribute:
        return []

    try:
        profile = getattr(user, profile_attribute)
    except ObjectDoesNotExist:
        # Legacy/system accounts without a role profile cannot complete it via
        # the profile form, so avoid trapping them in an unrecoverable loop.
        return []

    missing = []
    for path, label in requirements:
        owner, field_name = (user, path[5:]) if path.startswith('user.') else (profile, path)
        value = getattr(owner, field_name, '')
        if value is None or (isinstance(value, str) and not value.strip()):
            missing.append(label)
    return missing
