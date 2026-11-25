"""Personal Statement Assessment (Profile Self-Assessment document)."""

from __future__ import annotations

PS_ASSESSMENT_TITLE = 'Self-assessment'

PS_ASSESSMENT_INTRO = (
    'Please fill in all your achievements, activities, or participations in the following '
    'document. Answer all questions to the best of your knowledge. If you don’t have an answer '
    'to that question, or simply don’t know the answer, leave it empty. If you are not sure '
    'whether something should be included in the answer, please do include it, then we will '
    'filter it out.'
)

PS_ASSESSMENT_QUESTIONS: tuple[dict[str, str], ...] = (
    {
        'key': 'why_apply',
        'label': 'Why do you want to apply for this course?',
        'hint': (
            'You can list it as bullet points (e.g. childhood dream, career prospects, '
            'aligns with your hobbies, etc.)'
        ),
    },
    {
        'key': 'challenge',
        'label': (
            "Can you describe a challenge you've faced and how it has shaped your academic "
            'or personal development?'
        ),
        'hint': 'Focus on how it changed your mindset, resilience, or motivation.',
    },
    {
        'key': 'career_goals',
        'label': (
            'What are your career goals after university, and how does this course help you get there?'
        ),
        'hint': "Be as specific as possible—even if your plans aren't 100% certain.",
    },
    {
        'key': 'subjects_enjoyed',
        'label': 'Which subjects have you enjoyed the most in school/university, and why?',
        'hint': (
            'Try to explain what excites you about those subjects and how they relate to '
            'your university course.'
        ),
    },
    {
        'key': 'inspiration',
        'label': 'Have any teachers, books, or lessons inspired your interest in this course?',
        'hint': 'Feel free to name them and explain how they influenced your decision.',
    },
    {
        'key': 'hobbies',
        'label': (
            'What hobbies or activities do you do in your free time, and how do they relate '
            '(directly or indirectly) to your chosen course?'
        ),
        'hint': (
            'For example, managing a blog, playing chess, coding apps, volunteering, leading a team, etc.'
        ),
    },
    {
        'key': 'additional',
        'label': (
            'If there’s anything else we forgot to ask about, but you think would be worth mentioning, '
            'then please fill it in the box below.'
        ),
        'hint': '',
    },
)


def ps_assessment_values(academic) -> dict[str, str]:
    raw = getattr(academic, 'personal_statement_assessment', None) or {}
    if not isinstance(raw, dict):
        raw = {}
    values = {str(k): str(v or '') for k, v in raw.items()}
    if not values.get('career_goals') and (getattr(academic, 'career_goals', '') or '').strip():
        values['career_goals'] = academic.career_goals.strip()
    return values


def ps_assessment_questions_for_form(academic) -> list[dict[str, str]]:
    stored = ps_assessment_values(academic)
    return [
        {
            **question,
            'value': stored.get(question['key'], ''),
        }
        for question in PS_ASSESSMENT_QUESTIONS
    ]


def student_display_name(profile) -> str:
    if profile.platform_user:
        pu = profile.platform_user
        name = f'{pu.first_name} {pu.last_name}'.strip()
        if name:
            return name
        if pu.email:
            return pu.email
    return profile.personal_email or profile.edunade_email or ''


def ps_assessment_form_context(academic, profile) -> dict:
    ps_values = ps_assessment_values(academic)
    return {
        'ps_assessment_title': PS_ASSESSMENT_TITLE,
        'ps_assessment_intro': PS_ASSESSMENT_INTRO,
        'ps_assessment_desired_course': ps_values.get('desired_course', ''),
        'ps_assessment_questions': ps_assessment_questions_for_form(academic),
        'student_display_name': student_display_name(profile),
    }


def save_ps_assessment_from_post(academic, post) -> None:
    values = {
        'desired_course': post.get('ps_desired_course', '').strip(),
    }
    for question in PS_ASSESSMENT_QUESTIONS:
        key = question['key']
        values[key] = post.get(f'ps_{key}', '').strip()
    academic.personal_statement_assessment = values
    career = values.get('career_goals', '').strip()
    if career:
        academic.career_goals = career