from .models import ReferenceContact

MAX_REFERENCE_CONTACTS = 3

REFERENCE_CONTACT_FIELDS = (
    'name',
    'position',
    'email',
    'institution',
    'phone',
    'relation_to_student',
)


def _empty_reference_contact():
    return {field: '' for field in REFERENCE_CONTACT_FIELDS}


def reference_contacts_for_form(academic):
    stored = {
        contact.sort_order: contact
        for contact in academic.reference_contacts.order_by('sort_order')
    }
    rows = []
    visible = 1
    for index in range(1, MAX_REFERENCE_CONTACTS + 1):
        contact = stored.get(index)
        if contact:
            row = {field: getattr(contact, field, '') or '' for field in REFERENCE_CONTACT_FIELDS}
        else:
            row = _empty_reference_contact()
        rows.append(row)
        if any(row.values()):
            visible = index
    return rows, visible


def save_reference_contacts(academic, request):
    academic.reference_contacts.all().delete()
    for index in range(1, MAX_REFERENCE_CONTACTS + 1):
        data = {
            field: request.POST.get(f'ref_contact_{index}_{field}', '').strip()
            for field in REFERENCE_CONTACT_FIELDS
        }
        if any(data.values()):
            ReferenceContact.objects.create(
                academic_profile=academic,
                sort_order=index,
                **data,
            )
