import getpass

from django.core.management.base import BaseCommand, CommandError

from pTracker.dataaccess.platform_access.platform_user_models import PlatformUser


class Command(BaseCommand):
    help = 'Create a SaaS platform user (operator account, separate from employee logins)'

    def add_arguments(self, parser):
        parser.add_argument('--email', required=True)
        parser.add_argument('--full-name', default='')

    def handle(self, *args, **options):
        email = options['email']
        if PlatformUser.objects.filter(email__iexact=email).exists():
            raise CommandError('A platform user with this email already exists')

        password = getpass.getpass('Password: ')
        confirm = getpass.getpass('Password (again): ')
        if password != confirm:
            raise CommandError('Passwords did not match')

        PlatformUser.objects.create_superuser(
            email=email,
            password=password,
            full_name=options['full_name'],
        )
        self.stdout.write(self.style.SUCCESS(f'Platform user "{email}" created'))
