"""
Management command: seed_revision_skills

Creates / updates revision skill taxonomies for Math AI SL (Number & Algebra,
Geometry & Trigonometry, etc.).
Safe to run multiple times — uses get_or_create / update_or_create throughout.

Usage:
    python manage.py seed_revision_skills
"""

from django.core.management.base import BaseCommand
from website.models import RevisionChapter, RevisionTopic, RevisionSkill

TAXONOMIES = [
    {
        'chapter': {
            'slug':         'number_algebra',
            'display_name': 'Number & Algebra',
            'subject':      'Math AI SL',
            'order':        1,
        },
        'topics': [
            {
                'slug':         'number_skills',
                'display_name': 'Number Skills',
                'order':        1,
                'skills': [
                    {'slug': 'scientific_notation',     'display_name': 'Scientific Notation',          'order': 1},
                    {'slug': 'significant_figures',     'display_name': 'Significant Figures',          'order': 2},
                    {'slug': 'percentage_error',        'display_name': 'Percentage Error',             'order': 3},
                    {'slug': 'bounds_and_error_intervals','display_name': 'Bounds & Error Intervals',   'order': 4},
                ],
            },
            {
                'slug':         'sequences_series_financial',
                'display_name': 'Sequences, Series & Financial Mathematics',
                'order':        2,
                'skills': [
                    {'slug': 'arithmetic_sequences', 'display_name': 'Arithmetic Sequences & Series',  'order': 1},
                    {'slug': 'geometric_sequences',  'display_name': 'Geometric Sequences & Series',   'order': 2},
                    {'slug': 'sigma_notation',       'display_name': 'Sigma Notation',                 'order': 3},
                    {'slug': 'financial_math',       'display_name': 'Financial Mathematics',          'order': 4},
                ],
            },
            {
                'slug':         'systems_linear_equations',
                'display_name': 'Systems of Linear Equations',
                'order':        3,
                'skills': [
                    {'slug': 'solving_linear_systems', 'display_name': 'Solving Systems of Linear Equations', 'order': 1},
                ],
            },
        ],
    },
    {
        'chapter': {
            'slug':         'geometry_trigonometry',
            'display_name': 'Geometry & Trigonometry',
            'subject':      'Math AI SL',
            'order':        2,
        },
        'topics': [
            {
                'slug':         'trigonometry',
                'display_name': 'Trigonometry',
                'order':        1,
                'skills': [
                    {
                        'slug':         'basic_trigonometric_rules',
                        'display_name': 'Basic Trigonometric Rules',
                        'order':        1,
                    },
                ],
            },
        ],
    },
    {
        'chapter': {
            'slug':         'statistics_probability',
            'display_name': 'Statistics & Probability',
            'subject':      'Math AI SL',
            'order':        3,
        },
        'topics': [
            {
                'slug':         'descriptive_statistics',
                'display_name': 'Descriptive Statistics',
                'order':        1,
                'skills': [
                    {'slug': 'summary_statistics',   'display_name': 'Summary Statistics',   'order': 1},
                    {'slug': 'cumulative_frequency', 'display_name': 'Cumulative Frequency', 'order': 2},
                    {'slug': 'box_plots',            'display_name': 'Box Plots',           'order': 3},
                    {'slug': 'sampling_methods',   'display_name': 'Sampling Methods',     'order': 4},
                    {'slug': 'outliers',             'display_name': 'Outliers',             'order': 5},
                    {'slug': 'frequency_tables',     'display_name': 'Frequency Tables',     'order': 6},
                    {'slug': 'interquartile_range',  'display_name': 'Interquartile Range',  'order': 7},
                ],
            },
            {
                'slug':         'bivariate_statistics',
                'display_name': 'Bivariate Statistics',
                'order':        2,
                'skills': [
                    {'slug': 'pearson_correlation',  'display_name': "Pearson's Correlation",  'order': 1},
                    {'slug': 'spearman_correlation', 'display_name': "Spearman's Correlation", 'order': 2},
                    {'slug': 'regression_lines',     'display_name': 'Regression Lines',       'order': 3},
                ],
            },
            {
                'slug':         'probability',
                'display_name': 'Probability',
                'order':        3,
                'skills': [
                    {'slug': 'tree_diagrams',            'display_name': 'Tree Diagrams',            'order': 1},
                    {'slug': 'venn_diagrams',            'display_name': 'Venn Diagrams',            'order': 2},
                    {'slug': 'conditional_probability',  'display_name': 'Conditional Probability',  'order': 3},
                    {'slug': 'probability_distributions','display_name': 'Probability Distributions',  'order': 4},
                    {'slug': 'expected_value',           'display_name': 'Expected Value',           'order': 5},
                ],
            },
            {
                'slug':         'distributions',
                'display_name': 'Distributions',
                'order':        4,
                'skills': [
                    {'slug': 'normal_distribution',         'display_name': 'Normal Distribution',          'order': 1},
                    {'slug': 'inverse_normal_distribution', 'display_name': 'Inverse Normal Distribution',  'order': 2},
                    {'slug': 'binomial_distribution',       'display_name': 'Binomial Distribution',        'order': 3},
                    {'slug': 'expected_value_variance',     'display_name': 'Expected Value & Variance',    'order': 4},
                ],
            },
            {
                'slug':         'hypothesis_testing',
                'display_name': 'Hypothesis Testing',
                'order':        5,
                'skills': [
                    {'slug': 'one_sample_t_test',           'display_name': 'One-Sample t-Test',                'order': 1},
                    {'slug': 'two_sample_t_test',           'display_name': 'Two-Sample t-Test',                'order': 2},
                    {'slug': 'chi_squared_goodness_of_fit', 'display_name': 'Chi-Squared Goodness of Fit',      'order': 3},
                    {'slug': 'chi_squared_independence',    'display_name': 'Chi-Squared Test of Independence', 'order': 4},
                ],
            },
        ],
    },
]


class Command(BaseCommand):
    help = 'Seed / update revision skill taxonomy for Math AI SL Revision Engine'

    def handle(self, *args, **options):
        total_new_skills = 0
        for taxonomy in TAXONOMIES:
            new_skills = self._seed_taxonomy(taxonomy)
            total_new_skills += new_skills

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'Done. Created {total_new_skills} new skills across {len(TAXONOMIES)} chapter(s).'
        ))

    def _seed_taxonomy(self, taxonomy):
        chapter_data = taxonomy['chapter']
        chapter, created = RevisionChapter.objects.get_or_create(
            slug=chapter_data['slug'],
            defaults={
                'display_name': chapter_data['display_name'],
                'subject':      chapter_data['subject'],
                'order':        chapter_data['order'],
            }
        )
        self.stdout.write(
            self.style.SUCCESS(f'Created chapter: {chapter}') if created
            else f'Chapter exists: {chapter}'
        )

        new_skills = 0
        for topic_data in taxonomy['topics']:
            topic, t_created = RevisionTopic.objects.get_or_create(
                slug=topic_data['slug'],
                defaults={
                    'chapter':      chapter,
                    'display_name': topic_data['display_name'],
                    'order':        topic_data['order'],
                }
            )
            if not t_created:
                # Keep chapter / display_name / order in sync with taxonomy seed
                RevisionTopic.objects.filter(pk=topic.pk).update(
                    chapter_id=chapter.pk,
                    display_name=topic_data['display_name'],
                    order=topic_data['order'],
                )
            self.stdout.write(
                self.style.SUCCESS(f'  Created topic: {topic.display_name}') if t_created
                else f'  Topic exists:  {topic.display_name}'
            )

            for skill_data in topic_data['skills']:
                skill, s_created = RevisionSkill.objects.get_or_create(
                    slug=skill_data['slug'],
                    defaults={
                        'topic':        topic,
                        'display_name': skill_data['display_name'],
                        'order':        skill_data['order'],
                    }
                )
                if not s_created:
                    RevisionSkill.objects.filter(pk=skill.pk).update(
                        display_name=skill_data['display_name'],
                        order=skill_data['order'],
                        topic=topic,
                    )
                status = 'Created' if s_created else 'Exists '
                self.stdout.write(f'    {status}: {skill.slug}')
                if s_created:
                    new_skills += 1

        self.stdout.write('')
        return new_skills
