from django.core.management.base import BaseCommand
from website.models import Premium_Members, Users


class Command(BaseCommand):
    help = 'Fill in missing names and emails in Premium_Members from Users table'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        # Get all premium members
        premium_members = Premium_Members.objects.all()
        
        updated_count = 0
        not_found_count = 0
        
        self.stdout.write(f'Processing {premium_members.count()} premium members...')
        
        for member in premium_members:
            try:
                # Try to find the user by customer_id
                user = Users.objects.get(customer_id=member.customer_id)
                
                # Update the premium member with user data
                if not dry_run:
                    member.first_name = user.first_name
                    member.last_name = user.last_name
                    member.email = user.email
                    member.save()
                
                self.stdout.write(
                    f'✓ Updated {member.customer_id}: {user.first_name} {user.last_name} ({user.email})'
                )
                updated_count += 1
                
            except Users.DoesNotExist:
                # User not found, fill with "None"
                if not dry_run:
                    member.first_name = "None"
                    member.last_name = "None"
                    member.email = "None"
                    member.save()
                
                self.stdout.write(
                    self.style.WARNING(f'⚠ User not found for customer_id {member.customer_id} - filled with "None"')
                )
                not_found_count += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'✗ Error processing customer_id {member.customer_id}: {str(e)}')
                )
        
        # Summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write('SUMMARY:')
        self.stdout.write(f'Total premium members processed: {premium_members.count()}')
        self.stdout.write(f'Successfully updated: {updated_count}')
        self.stdout.write(f'Not found (filled with "None"): {not_found_count}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\nThis was a DRY RUN - no changes were made'))
            self.stdout.write('Run without --dry-run to apply changes')
        else:
            self.stdout.write(self.style.SUCCESS('\n✓ All premium members have been updated!'))

