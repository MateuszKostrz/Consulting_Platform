from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0008_platformuser_registration_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='PortfolioDesign',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('google_doc_url', models.URLField(blank=True, default='', max_length=500)),
                ('is_unlocked', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('personal_profile', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='portfolio_design',
                    to='portal.personalprofile',
                )),
            ],
            options={
                'verbose_name': 'Portfolio Design',
                'verbose_name_plural': 'Portfolio Designs',
            },
        ),
    ]
