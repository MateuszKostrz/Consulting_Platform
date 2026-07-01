from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0017_personalprofile_school_address_profile_photo'),
    ]

    operations = [
        migrations.CreateModel(
            name='ReferenceContact',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sort_order', models.PositiveSmallIntegerField(default=1)),
                ('name', models.CharField(blank=True, default='', max_length=150)),
                ('position', models.CharField(blank=True, default='', max_length=150)),
                ('email', models.EmailField(blank=True, default='', max_length=254)),
                ('institution', models.CharField(blank=True, default='', max_length=200)),
                ('phone', models.CharField(blank=True, default='', max_length=30)),
                ('relation_to_student', models.CharField(blank=True, default='', max_length=150)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('academic_profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reference_contacts', to='portal.academicprofile')),
            ],
            options={
                'verbose_name': 'Reference Contact',
                'verbose_name_plural': 'Reference Contacts',
                'ordering': ['sort_order'],
            },
        ),
        migrations.AddConstraint(
            model_name='referencecontact',
            constraint=models.UniqueConstraint(fields=('academic_profile', 'sort_order'), name='unique_reference_contact_order_per_profile'),
        ),
    ]
