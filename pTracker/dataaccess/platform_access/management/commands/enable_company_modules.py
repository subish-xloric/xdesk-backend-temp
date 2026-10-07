from django.core.management.base import BaseCommand, CommandError

from pTracker.api.platform.module_biz import ModuleBL


class Command(BaseCommand):
    help = ('Set the exact list of product modules enabled for a company. Uses the same '
            'validation as the platform API (unknown codes and missing dependencies are rejected). '
            'A company with no modules enabled is blocked from every gated module.')

    def add_arguments(self, parser):
        parser.add_argument('--company-id', type=int, required=True)
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('--all', action='store_true', help='Enable every module in the catalog')
        group.add_argument('--modules', help='Comma separated module codes, e.g. employee,attendance,leave')

    def handle(self, *args, **options):
        bl = ModuleBL()
        if options['all']:
            catalog = bl.list_modules()['modules']
            codes = [m['code'] for m in catalog]
        else:
            codes = [c.strip() for c in options['modules'].split(',') if c.strip()]

        result = bl.set_company_modules(options['company_id'], codes)
        if result['status'] != 200:
            raise CommandError(str(result))

        enabled = [m['code'] for m in result['modules'] if m['is_enabled']]
        self.stdout.write(self.style.SUCCESS(
            f"Company {options['company_id']}: enabled {len(enabled)} module(s): {', '.join(enabled)}"))
