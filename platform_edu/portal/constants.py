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

SUBJECT_OTHER_VALUE = 'other'

GRADUATION_YEARS = ['2024', '2025', '2026', '2027', '2028', '2029', '2030', 'Other']

PHONE_COUNTRY_CODES = [
    ('+44', '+44 (UK)'),
    ('+1', '+1 (US/Canada)'),
    ('+48', '+48 (Poland)'),
    ('+49', '+49 (Germany)'),
    ('+33', '+33 (France)'),
    ('+31', '+31 (Netherlands)'),
    ('+41', '+41 (Switzerland)'),
    ('+353', '+353 (Ireland)'),
    ('+61', '+61 (Australia)'),
    ('+64', '+64 (New Zealand)'),
    ('+971', '+971 (UAE)'),
    ('+65', '+65 (Singapore)'),
    ('+852', '+852 (Hong Kong)'),
    ('+34', '+34 (Spain)'),
    ('+39', '+39 (Italy)'),
    ('+32', '+32 (Belgium)'),
    ('+46', '+46 (Sweden)'),
    ('+45', '+45 (Denmark)'),
    ('+47', '+47 (Norway)'),
    ('+91', '+91 (India)'),
    ('+86', '+86 (China)'),
]

COUNTRY_CHOICES = [
    'United Kingdom', 'United States', 'Canada', 'Australia', 'Netherlands',
    'Germany', 'France', 'Switzerland', 'Singapore', 'Hong Kong', 'Ireland',
    'Spain', 'Italy', 'Belgium', 'Sweden', 'Denmark', 'Norway', 'New Zealand',
    'United Arab Emirates', 'Other',
]

BUDGET_CHOICES = [
    ('under_10k', 'Under 10,000 / year'),
    ('10k_25k', '10,000 – 25,000 / year'),
    ('25k_50k', '25,000 – 50,000 / year'),
    ('50k_75k', '50,000 – 75,000 / year'),
    ('75k_plus', '75,000+ / year'),
    ('flexible', 'Flexible / not sure yet'),
]

BUDGET_CURRENCY_CHOICES = [
    ('USD', 'USD ($)'),
    ('EUR', 'EUR (€)'),
    ('GBP', 'GBP (£)'),
    ('PLN', 'PLN (zł)'),
]

DEFAULT_BUDGET_CURRENCY = 'USD'

MAX_UPLOAD_SIZE = 10 * 1024 * 1024
ALLOWED_UPLOAD_EXTENSIONS = {'.pdf', '.doc', '.docx'}
MAX_PROFILE_PHOTO_SIZE = 5 * 1024 * 1024
ALLOWED_PROFILE_PHOTO_EXTENSIONS = {'.jpg', '.jpeg', '.png'}

DIAGNOSTIC_CALL_BOOKING_URL = 'https://calendly.com/edunade/diagnostics'

DIAGNOSTIC_STAGES = [
    {
        'key': 'readiness',
        'step': 1,
        'title': 'Schedule a call',
        'description': (
            'Book a call with your Edunade consultant. We get to know you and '
            'assess your preferences and situation in relation to your ambitions.'
        ),
        'mandatory': False,
        'template_label': None,
        'student_upload_label': None,
        'admin_upload_label': None,
        'allow_student_upload': False,
        'allow_template_upload': False,
    },
    {
        'key': 'test',
        'step': 2,
        'title': 'Download exam',
        'description': 'Download the diagnostic exam, complete it, and return it as instructed by your consultant.',
        'mandatory': False,
        'template_label': 'Diagnostic exam',
        'student_upload_label': None,
        'admin_upload_label': None,
        'allow_student_upload': False,
        'allow_template_upload': True,
    },
    {
        'key': 'report',
        'step': 3,
        'title': 'Receive report',
        'description': 'Your personalised diagnostics report, prepared after your call and exam.',
        'mandatory': False,
        'template_label': None,
        'student_upload_label': None,
        'admin_upload_label': 'Diagnostics report',
        'allow_student_upload': False,
        'allow_template_upload': False,
    },
]

DIAGNOSTIC_STAGE_KEYS = [stage['key'] for stage in DIAGNOSTIC_STAGES]

INTERVIEW_PREP_SESSION_SLOTS = (1, 2, 3)
INTERVIEW_FEEDBACK_EXTENSIONS = {'.pdf', '.docx'}

RESULT_DOCUMENT_TYPE_CHOICES = [
    ('transcript', 'Transcript'),
    ('cv', 'CV'),
    ('final_diploma', 'Final diploma'),
    ('language_certificate', 'Language certificate'),
    ('exam_results', 'Exam results'),
    ('other', 'Other'),
]

RESULT_DOCUMENT_TYPE_VALUES = {value for value, _ in RESULT_DOCUMENT_TYPE_CHOICES}

HOME_DOCUMENT_TYPE_CHOICES = [
    ('passport', 'Passport'),
    ('id', 'ID'),
    ('cv', 'CV'),
    ('transcript', 'Transcript'),
    ('language_certificate', 'Language certificate'),
    ('personal_statement', 'Personal statement'),
    ('other', 'Other'),
]

HOME_DOCUMENT_TYPE_VALUES = {value for value, _ in HOME_DOCUMENT_TYPE_CHOICES}

HOME_DOCUMENT_ALLOWED_EXTENSIONS = {'.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png'}
MAX_HOME_DOCUMENT_SIZE = 5 * 1024 * 1024

DEADLINE_TIMEZONE_CHOICES = [
    ('Europe/Warsaw', 'Warsaw (CET)'),
    ('Europe/London', 'London (GMT/BST)'),
    ('Europe/Amsterdam', 'Amsterdam (CET)'),
    ('Europe/Berlin', 'Berlin (CET)'),
    ('Europe/Paris', 'Paris (CET)'),
    ('America/New_York', 'New York (ET)'),
    ('America/Los_Angeles', 'Los Angeles (PT)'),
    ('Asia/Tokyo', 'Tokyo (JST)'),
    ('Asia/Singapore', 'Singapore (SGT)'),
    ('Australia/Sydney', 'Sydney (AEST)'),
    ('UTC', 'UTC'),
]

DEADLINE_TIMEZONE_VALUES = {tz for tz, _ in DEADLINE_TIMEZONE_CHOICES}
