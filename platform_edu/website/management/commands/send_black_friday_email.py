from django.core.management.base import BaseCommand
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings

class Command(BaseCommand):
    help = 'Send Black Friday promotional email to users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            help='Email address to send the promo to (if not specified, uses test email)'
        )
        parser.add_argument(
            '--all-users',
            action='store_true',
            help='Send to all registered users in the database'
        )
        parser.add_argument(
            '--non-premium',
            action='store_true',
            help='Send only to non-premium users'
        )

    def handle(self, *args, **options):
        recipients = []
        
        if options['all_users']:
            from website.models import Users, Premium_Members
            
            if options['non_premium']:
                # Get all users who are not premium
                premium_customer_ids = Premium_Members.objects.filter(subscribed="Yes").values_list('customer_id', flat=True)
                users = Users.objects.exclude(customer_id__in=premium_customer_ids)
                self.stdout.write(f"Preparing to send Black Friday email to {users.count()} non-premium users...")
            else:
                # Get all users
                users = Users.objects.all()
                self.stdout.write(f"Preparing to send Black Friday email to {users.count()} users...")
            
            recipients = [user.email for user in users if user.email]
            
        elif options['email']:
            recipients = [options['email']]
            self.stdout.write(f"Preparing to send Black Friday email to: {options['email']}")
        else:
            # Default test email
            recipients = ['marek.kowalczyk12@vp.pl']
            self.stdout.write(f"Preparing to send test Black Friday email to: marek.kowalczyk12@vp.pl")
        
        if not recipients:
            self.stdout.write(self.style.WARNING('No recipients found!'))
            return
        
        success_count = 0
        error_count = 0
        
        for recipient_email in recipients:
            try:
                # Prepare email context
                context = {
                    'checkout_url': 'https://academy.edunade.com/pricing/',
                }
                
                # Render HTML email template
                email_html_message = render_to_string('email/black_friday_promo.html', context)
                
                # Plain text fallback
                email_text = f"""
Black Friday Sale - Up to 50% OFF

Hello,

This Black Friday, we're offering our biggest discounts of the year on Edunade Academy memberships. Join over 50,000 students preparing for their IB exams with our comprehensive learning platform.

PROMO CODES:
• BLACKFRIDAY30 - 30% OFF Monthly
• BLACKFRIDAY365 - 50% OFF Yearly

Offer expires December 1st, 2025

WHAT'S INCLUDED:
• Unlimited access to thousands of exam-style questions
• Complete past paper solutions with detailed explanations
• Video tutorials for all topics
• Topic-organized questionbanks for Math, Physics, Computer Science, and Biology
• Study tracking and progress monitoring
• Access from any device, anytime

HOW TO REDEEM:
1. Visit: https://academy.edunade.com/subscription/
2. Select your package (Monthly or Yearly)
3. Click "Add promotion code" at checkout
4. Enter your promo code

Best regards,
The Edunade Academy Team

© 2025 Edunade Academy. All rights reserved.
Need help? Contact us at contact@edunade.com
                """
                
                # Create email
                subject = 'BLACK FRIDAY: Save up to 50% on Edunade Academy Premium!'
                from_email = f'Edunade Academy <{settings.DEFAULT_FROM_EMAIL}>'
                
                email = EmailMultiAlternatives(
                    subject=subject,
                    body=email_text,
                    from_email=from_email,
                    to=[recipient_email]
                )
                email.attach_alternative(email_html_message, "text/html")
                
                # Send email
                email.send()
                success_count += 1
                
                self.stdout.write(self.style.SUCCESS(f'✅ Sent to {recipient_email}'))
                
            except Exception as e:
                error_count += 1
                self.stdout.write(self.style.ERROR(f'❌ Failed to send to {recipient_email}: {str(e)}'))
        
        # Summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS(f'✅ Successfully sent: {success_count}'))
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f'❌ Failed: {error_count}'))
        self.stdout.write('\nPromo Codes:')
        self.stdout.write('  📅 Monthly: BLACKFRIDAY30 (30% OFF)')
        self.stdout.write('  🎓 Yearly: BLACKFRIDAY365 (50% OFF)')
        self.stdout.write('  ⏰ Valid until: December 1st, 2025')
        self.stdout.write('='*60)

