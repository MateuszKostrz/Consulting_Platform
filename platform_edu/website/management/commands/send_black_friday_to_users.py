from django.core.management.base import BaseCommand
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
import openpyxl
import os

class Command(BaseCommand):
    help = 'Send Black Friday promotional email to users from Excel file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='static/website/css/website_users.xlsx',
            help='Path to Excel file with user emails'
        )
        parser.add_argument(
            '--test',
            action='store_true',
            help='Test mode - only show emails without sending'
        )

    def handle(self, *args, **options):
        file_path = options['file']
        test_mode = options['test']
        
        # Emails to EXCLUDE (internal/test emails - will not send to these)
        exclude_emails = [
            # Add any emails you want to exclude here
        ]
        
        # Build full path
        if not os.path.isabs(file_path):
            base_dir = settings.BASE_DIR
            full_path = os.path.join(base_dir, file_path)
        else:
            full_path = file_path
        
        self.stdout.write(f"Loading emails from: {full_path}")
        
        try:
            # Read Excel file using openpyxl
            workbook = openpyxl.load_workbook(full_path, read_only=True)
            sheet = workbook.active
            
            # Try to find the email column by checking first few rows
            email_col_index = None
            header_row = None
            
            # Check first 5 rows to find 'email' header
            for row_num in range(1, 6):
                row_values = [cell.value for cell in sheet[row_num]]
                if 'email' in [str(v).lower() if v else '' for v in row_values]:
                    # Found the header row
                    header_row = row_num
                    for i, val in enumerate(row_values):
                        if val and str(val).lower() == 'email':
                            email_col_index = i
                            break
                    break
            
            if email_col_index is None:
                self.stdout.write(self.style.ERROR(f"Column 'email' not found in first 5 rows."))
                self.stdout.write(f"First row: {[cell.value for cell in sheet[1]]}")
                workbook.close()
                return
            
            self.stdout.write(f"Found 'email' column at index {email_col_index}, header row {header_row}")
            
            # Get all emails (starting from row after header)
            all_emails = []
            for row in sheet.iter_rows(min_row=header_row + 1, values_only=True):
                if len(row) > email_col_index:
                    email = row[email_col_index]
                    if email and isinstance(email, str) and '@' in email:
                        all_emails.append(email.strip().lower())
            
            # Remove duplicates
            all_emails = list(set(all_emails))
            workbook.close()
            
            # Filter out excluded emails
            filtered_emails = [
                email for email in all_emails 
                if email.lower() not in [e.lower() for e in exclude_emails]
            ]
            
            self.stdout.write(f"\nTotal emails in file: {len(all_emails)}")
            self.stdout.write(f"Excluded emails: {len(exclude_emails)}")
            self.stdout.write(f"Emails to send to: {len(filtered_emails)}\n")
            
            if test_mode:
                self.stdout.write(self.style.WARNING("\n🧪 TEST MODE - No emails will be sent\n"))
                
                if exclude_emails:
                    self.stdout.write(f"\nExcluded emails ({len(exclude_emails)}):")
                    for email in exclude_emails:
                        self.stdout.write(f"  ❌ {email}")
                
                self.stdout.write(f"\nEmails that would be sent to ({len(filtered_emails)}):")
                # Show first 20 emails as preview
                for i, email in enumerate(filtered_emails[:20], 1):
                    self.stdout.write(f"  ✅ {i}. {email}")
                if len(filtered_emails) > 20:
                    self.stdout.write(f"  ... and {len(filtered_emails) - 20} more")
                return
            
            # Send emails
            success_count = 0
            error_count = 0
            
            self.stdout.write(self.style.WARNING("\n📧 Sending emails...\n"))
            
            for i, recipient_email in enumerate(filtered_emails, 1):
                try:
                    # Show progress
                    self.stdout.write(f"Sending email to {recipient_email}...")
                    
                    # Prepare email context
                    context = {
                        'checkout_url': 'https://academy.edunade.com/pricing/',
                    }
                    
                    # Render HTML email template
                    email_html_message = render_to_string('email/black_friday_promo.html', context)
                    
                    # Plain text fallback
                    email_text = """
Black Friday Sale - Up to 50% OFF

Hello,

This Black Friday, we're offering our biggest discounts of the year on Edunade Academy memberships. Join over 50,000 students preparing for their IB exams with our comprehensive learning platform.

PROMO CODES:
• BLACKFRIDAY30 - 30% OFF Monthly
• BLACKFRIDAY365 - 50% OFF Yearly

Offer expires December 5th, 2025

WHAT'S INCLUDED:
• Unlimited access to thousands of exam-style questions
• Complete past paper solutions with detailed explanations
• Video tutorials for all topics
• Topic-organized questionbanks for Math, Physics, Computer Science, and Biology
• Study tracking and progress monitoring
• Access from any device, anytime

HOW TO REDEEM:
1. Visit: https://academy.edunade.com/pricing/
2. Select your package (Monthly or Yearly)
3. Click "Add promotion code" at checkout
4. Enter your promo code

Best regards,
The Edunade Academy Team

© 2025 Edunade Academy. All rights reserved.
Need help? Contact us at contact@edunade.com
                    """
                    
                    # Create email
                    subject = '🎉 BLACK FRIDAY: Save up to 50% on Edunade Academy Premium!'
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
                    self.stdout.write(self.style.SUCCESS(f"  ✅ Sent successfully to {recipient_email}"))
                    
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
            self.stdout.write('  ⏰ Valid until: December 5th, 2025')
            self.stdout.write('='*60)
            
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'File not found: {full_path}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error reading file: {str(e)}'))
            raise e

