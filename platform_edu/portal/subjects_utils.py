from .constants import IB_SUBJECT_CHOICES, SUBJECT_LEVEL_CHOICES

IB_SUBJECT_VALUES = {value for value, _ in IB_SUBJECT_CHOICES}
IB_LABEL_BY_VALUE = dict(IB_SUBJECT_CHOICES)
STANDARD_LEVEL_VALUES = {value for value, _ in SUBJECT_LEVEL_CHOICES if value != 'Other'}
STANDARD_CURRICULUM_VALUES = {'IB', 'A-Levels', 'SAT', 'Other'}


def curriculum_for_form(stored_curriculum, stored_other=''):
    stored_curriculum = (stored_curriculum or '').strip()
    stored_other = (stored_other or '').strip()

    if stored_curriculum in STANDARD_CURRICULUM_VALUES and stored_curriculum != 'Other':
        return stored_curriculum, ''

    if stored_curriculum == 'Other':
        return 'Other', stored_other

    if stored_curriculum:
        return 'Other', stored_curriculum

    return '', stored_other


def curriculum_from_post(request):
    curriculum = request.POST.get('curriculum', '').strip()
    curriculum_other = request.POST.get('curriculum_other', '').strip()
    if curriculum == 'Other':
        return 'Other', curriculum_other
    return curriculum, ''


def encode_subject(name, level='', level_other=''):
    name = (name or '').strip()
    if not name:
        return None

    level = (level or '').strip()
    level_other = (level_other or '').strip()

    if level == 'Other':
        level_part = f'Other:{level_other}' if level_other else 'Other'
    elif level:
        level_part = level
    else:
        level_part = ''

    if level_part:
        return f'{name}|{level_part}'
    return name


def _parse_legacy_ib(value):
    if value not in IB_SUBJECT_VALUES:
        return None
    label = IB_LABEL_BY_VALUE[value]
    if label.endswith(' HL'):
        return {'name': label[:-3].strip(), 'level': 'HL', 'level_other': ''}
    if label.endswith(' SL'):
        return {'name': label[:-3].strip(), 'level': 'SL', 'level_other': ''}
    return {'name': label, 'level': '', 'level_other': ''}


def decode_subject(entry):
    entry = (entry or '').strip()
    if not entry:
        return {'name': '', 'level': '', 'level_other': ''}

    if '|' in entry:
        name, level_part = entry.split('|', 1)
        name = name.strip()
        level_part = level_part.strip()
        if level_part.startswith('Other:'):
            return {'name': name, 'level': 'Other', 'level_other': level_part[6:].strip()}
        if level_part == 'Other':
            return {'name': name, 'level': 'Other', 'level_other': ''}
        if level_part in STANDARD_LEVEL_VALUES:
            return {'name': name, 'level': level_part, 'level_other': ''}
        return {'name': name, 'level': 'Other', 'level_other': level_part}

    legacy = _parse_legacy_ib(entry)
    if legacy:
        return legacy

    return {'name': entry, 'level': '', 'level_other': ''}


def subjects_from_post(request):
    names = request.POST.getlist('subjects_name')
    levels = request.POST.getlist('subjects_level')
    level_others = request.POST.getlist('subjects_level_other')

    normalized = []
    seen = set()

    for index, name in enumerate(names):
        level = levels[index].strip() if index < len(levels) else ''
        level_other = level_others[index].strip() if index < len(level_others) else ''
        encoded = encode_subject(name, level, level_other)
        if not encoded or encoded in seen:
            continue
        seen.add(encoded)
        normalized.append(encoded)

    return ', '.join(normalized)


def subjects_for_form(stored_subjects):
    stored = [part.strip() for part in (stored_subjects or '').split(',') if part.strip()]
    if not stored:
        return [{'name': '', 'level': '', 'level_other': ''}]
    return [decode_subject(part) for part in stored]
