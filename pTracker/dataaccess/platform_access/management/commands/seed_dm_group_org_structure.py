from django.core.management.base import BaseCommand

from pTracker.dataaccess.platform_access.tenancy_models import Tenant
from pTracker.dataaccess.platform_access.tenancy_models import Company
from pTracker.dataaccess.platform_access.tenancy_models import Branch
from pTracker.dataaccess.platform_access.role_models import Role

# Reuses the Tenant/Company rows created by bridge_legacy_companies
# (matched via legacy_company_id, which is unique) and fills in real
# org structure: branches per company, and each company's own role set.
BRANCHES = {
    2: ['CSEZ Cochin', 'Tech Park Edapilly'],   # DigitalMesh
    3: ['Head Office'],                          # EM Soft
}

ROLES = {
    2: ['Director', 'HR', 'Office Head', 'Lead', 'Developer'],          # DigitalMesh
    3: ['CEO', 'HR Manager', 'Auditor', 'Account'],                     # EM Soft
}


class Command(BaseCommand):
    help = ('One-off: rename the tenant/companies to their real names and create '
            'branches + company-scoped roles for DM Group. Idempotent - safe to re-run.')

    def handle(self, *args, **options):
        tenant, _ = Tenant.objects.update_or_create(
            slug='digitalmesh-group',
            defaults={'name': 'DM Group'},
        )
        self.stdout.write(self.style.SUCCESS(f'Tenant: {tenant.name} (id={tenant.id})'))

        names = {2: ('Digital Mesh', 'Digital Mesh'), 3: ('EM Soft', 'EM Soft')}
        companies = {}
        for legacy_id, (legal_name, short_name) in names.items():
            company = Company.objects.get(legacy_company_id=legacy_id)
            company.legal_name = legal_name
            company.short_name = short_name
            company.save(update_fields=['legal_name', 'short_name', 'updated_at'])
            companies[legacy_id] = company
            self.stdout.write(f'Company: {company.legal_name} (id={company.id}, legacy_company_id={legacy_id})')

        for legacy_id, branch_names in BRANCHES.items():
            company = companies[legacy_id]
            for name in branch_names:
                code = ''.join(w[0] for w in name.split()).upper()
                branch, created = Branch.objects.get_or_create(
                    company=company, name=name,
                    defaults={'code': code},
                )
                status = 'created' if created else 'already exists'
                self.stdout.write(f'  Branch: {branch.name} ({status}, id={branch.id})')

        for legacy_id, role_names in ROLES.items():
            company = companies[legacy_id]
            for name in role_names:
                role, created = Role.objects.get_or_create(company=company, name=name)
                status = 'created' if created else 'already exists'
                self.stdout.write(f'  Role: {role.name} ({status}, id={role.id})')
