from django.core.management.base import BaseCommand

from pTracker.common.confidential_storage import CompanyFileStorage
from pTracker.common.confidential_storage import StorageError
from pTracker.dataaccess.platform_access.document_da import CompanyDocumentDA
from pTracker.dataaccess.platform_access.tenancy_models import Company


class Command(BaseCommand):
    help = ('Reconcile company confidential storage with platform_company_document: removes '
            'temporary files left by interrupted uploads and reports (or with --delete-orphans '
            'removes) stored files that no document row references, and rows whose file is '
            'missing. Each company is checked only against its own directory and rows.')

    def add_arguments(self, parser):
        parser.add_argument('--delete-orphans', action='store_true',
                            help='Delete unreferenced files (default: report only)')
        parser.add_argument('--partial-age', type=int, default=3600,
                            help='Seconds before an unfinished upload file counts as stale (default 3600)')

    def handle(self, *args, **options):
        storage = CompanyFileStorage()
        da = CompanyDocumentDA()
        for company in Company.objects.order_by('id').only('id', 'uuid', 'short_name'):
            label = f'company {company.id} ({company.short_name})'
            try:
                removed = storage.remove_stale_partials(company.uuid, options['partial_age'])
                on_disk = storage.list_keys(company.uuid)
            except StorageError as error:
                self.stderr.write(f'{label}: skipped - {error}')
                continue

            recorded = da.get_storage_keys(company.id)
            orphans = sorted(on_disk - recorded)
            missing = sorted(recorded - on_disk)

            if removed:
                self.stdout.write(f'{label}: removed {removed} stale partial upload(s)')
            for key in orphans:
                if options['delete_orphans']:
                    storage.delete(company.uuid, key)
                    self.stdout.write(f'{label}: deleted orphan {key}')
                else:
                    self.stdout.write(f'{label}: orphan {key} (use --delete-orphans to remove)')
            for key in missing:
                self.stdout.write(self.style.WARNING(f'{label}: document row without file {key}'))
        self.stdout.write(self.style.SUCCESS('Done'))
