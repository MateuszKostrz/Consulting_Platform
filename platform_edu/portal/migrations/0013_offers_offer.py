from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0012_interviewpreparation_interviewprepsession'),
    ]

    operations = [
        migrations.CreateModel(
            name='Offers',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_unlocked', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('personal_profile', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='offers_access',
                    to='portal.personalprofile',
                )),
            ],
            options={
                'verbose_name': 'Offers',
                'verbose_name_plural': 'Offers',
            },
        ),
        migrations.CreateModel(
            name='Offer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('university_name', models.CharField(max_length=200)),
                ('degree_name', models.CharField(max_length=200)),
                ('offer_requirements', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('personal_profile', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='offers',
                    to='portal.personalprofile',
                )),
            ],
            options={
                'verbose_name': 'Offer',
                'verbose_name_plural': 'Offers',
                'ordering': ['university_name', 'degree_name', 'id'],
            },
        ),
    ]
