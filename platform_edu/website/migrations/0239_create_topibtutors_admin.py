from django.db import migrations
from django.contrib.auth.hashers import make_password
import random
import string


def create_topibtutors_admin(apps, schema_editor):
    """Create AdminExternal user for Top IB Tutors"""
    ApexUsers = apps.get_model('website', 'ApexUsers')
    User = apps.get_model('auth', 'User')
    Premium_Members = apps.get_model('website', 'Premium_Members')
    
    # Delete all old users first
    old_emails = ['help@topibtutors.com', 'info@topibtutors.com', 'max@topibtutors.com']
    
    for old_email in old_emails:
        if ApexUsers.objects.filter(email=old_email).exists():
            apex_user = ApexUsers.objects.get(email=old_email)
            Premium_Members.objects.filter(customer_id=apex_user.customer_id).delete()
            apex_user.delete()
            print(f"Deleted existing ApexUsers entry for {old_email}")
        
        if User.objects.filter(username=old_email).exists():
            User.objects.filter(username=old_email).delete()
            print(f"Deleted existing Django User for {old_email}")
    
    # Set new email
    email = 'info@topibtutors.com'
    
    # Generate unique customer_id
    customer_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    while ApexUsers.objects.filter(customer_id=customer_id).exists():
        customer_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    
    # Create Django User for authentication
    django_user = User.objects.create(
        username=email,
        email=email,
        first_name='Max',
        last_name='Milstein',
        password=make_password('Apex2026!'),
        is_active=True,
    )
    
    # Create ApexUsers entry
    apex_user = ApexUsers.objects.create(
        first_name='Max',
        last_name='Milstein',
        email=email,
        password='N/A',
        curriculum='IBDP',
        occupation='AdminExternal',
        exam_session='M25',
        customer_id=customer_id,
        school_name='Top IB Tutors',
        avatar='avatar1.png',
        verified=True,
        confirmed_teacher=True,
        source_domain='topibtutors',
    )
    
    # Add premium membership for 1 year
    from datetime import datetime, timedelta
    from django.utils import timezone
    
    Premium_Members.objects.create(
        customer_id=customer_id,
        subscription_type='apex_teacher',
        subscribed='Yes',
        subscription_end_date=timezone.now() + timedelta(days=365),
    )
    
    print(f"Created new AdminExternal user: Max Milstein ({email})")


def reverse_create_topibtutors_admin(apps, schema_editor):
    """Remove the TopIBTutors admin user"""
    ApexUsers = apps.get_model('website', 'ApexUsers')
    User = apps.get_model('auth', 'User')
    Premium_Members = apps.get_model('website', 'Premium_Members')
    
    email = 'info@topibtutors.com'
    
    try:
        apex_user = ApexUsers.objects.get(email=email)
        Premium_Members.objects.filter(customer_id=apex_user.customer_id).delete()
        apex_user.delete()
    except ApexUsers.DoesNotExist:
        pass
    
    User.objects.filter(username=email).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0238_add_source_domain_to_apexusers'),
    ]

    operations = [
        migrations.RunPython(create_topibtutors_admin, reverse_create_topibtutors_admin),
    ]
