from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0009_portfoliodesign'),
    ]

    operations = [
        migrations.CreateModel(
            name='StrategicApplication',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_unlocked', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('personal_profile', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='strategic_application',
                    to='portal.personalprofile',
                )),
            ],
            options={
                'verbose_name': 'Strategic Application',
                'verbose_name_plural': 'Strategic Applications',
            },
        ),
        migrations.CreateModel(
            name='UniversityChoice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('university_name', models.CharField(max_length=200)),
                ('degree', models.CharField(max_length=200)),
                ('riskiness', models.CharField(
                    choices=[
                        ('very_risky', 'Very risky'),
                        ('risky', 'Risky'),
                        ('realistic', 'Realistic'),
                        ('safe', 'Safe'),
                        ('very_safe', 'Very safe'),
                    ],
                    default='realistic',
                    max_length=20,
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('personal_profile', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='university_choices',
                    to='portal.personalprofile',
                )),
            ],
            options={
                'verbose_name': 'University Choice',
                'verbose_name_plural': 'University Choices',
                'ordering': ['university_name', 'degree', 'id'],
            },
        ),
    ]
