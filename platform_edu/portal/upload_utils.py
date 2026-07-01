import os

from .constants import (
    ALLOWED_PROFILE_PHOTO_EXTENSIONS,
    MAX_PROFILE_PHOTO_SIZE,
)

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


def assign_file_field(instance, field_name, uploaded_file):
    if not uploaded_file:
        return None
    if getattr(instance, field_name):
        return 'already_exists'
    getattr(instance, field_name).save(uploaded_file.name, uploaded_file, save=False)
    return None


def validate_profile_photo(uploaded_file):
    if not uploaded_file:
        return None

    if uploaded_file.size > MAX_PROFILE_PHOTO_SIZE:
        return 'Profile photo must be 5 MB or smaller.'

    extension = os.path.splitext(uploaded_file.name)[1].lower()
    if extension not in ALLOWED_PROFILE_PHOTO_EXTENSIONS:
        return 'Only JPG and PNG images are allowed.'

    return None


def replace_profile_photo(profile, uploaded_file):
    error = validate_profile_photo(uploaded_file)
    if error:
        return error
    clear_file_field(profile, 'profile_photo')
    profile.profile_photo.save(uploaded_file.name, uploaded_file, save=False)
    return None


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
