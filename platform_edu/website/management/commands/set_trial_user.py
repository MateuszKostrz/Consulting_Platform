from django.core.management.base import BaseCommand
from website.models import Premium_Members

class Command(BaseCommand):
    help = 'Set specific user to free trial subscription type'

    def handle(self, *args, **options):
        email = 'krzysztof.zgoda23@op.pl'
        
        try:
            premium_member = Premium_Members.objects.get(email=email)
            premium_member.subscription_type = 'free_trial'
            premium_member.save()
            
            self.stdout.write(self.style.SUCCESS(
                f'✓ Successfully set {email} to free_trial subscription type'
            ))
            self.stdout.write(f'  Customer ID: {premium_member.customer_id}')
            self.stdout.write(f'  Subscription end: {premium_member.subscription_end_date}')
            
        except Premium_Members.DoesNotExist:
            self.stdout.write(self.style.ERROR(
                f'✗ No premium member found with email: {email}'
            ))

