from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0029_offer_attachment_file'),
    ]

    operations = [
        migrations.CreateModel(
            name='Results',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_unlocked', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('personal_profile', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='results_access',
                    to='portal.personalprofile',
                )),
            ],
            options={
                'verbose_name': 'Results',
                'verbose_name_plural': 'Results',
            },
        ),
        migrations.CreateModel(
            name='ResultDocument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('document_type', models.CharField(max_length=50)),
                ('document_file', models.FileField(upload_to='results/documents/')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('personal_profile', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='result_documents',
                    to='portal.personalprofile',
                )),
            ],
            options={
                'verbose_name': 'Result Document',
                'verbose_name_plural': 'Result Documents',
                'ordering': ['-created_at', 'id'],
            },
        ),
        migrations.AddField(
            model_name='studentsectionaccess',
            name='results',
            field=models.BooleanField(blank=True, null=True),
        ),
    ]
