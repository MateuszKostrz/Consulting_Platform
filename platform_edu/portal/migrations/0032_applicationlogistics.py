from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0031_personalprofile_second_parent_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='ApplicationLogistics',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_unlocked', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('personal_profile', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='application_logistics',
                    to='portal.personalprofile',
                )),
            ],
            options={
                'verbose_name': 'Application Logistics',
                'verbose_name_plural': 'Application Logistics',
            },
        ),
        migrations.CreateModel(
            name='ApplicationLogisticsPortal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('portal_name', models.CharField(max_length=200)),
                ('portal_link', models.URLField(blank=True, default='', max_length=500)),
                ('username', models.CharField(blank=True, default='', max_length=200)),
                ('password', models.CharField(blank=True, default='', max_length=200)),
                ('comments', models.TextField(blank=True, default='')),
                ('sort_order', models.PositiveSmallIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('personal_profile', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='application_logistics_portals',
                    to='portal.personalprofile',
                )),
            ],
            options={
                'verbose_name': 'Application Logistics Portal',
                'verbose_name_plural': 'Application Logistics Portals',
                'ordering': ['sort_order', 'id'],
            },
        ),
        migrations.AddField(
            model_name='studentsectionaccess',
            name='application_logistics',
            field=models.BooleanField(blank=True, null=True),
        ),
    ]
