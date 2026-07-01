from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0018_referencecontact'),
    ]

    operations = [
        migrations.CreateModel(
            name='AcademicActivityEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('category', models.CharField(choices=[('test', 'Standardised Test'), ('extracurricular', 'Extracurricular Activity'), ('award', 'Award / Competition')], max_length=20)),
                ('sort_order', models.PositiveSmallIntegerField(default=1)),
                ('name', models.CharField(blank=True, default='', max_length=200)),
                ('date', models.CharField(blank=True, default='', max_length=100)),
                ('location', models.CharField(blank=True, default='', max_length=200)),
                ('description', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('academic_profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='activity_entries', to='portal.academicprofile')),
            ],
            options={
                'verbose_name': 'Academic Activity Entry',
                'verbose_name_plural': 'Academic Activity Entries',
                'ordering': ['category', 'sort_order'],
            },
        ),
    ]
