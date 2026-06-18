from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0011_profilenarrative'),
    ]

    operations = [
        migrations.CreateModel(
            name='InterviewPreparation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_unlocked', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('personal_profile', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='interview_preparation',
                    to='portal.personalprofile',
                )),
            ],
            options={
                'verbose_name': 'Interview Preparation',
                'verbose_name_plural': 'Interview Preparations',
            },
        ),
        migrations.CreateModel(
            name='InterviewPrepSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slot', models.PositiveSmallIntegerField()),
                ('meeting_link', models.URLField(blank=True, default='', max_length=500)),
                ('feedback_file', models.FileField(blank=True, null=True, upload_to='interview_prep/feedback/')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('personal_profile', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='interview_prep_sessions',
                    to='portal.personalprofile',
                )),
            ],
            options={
                'verbose_name': 'Interview Prep Session',
                'verbose_name_plural': 'Interview Prep Sessions',
                'ordering': ['slot'],
            },
        ),
        migrations.AddConstraint(
            model_name='interviewprepsession',
            constraint=models.UniqueConstraint(
                fields=('personal_profile', 'slot'),
                name='unique_interview_prep_session_per_profile',
            ),
        ),
    ]
