from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0032_applicationlogistics'),
    ]

    operations = [
        migrations.CreateModel(
            name='PortfolioDesignElement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('row_type', models.CharField(
                    choices=[('university', 'University'), ('additional', 'Additional element')],
                    default='university',
                    max_length=20,
                )),
                ('title', models.CharField(max_length=200)),
                ('country', models.CharField(blank=True, default='', max_length=100)),
                ('detail', models.CharField(blank=True, default='', max_length=200)),
                ('status_color', models.CharField(
                    blank=True,
                    choices=[('', 'None'), ('red', 'Red'), ('yellow', 'Yellow'), ('green', 'Green')],
                    default='',
                    max_length=10,
                )),
                ('comment', models.TextField(blank=True, default='')),
                ('sort_order', models.PositiveSmallIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('personal_profile', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='portfolio_design_elements',
                    to='portal.personalprofile',
                )),
            ],
            options={
                'verbose_name': 'Portfolio Design Element',
                'verbose_name_plural': 'Portfolio Design Elements',
                'ordering': ['sort_order', 'id'],
            },
        ),
    ]
