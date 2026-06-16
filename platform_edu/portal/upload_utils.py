import os

ACADEMIC_UPLOAD_FIELDS = {
    'transcripts': 'Transcripts',
    'cv_upload': 'CV',
    'personal_statement_upload': 'Personal Statement',
}

DIAGNOSTIC_UPLOAD_FIELDS = {
    'template_file': 'Template',
    'student_submission': 'Student submission',
    'admin_document': 'Consultant document',
}


def upload_display_name(file_field):
    if not file_field:
        return ''
    return os.path.basename(file_field.name)


def clear_file_field(instance, field_name):
    file_field = getattr(instance, field_name)
    if file_field:
        file_field.delete(save=False)


def replace_file_field(instance, field_name, uploaded_file):
    if not uploaded_file:
        return
    clear_file_field(instance, field_name)
    getattr(instance, field_name).save(uploaded_file.name, uploaded_file, save=False)


def can_delete_academic_upload(platform_user):
    if not platform_user:
        return False
    return platform_user.is_admin or platform_user.is_student


def can_delete_diagnostic_upload(request, platform_user, upload_field):
    is_admin = bool(platform_user and platform_user.is_admin)
    if upload_field == 'student_submission':
        return request.user.is_authenticated
    if upload_field in {'template_file', 'admin_document'}:
        return is_admin
    return False
