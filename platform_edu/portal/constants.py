IB_SUBJECT_CHOICES = [
    ('physics_sl', 'Physics SL'),
    ('physics_hl', 'Physics HL'),
    ('biology_sl', 'Biology SL'),
    ('biology_hl', 'Biology HL'),
    ('chemistry_sl', 'Chemistry SL'),
    ('chemistry_hl', 'Chemistry HL'),
    ('math_ai_sl', 'Math AI SL'),
    ('math_ai_hl', 'Math AI HL'),
    ('math_aa_sl', 'Math AA SL'),
    ('math_aa_hl', 'Math AA HL'),
    ('comp_sci_sl', 'Comp Sci SL'),
    ('comp_sci_hl', 'Comp Sci HL'),
    ('geography_sl', 'Geography SL'),
    ('geography_hl', 'Geography HL'),
    ('economics_sl', 'Economics SL'),
    ('economics_hl', 'Economics HL'),
    ('history_sl', 'History SL'),
    ('history_hl', 'History HL'),
    ('business_sl', 'Business SL'),
    ('business_hl', 'Business HL'),
    ('english_a_sl', 'English A SL'),
    ('english_a_hl', 'English A HL'),
    ('english_b_sl', 'English B SL'),
    ('english_b_hl', 'English B HL'),
]

GRADUATION_YEARS = ['2024', '2025', '2026', '2027', '2028', '2029', '2030', 'Other']

COUNTRY_CHOICES = [
    'United Kingdom', 'United States', 'Canada', 'Australia', 'Netherlands',
    'Germany', 'France', 'Switzerland', 'Singapore', 'Hong Kong', 'Ireland',
    'Spain', 'Italy', 'Belgium', 'Sweden', 'Denmark', 'Norway', 'New Zealand',
    'United Arab Emirates', 'Other',
]

BUDGET_CHOICES = [
    ('under_10k', 'Under $10,000 / year'),
    ('10k_25k', '$10,000 – $25,000 / year'),
    ('25k_50k', '$25,000 – $50,000 / year'),
    ('50k_75k', '$50,000 – $75,000 / year'),
    ('75k_plus', '$75,000+ / year'),
    ('flexible', 'Flexible / not sure yet'),
]

MAX_UPLOAD_SIZE = 10 * 1024 * 1024
ALLOWED_UPLOAD_EXTENSIONS = {'.pdf', '.doc', '.docx'}

DIAGNOSTIC_STAGES = [
    {
        'key': 'readiness',
        'step': 1,
        'title': 'Readiness & Profile Assessment',
        'description': (
            'A Zoom call with your Edunade consultant. Download the assessment form, '
            'complete it after your session, and upload it here.'
        ),
        'mandatory': False,
        'template_label': 'Assessment form',
        'student_upload_label': 'Completed assessment form',
        'admin_upload_label': 'Consultant materials',
        'allow_student_upload': True,
        'allow_template_upload': True,
    },
    {
        'key': 'homework',
        'step': 2,
        'title': 'Profile Self-Assessment (Homework)',
        'description': 'Download the self-assessment form, complete it, and upload your answers. This step is required.',
        'mandatory': True,
        'template_label': 'Self-assessment form',
        'student_upload_label': 'Completed self-assessment',
        'admin_upload_label': 'Consultant feedback',
        'allow_student_upload': True,
        'allow_template_upload': True,
    },
    {
        'key': 'test',
        'step': 3,
        'title': 'Diagnostic Test',
        'description': 'Download the diagnostic test, complete it, and submit your answers on the platform.',
        'mandatory': False,
        'template_label': 'Diagnostic test',
        'student_upload_label': 'Completed test submission',
        'admin_upload_label': 'Marked test / notes',
        'allow_student_upload': True,
        'allow_template_upload': True,
    },
    {
        'key': 'report',
        'step': 4,
        'title': 'Diagnostics Report',
        'description': 'Your personalised diagnostics report prepared by Edunade. Available as a PDF once ready.',
        'mandatory': False,
        'template_label': None,
        'student_upload_label': None,
        'admin_upload_label': 'Diagnostics report (PDF)',
        'allow_student_upload': False,
        'allow_template_upload': False,
    },
]

DIAGNOSTIC_STAGE_KEYS = [stage['key'] for stage in DIAGNOSTIC_STAGES]
