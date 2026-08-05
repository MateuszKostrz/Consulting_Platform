"""Consulting pathway section order and post-save redirects."""

from django.shortcuts import redirect

SECTION_FLOW = (
    'personal-information',
    'academic-profile',
    'diagnostics',
    'portfolio-design',
    'strategic-application',
    'profile-narrative',
    'application-logistics',
    'interview-preparation',
    'offers',
    'results',
)

ALLOWED_NEXT_SECTIONS = frozenset(SECTION_FLOW) | {'home'}


def next_section_url_name(current_url_name):
    try:
        index = SECTION_FLOW.index(current_url_name)
    except ValueError:
        return 'home'
    if index + 1 < len(SECTION_FLOW):
        return SECTION_FLOW[index + 1]
    return 'home'


def redirect_after_section_save(request, default_url_name):
    next_section = request.POST.get('next_section', '').strip()
    if next_section in ALLOWED_NEXT_SECTIONS:
        return redirect(next_section)
    return redirect(default_url_name)
