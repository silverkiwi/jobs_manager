from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings

class Command(BaseCommand):
    help = 'Test email configuration by sending a test email'

    def add_arguments(self, parser):
        parser.add_argument('recipient_email', type=str, help='Email address to send the test email to')

    def handle(self, *args, **options):
        recipient = options['recipient_email']
        
        try:
            send_mail(
                subject='Test Email from Jobs Manager',
                message='This is a test email to verify the email configuration is working correctly.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                fail_silently=False,
            )
            self.stdout.write(self.style.SUCCESS(f'Test email sent successfully to {recipient}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to send email: {str(e)}'))
