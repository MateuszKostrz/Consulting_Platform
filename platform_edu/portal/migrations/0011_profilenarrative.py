from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0010_strategicapplication_universitychoice'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProfileNarrative',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_unlocked', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('personal_profile', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='profile_narrative',
                    to='portal.personalprofile',
                )),
            ],
            options={
                'verbose_name': 'Profile Narrative',
                'verbose_name_plural': 'Profile Narratives',
            },
        ),
    ]
