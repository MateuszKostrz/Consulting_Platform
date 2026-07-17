from .constants import IB_SUBJECT_CHOICES

IB_SUBJECT_VALUES = {value for value, _ in IB_SUBJECT_CHOICES}
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


def subjects_from_post(request):
    subjects = request.POST.getlist('subjects')
    custom_subjects = request.POST.getlist('subjects_custom')
    normalized = []
    seen = set()

    for subject in subjects:
        subject = subject.strip()
        if subject and subject not in seen:
            seen.add(subject)
            normalized.append(subject)

    for subject in custom_subjects:
        subject = subject.strip()
        if subject and subject not in seen:
            seen.add(subject)
            normalized.append(subject)

    return ', '.join(normalized)


def subjects_for_form(stored_subjects):
    stored = [part.strip() for part in stored_subjects.split(',') if part.strip()]
    known = [subject for subject in stored if subject in IB_SUBJECT_VALUES]
    custom = [subject for subject in stored if subject not in IB_SUBJECT_VALUES]
    return known, custom
