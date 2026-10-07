from django.core.management.base import BaseCommand

from pTracker.dataaccess.platform_access.tenancy_models import Tenant
from pTracker.dataaccess.platform_access.tenancy_models import Company

# Mirrors settings.COMPANY / settings.ORGANIZATION (pTracker/settings/constants.py)
LEGACY_COMPANIES = [
    (2, 'DigitalMesh'),
    (3, 'EM Softtech'),
]


class Command(BaseCommand):
    help = ('One-off bridge: create a Tenant + Company row for each of the two real, '
            'pre-existing companies (today\'s settings.COMPANY[\'DM\']/[\'EM\'] int ids), '
            'so employee Memberships have something real to attach to during the '
            'module-by-module rollout. Safe to re-run - idempotent per legacy id.')

    def add_arguments(self, parser):
        parser.add_argument('--tenant-slug', default='digitalmesh-group')
        parser.add_argument('--tenant-name', default='DigitalMesh Group')

    def handle(self, *args, **options):
        tenant, created = Tenant.objects.get_or_create(
            slug=options['tenant_slug'],
            defaults={'name': options['tenant_name'], 'status': Tenant.STATUS_ACTIVE},
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created tenant "{tenant.slug}"'))
        else:
            self.stdout.write(f'Using existing tenant "{tenant.slug}"')

        for legacy_id, legal_name in LEGACY_COMPANIES:
            company, created = Company.objects.get_or_create(
                legacy_company_id=legacy_id,
                defaults={
                    'tenant': tenant,
                    'legal_name': legal_name,
                    'short_name': legal_name,
                },
            )
            status = 'created' if created else 'already exists'
            self.stdout.write(f'Company legacy_company_id={legacy_id} ({legal_name}): {status} (id={company.id})')
