from django.urls import resolve

def current_url_name(request):
    try:
        url_name = resolve(request.path_info).url_name
    except:
        url_name = ''
    
    # Define menu sections with patterns and specific URLs
    menu_sections = {

        # PAST PAPERS PER YEAR

        'past_papers_year_math_ai_sl': lambda name: (
            name == 'math-ai-sl-past-papers' or
            (name.startswith('math-ai-sl-') and ('may' in name or 'nov' in name) and 'tz' in name and ('p1' in name or 'p2' in name) and 'topics' not in name and 'videos' not in name)
        ),

        'past_papers_year_math_ai_hl': lambda name: (
            name == 'math-ai-hl-past-papers' or
            (name.startswith('math-ai-hl-') and ('may' in name or 'nov' in name) and 'tz' in name and ('p1' in name or 'p2' in name) and 'topics' not in name and 'videos' not in name)
        ),

        'past_papers_year_math_aa_sl': lambda name: (
            name == 'math-aa-sl-past-papers' or
            (name.startswith('math-aa-sl-') and ('may' in name or 'nov' in name) and 'tz' in name and ('p1' in name or 'p2' in name) and 'topics' not in name and 'videos' not in name)
        ),
        
        'past_papers_year_math_aa_hl': lambda name: (
            name == 'math-aa-hl-past-papers' or
            (name.startswith('math-aa-hl-') and ('may' in name or 'nov' in name) and 'tz' in name and ('p1' in name or 'p2' in name) and 'topics' not in name and 'videos' not in name)
        ),

        'past_papers_year_physics_sl': lambda name: (
            name == 'physics-sl-past-papers' or
            (name.startswith('physics-sl-') and ('may' in name or 'nov' in name or 'specimen' in name))
        ),

        'past_papers_year_physics_hl': lambda name: (
            name == 'physics-hl-past-papers' or
            (name.startswith('physics-hl-') and ('may' in name or 'nov' in name or 'specimen' in name))
        ),

        'past_papers_year_comp_sci_sl': lambda name: (
            name == 'comp-sci-sl-past-papers' or
            (name.startswith('comp-sci-sl-') and ('may' in name or 'nov' in name or 'specimen' in name))
        ),
        
        # REST
        'past_papers_topics_math_ai_sl': [
           'math-ai-sl-past-papers-topics', 'math-ai-sl-number-skills-videos', 'math-ai-sl-seq-series-videos', 'math-ai-sl-lin-eq-graphs-videos'
        ],
        'past_papers_topics_math_ai_hl': [
           'math-ai-hl-past-papers-topics', 'math-ai-hl-number-skills-videos', 'math-ai-hl-seq-series-videos', 'math-ai-hl-lin-eq-graphs-videos'
        ],

        'webinars': [
           'webinars-recorded', 'webinars-live', 'webinar-interview-preparation', 'webinar-cv', 'webinar-around-the-world'
        ],
        
        'webinars_live': [
           'webinars-live'
        ],
        
        'webinars_recorded': [
           'webinars-recorded', 'webinar-interview-preparation', 'webinar-cv', 'webinar-around-the-world', 'webinar-personal-statement', 'webinar-uni-docs', 'webinar-ias-ees', 'webinar-surviving-a-degree', 'webinar-application-portals', 'webinar-revision', 'webinar-why-study-abroad', 'webinar-suitability'
        ],

        'uni_database': [
           'uni-database'
        ],

        'contact': [
           'contact'
        ],

        'suitability_survey': [
           'suitability-survey'
        ],

        'uni_docs': [
           'uni-docs'
        ],
    }
    
    # Pattern-based detection for more flexible matching
    pattern_sections = {
        'questionbank': lambda name: (
            # Main subject pages
            name in ['math-ai-sl', 'math-ai-hl', 'math-aa-sl', 'math-aa-hl', 'comp-sci-sl', 'comp-sci-hl', 'bio-sl', 'bio-hl'] or
            # Subtopic pages (contain subject + topic pattern) BUT exclude past papers
            (any(name.startswith(subject + '-') or name.endswith('-' + subject.split('-')[-1]) for subject in ['math-ai-sl', 'math-ai-hl', 'math-aa-sl', 'math-aa-hl', 'comp-sci-sl', 'comp-sci-hl', 'bio-sl', 'bio-hl']) and 
             'past-papers' not in name and 'may' not in name and 'nov' not in name and 'tz' not in name and 'p1' not in name and 'p2' not in name)
        ) and 'past-papers' not in name and 'videos' not in name,

        'questionbank_ai_sl': lambda name: (
            name == 'math-ai-sl' or
            (name.startswith('math-ai-sl-') or name.endswith('-ai-sl')) and
            name in ['math-ai-sl', 'number-skills-ai-sl', 'seq-series-ai-sl', 'systems-lin-eq-ai-sl', 'lin-eq-graphs-ai-sl', 'applications-of-functions-ai-sl', 'properties-of-functions-ai-sl', 'geometry-shapes-ai-sl', 'trigonometry-ai-sl',  'voronoi-diagrams-ai-sl', 'descriptive-stats-ai-sl', 'bivariate-statistics-ai-sl', 'hypothesis-testing-ai-sl', 'probability-ai-sl', 'distributions-ai-sl', 'integration-ai-sl', 'differentiation-ai-sl', 'differentiation-ai-sl', 'integration-ai-sl']
        ),
        'questionbank_ai_hl': lambda name: (
            name == 'math-ai-hl' or
            (name.startswith('math-ai-hl-') or name.endswith('-ai-hl')) and
            name in ['math-ai-hl', 'number-skills-ai-hl', 'seq-series-ai-hl', 'complex-numbers-ai-hl', 'systems-lin-eq-ai-hl', 'linear-equations-graphs-ai-hl', 'application-of-functions-ai-hl', 'properties-of-functions-ai-hl', 'function-transformations-ai-hl', 'geometry-shapes-ai-hl', 'trigonometry-ai-hl', 'trigonometric-functions-ai-hl', 'geometric-transformations-ai-hl', 'voronoi-diagrams-ai-hl', 'graph-theory-ai-hl', 'vectors-ai-hl', 'descriptive-stats-ai-hl', 'bivariate-statistics-ai-hl', 'hypothesis-testing-ai-hl', 'probability-ai-hl', 'confidence-intervals-ai-hl', 'distributions-ai-hl', 'integration-ai-hl', 'differentiation-ai-hl', 'kinematics-ai-hl', 'differential-equation-ai-hl', 'matrices-ai-hl']
        ),
        'questionbank_aa_sl': lambda name: (
            name == 'math-aa-sl' or
            (name.startswith('math-aa-sl-') or name.endswith('-aa-sl')) and
            name in ['math-aa-sl', 'seq-and-series-aa-sl', 'exp-and-logs-aa-sl', 'binomial-expansion-aa-sl', 'proofs-aa-sl', 'properties-of-functions-aa-sl', 'quadratic-functions-aa-sl', 'rational-functions-aa-sl', 'exp-and-logs-functions-aa-sl', 'function-transformations-aa-sl', 'geometry-aa-sl', 'differentiation-aa-sl', 'distributions-aa-sl', 'kinematics-aa-sl', 'statistics-aa-sl', 'trig-functions-aa-sl', 'bivariate-stats-aa-sl', 'probability-aa-sl', 'integration-aa-sl']
        ),
        'questionbank_aa_hl': lambda name: (
            name == 'math-aa-hl' or
            (name.startswith('math-aa-hl-') or name.endswith('-aa-hl')) and
            name in ['math-aa-hl', 'seq-and-series-aa-hl', 'exp-and-logs-aa-hl', 'binomial-expansion-aa-hl', 'counting-principles-aa-hl', 'proofs-aa-hl', 'complex-numbers-aa-hl', 'systems-of-equations-aa-hl', 'properties-of-functions-aa-hl', 'quadratic-functions-aa-hl', 'rational-functions-aa-hl', 'polynomials-aa-hl', 'modulus-inequalities-aa-hl', 'exp-and-logs-functions-aa-hl', 'function-transformations-aa-hl', 'geometry-aa-hl', 'vectors-aa-hl', 'differentiation-aa-hl', 'distributions-aa-hl', 'kinematics-aa-hl', 'statistics-aa-hl', 'trig-functions-aa-hl', 'bivariate-stats-aa-hl', 'probability-aa-hl', 'differential-equations-aa-hl', 'differential-calculus-aa-hl', 'integral-calculus-aa-hl', 'maclaurin-series-aa-hl']
        ),
        'questionbank_biology_sl': lambda name: (
            name == 'biology-sl' or
            name.startswith('biology-sl-') or
            name in ['biology-sl', 'water-sl', 'cell-structure-sl', 'nucleic-acids-sl', 'diversity-of-organisms-sl', 'evolution-and-speciation-sl', 'conservation-of-biodiversity-sl', 'carbohydrates-and-lipids-sl', 'proteins-sl', 'membranes-transport-sl', 'organelles-compartment-sl', 'cell-specialization-sl', 'gas-exchange-sl', 'transport-sl', 'adaptation-to-environment-sl', 'ecological-niches-sl', 'enzymes-metabolism-sl', 'cell-respiration-sl', 'photosynthesis-sl', 'neural-signaling-sl', 'integration-of-body-systems-sl', 'defence-against-disease-sl', 'population-communities-sl', 'transfer-energy-matter-sl', 'dna-replication-sl', 'protein-synthesis-sl', 'mutations-editing-sl', 'natural-selection-sl', 'inheritance-sl', 'climate-change-sl', 'water-potential-sl', 'cell-division-sl', 'reproduction-sl', 'stability-change-sl', 'homeostasis-sl']
        ),

        'questionbank_biology_hl': lambda name: (
            name == 'biology-hl' or
            name.startswith('biology-hl-') or
            name in ['biology-hl', 'water-hl', 'nucleic-acids-hl', 'origin-of-cells-hl', 'viruses-hl', 'classification-hl', 'muscle-and-motility-hl', 'chemical-signaling-hl', 'cell-structure-hl', 'diversity-of-organisms-hl', 'evolution-and-speciation-hl', 'conservation-of-biodiversity-hl', 'carbohydrates-and-lipids-hl', 'proteins-hl', 'membranes-transport-hl', 'organelles-compartment-hl', 'cell-specialization-hl', 'gas-exchange-hl', 'transport-hl', 'adaptation-to-environment-hl', 'ecological-niches-hl', 'enzymes-metabolism-hl', 'cell-respiration-hl', 'photosynthesis-hl', 'neural-signaling-hl', 'integration-of-body-systems-hl', 'defence-against-disease-hl', 'population-communities-hl', 'transfer-energy-matter-hl', 'dna-replication-hl', 'protein-synthesis-hl', 'mutations-editing-hl', 'natural-selection-hl', 'inheritance-hl', 'climate-change-hl', 'water-potential-hl', 'cell-division-hl', 'reproduction-hl', 'stability-change-hl', 'homeostasis-hl', 'gene-expression-hl']
        ),


        'questionbank_physics_sl': lambda name: (
            name == 'physics-sl' or
            name.startswith('physics-sl-') or
            name in ['kinematics-sl', 'work-energy-power-sl', 'thermal-energy-sl', 'greenhouse-effect-sl', 'ideal-gas-model-sl', 'electric-circuits-sl', 'electric-fields-sl', 'forces-momentum-sl', 'simple-harmonic-motion-sl', 'wave-model-sl', 'standing-waves-sl', 'doppler-effect-sl', 'gravitational-fields-sl', 'electric-magnetic-fields-sl', 'motion-in-fields-sl', 'structure-atom-sl', 'radioactive-decay-sl', 'fission-sl', 'fusion-and-stars-sl', 'wave-phenomena-sl']
        ),
        'questionbank_physics_hl': lambda name: (
            name == 'physics-hl' or
            name.startswith('physics-hl-') or
            name in ['kinematics-hl', 'forces-momentum-hl', 'work-energy-power-hl', 'rigid-body-mechanics-hl', 'galilean-and-special-relativity-hl', 'thermal-energy-hl', 'greenhouse-effect-hl', 'ideal-gas-model-hl', 'thermodynamics-hl', 'electric-circuits-hl', 'simple-harmonic-motion-hl', 'wave-model-hl', 'wave-phenomena-hl', 'standing-waves-hl', 'doppler-effect-hl', 'gravitational-fields-hl', 'electric-magnetic-fields-hl', 'motion-in-fields-hl', 'induction-hl', 'structure-atom-hl', 'quantum-physics-hl', 'radioactive-decay-hl', 'fission-hl', 'fusion-and-stars-hl']
        ),

        'questionbank_comp_sci_sl': lambda name: (
            name == 'comp-sci-sl' or
            name.startswith('comp-sci-sl-') or
            name in ['system-fundamentals-sl', 'computer-organisation-sl', 'networks-sl', 'computational-thinking-sl', 'variables-and-input-sl', 'if-statements-sl', 'loops-sl', 'arrays-sl', 'methods-sl', 'constructors-sl', 'oop-sl']
        ),

        'questionbank_comp_sci_hl': lambda name: (
            name == 'comp-sci-hl' or
            name.startswith('comp-sci-hl-') or
            name in ['system-fundamentals-hl', 'computer-organisation-hl', 'networks-hl', 'computational-thinking-hl', 'variables-and-input-hl', 'if-statements-hl', 'loops-hl', 'arrays-hl', 'methods-hl', 'constructors-hl', 'resource-management-hl', 'abstract-data-structures-hl', 'oop-hl']
        ),

    
        'exam_builder': lambda name: (
            name == 'exam-builder' or
            name.startswith('exam-builder-') or
            name in ['exam-builder', 'exam-answers']
        ),

        'ib_tutoring': lambda name: (
            name == 'tutoring' or
            name.startswith('tutoring-') or
            name in ['tutoring', 'tutoring-sessions', 'student-admin', 'tutor-admin', 'admin-student-management', 'parent-admin']
        ),

        'admin_panel': lambda name: (
            name == 'admin-panel' or
            name.startswith('admin-panel-') or
            name in ['admin-panel', 'admin-panel-sessions']
        ),
        'student_panel': lambda name: (
            name == 'student-panel' or
            name.startswith('student-panel-') or
            name in ['student-panel', 'student-panel-sessions']
        ),
        'parent_panel': lambda name: (
            name == 'parent-panel' or
            name.startswith('parent-panel-') or
            name in ['parent-panel', 'parent-panel-sessions']
        ),
        'tutor_panel': lambda name: (
            name == 'tutor-panel' or
            name.startswith('tutor-panel-') or
            name in ['tutor-panel', 'tutor-panel-sessions']
        ),

        'past_papers_year': lambda name: (
            'past-papers' in name and 'topics' not in name and 'exam-builder' not in name
        ) or (
            # Pattern for individual past paper pages (e.g., math-ai-sl-may24tz1p1)
            any(subject in name for subject in ['math-ai-sl', 'math-ai-hl', 'math-aa-sl', 'math-aa-hl', 'physics-sl', 'physics-hl', 'comp-sci-sl', 'comp-sci-hl', 'bio-sl', 'bio-hl']) and
            any(month in name for month in ['may', 'nov', 'specimen']) and
            any(indicator in name for indicator in ['tz1', 'tz2', 'tz0', '']) and
            any(paper in name for paper in ['p1', 'p2']) and
            'topics' not in name and 'videos' not in name
        ),
        'past_papers_topics': lambda name: ('past-papers-topics' in name or 'videos' in name) and any(subject in name for subject in ['math-ai-sl', 'math-ai-hl', 'math-aa-sl', 'math-aa-hl', 'comp-sci-sl', 'comp-sci-hl', 'bio-sl', 'bio-hl', 'physics-sl', 'physics-hl']),

        'post_ib_guidance': lambda name: name in ['uni-database', 'suitability-survey', 'uni-docs', 'webinars-live', 'webinars-recorded'],
    }
    
    # Check which section the current URL belongs to
    active_sections = {}
    
    # First check specific patterns
    for section, patterns in menu_sections.items():
        if callable(patterns):
            # Handle function-based patterns
            active_sections[f'is_{section}_active'] = patterns(url_name)
        else:
            # Handle list-based patterns
            active_sections[f'is_{section}_active'] = url_name in patterns
    
    # Then check pattern-based sections
    for section, pattern_func in pattern_sections.items():
        active_sections[f'is_{section}_active'] = pattern_func(url_name)
    
    # Helper function for pattern checking in templates
    def url_matches_pattern(pattern):
        if isinstance(pattern, str):
            return pattern in url_name or url_name.startswith(pattern)
        elif isinstance(pattern, list):
            return url_name in pattern
        return False
    
    # Determine current theme
    host = request.get_host()
    theme_from_url = request.GET.get('theme')
    
    if theme_from_url:
        current_theme = theme_from_url
    elif 'apex' in host:
        current_theme = 'apex'
    elif 'topibtutors' in host:
        current_theme = 'topibtutors'
    elif 'iboost' in host:
        current_theme = 'iboost'
    elif 'example' in host:
        current_theme = 'example'
    else:
        current_theme = getattr(request, 'theme', 'academy')
    
    # Site name based on theme
    site_names = {
        'apex': 'Apex Tuition Australia',
        'topibtutors': 'Top IB Tutors',
        'iboost': 'IBoost',
        'example': 'Your Name',
        'academy': 'Edunade Academy',
    }
    site_name = site_names.get(current_theme, 'Edunade Academy')
    
    return {
        'current_url_name': url_name,
        'url_matches': url_matches_pattern,
        'current_theme': current_theme,
        'site_name': site_name,
        # User session information
        'user_logged_in': request.session.get('already_registered', False),
        'user_first_name': request.session.get('user_name', ''),
        'user_last_name': request.session.get('last_name', ''),
        'user_school_name': request.session.get('school_name', ''),
        'user_curriculum': request.session.get('curriculum', ''),
        'user_student_type': request.session.get('student_type', '') or request.session.get('occupation', ''),
        'user_occupation': request.session.get('occupation', ''),
        'user_exam_session': request.session.get('exam_session', ''),
        'user_email': request.session.get('email', ''),
        'user_avatar': request.session.get('avatar', 'avatar1.png'),
        'user_type': request.session.get('user_type', 'free') if request.session.get('already_registered', False) else 'none',
        'is_apex_user': request.session.get('is_apex_user', False),
        **active_sections
    }