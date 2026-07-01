from .constants import IB_SUBJECT_CHOICES, SUBJECT_OTHER_VALUE

IB_SUBJECT_VALUES = {value for value, _ in IB_SUBJECT_CHOICES}


def subjects_from_post(request):
    subjects = request.POST.getlist('subjects')
    other_text = request.POST.get('subjects_other', '').strip()
    normalized = []
    seen = set()

    for subject in subjects:
        if subject == SUBJECT_OTHER_VALUE:
            continue
        subject = subject.strip()
        if subject and subject not in seen:
            seen.add(subject)
            normalized.append(subject)

    if SUBJECT_OTHER_VALUE in subjects or other_text:
        for part in other_text.split(','):
            part = part.strip()
            if part and part not in seen:
                seen.add(part)
                normalized.append(part)

    return ', '.join(normalized)


def subjects_for_form(stored_subjects):
    stored = [part.strip() for part in stored_subjects.split(',') if part.strip()]
    known = [subject for subject in stored if subject in IB_SUBJECT_VALUES]
    custom = [subject for subject in stored if subject not in IB_SUBJECT_VALUES]
    return known, custom
