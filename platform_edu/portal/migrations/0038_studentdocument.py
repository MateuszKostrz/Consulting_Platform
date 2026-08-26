from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0037_backfill_personal_email_from_login'),
    ]

    operations = [
        migrations.CreateModel(
            name='StudentDocument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('document_type', models.CharField(
                    choices=[
                        ('passport', 'Passport'),
                        ('id', 'ID'),
                        ('cv', 'CV'),
                        ('transcript', 'Transcript'),
                        ('language_certificate', 'Language certificate'),
                        ('personal_statement', 'Personal statement'),
                        ('other', 'Other'),
                    ],
                    max_length=40,
                )),
                ('document_file', models.FileField(upload_to='home/documents/')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('student', models.ForeignKey(
                    limit_choices_to={'role': 'student'},
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='home_documents',
                    to='portal.platformuser',
                )),
                ('uploaded_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='uploaded_home_documents',
                    to='portal.platformuser',
                )),
            ],
            options={
                'verbose_name': 'Student document',
                'verbose_name_plural': 'Student documents',
                'ordering': ['-created_at', 'document_type'],
            },
        ),
    ]
