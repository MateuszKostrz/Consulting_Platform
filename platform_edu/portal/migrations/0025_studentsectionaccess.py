from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0024_personalprofile_curriculum_other'),
    ]

    operations = [
        migrations.CreateModel(
            name='StudentSectionAccess',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('personal_information', models.BooleanField(blank=True, null=True)),
                ('academic_profile', models.BooleanField(blank=True, null=True)),
                ('diagnostics', models.BooleanField(blank=True, null=True)),
                ('portfolio_design', models.BooleanField(blank=True, null=True)),
                ('strategic_application', models.BooleanField(blank=True, null=True)),
                ('profile_narrative', models.BooleanField(blank=True, null=True)),
                ('interview_preparation', models.BooleanField(blank=True, null=True)),
                ('offers', models.BooleanField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('platform_user', models.OneToOneField(limit_choices_to={'role': 'student'}, on_delete=django.db.models.deletion.CASCADE, related_name='section_access', to='portal.platformuser')),
            ],
            options={
                'verbose_name': 'Student Section Access',
                'verbose_name_plural': 'Student Section Access',
            },
        ),
    ]
