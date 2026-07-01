from .models import AcademicActivityEntry

ACTIVITY_ENTRY_FIELDS = ('name', 'date', 'location', 'description')
ACTIVITY_ENTRY_CATEGORY = 'extracurricular'
MAX_ACTIVITY_ENTRY_SCAN = 100

_LEGACY_CATEGORY_ORDER = {
    'test': 0,
    'extracurricular': 1,
    'award': 2,
}


def _empty_activity_entry():
    return {field: '' for field in ACTIVITY_ENTRY_FIELDS}


def activity_entries_for_form(academic):
    entries = list(academic.activity_entries.all())
    entries.sort(
        key=lambda entry: (
            _LEGACY_CATEGORY_ORDER.get(entry.category, 99),
            entry.sort_order,
        )
    )
    rows = [
        {field: getattr(entry, field, '') or '' for field in ACTIVITY_ENTRY_FIELDS}
        for entry in entries
    ]
    if not rows:
        return []
    return rows


def activity_entries_has_data(academic):
    return academic.activity_entries.exists()


def save_activity_entries(academic, request):
    academic.activity_entries.all().delete()
    sort_order = 1
    for index in range(1, MAX_ACTIVITY_ENTRY_SCAN + 1):
        data = {
            field: request.POST.get(f'activity_{index}_{field}', '').strip()
            for field in ACTIVITY_ENTRY_FIELDS
        }
        if not any(data.values()):
            continue
        AcademicActivityEntry.objects.create(
            academic_profile=academic,
            category=ACTIVITY_ENTRY_CATEGORY,
            sort_order=sort_order,
            **data,
        )
        sort_order += 1
