from pTracker.dataaccess.platform_access.module_models import Module
from pTracker.dataaccess.platform_access.module_models import CompanyModule


class ModuleDA():

    def get_all_modules(self):
        return Module.objects.filter(is_active=True).prefetch_related('requires').order_by('code')

    def get_all_module_codes(self):
        return set(Module.objects.filter(is_active=True).values_list('code', flat=True))

    def get_enabled_codes_for_company(self, company_id):
        return set(CompanyModule.objects.filter(
            company_id=company_id, is_enabled=True, module__is_active=True,
        ).values_list('module_id', flat=True))

    def set_company_modules(self, company_id, module_codes):
        wanted = set(module_codes)
        for code in wanted:
            CompanyModule.objects.update_or_create(
                company_id=company_id, module_id=code, defaults={'is_enabled': True},
            )
        CompanyModule.objects.filter(company_id=company_id).exclude(module_id__in=wanted).update(is_enabled=False)
