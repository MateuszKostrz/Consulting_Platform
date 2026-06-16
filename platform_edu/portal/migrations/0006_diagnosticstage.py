from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0005_link_student_profiles_to_platform_users'),
    ]

    operations = [
        migrations.CreateModel(
            name='DiagnosticStage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('stage_key', models.CharField(
                    choices=[
                        ('readiness', 'Readiness & Profile Assessment'),
                        ('homework', 'Profile Self-Assessment (Homework)'),
                        ('test', 'Diagnostic Test'),
                        ('report', 'Diagnostics Report'),
                    ],
                    max_length=32,
                )),
                ('sort_order', models.PositiveSmallIntegerField(default=1)),
                ('template_file', models.FileField(blank=True, null=True, upload_to='diagnostics/templates/')),
                ('student_submission', models.FileField(blank=True, null=True, upload_to='diagnostics/student/')),
                ('admin_document', models.FileField(blank=True, null=True, upload_to='diagnostics/admin/')),
                ('student_submitted_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('personal_profile', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='diagnostic_stages',
                    to='portal.personalprofile',
                )),
            ],
            options={
                'verbose_name': 'Diagnostic Stage',
                'verbose_name_plural': 'Diagnostic Stages',
                'ordering': ['sort_order', 'stage_key'],
            },
        ),
        migrations.AddConstraint(
            model_name='diagnosticstage',
            constraint=models.UniqueConstraint(
                fields=('personal_profile', 'stage_key'),
                name='unique_diagnostic_stage_per_profile',
            ),
        ),
    ]
