from pTracker.dataaccess.platform_access.module_da import ModuleDA
from pTracker.dataaccess.platform_access.tenancy_da import TenancyDA
from pTracker.common.company_modules import clear_company_modules_cache
from pTracker.common.logs import Logs
from pTracker.common.exception_handler import ExceptionHandler


def _module_dict(module):
    return {
        'code': module.code,
        'name': module.name,
        'description': module.description,
        'requires': sorted(r.code for r in module.requires.all()),
    }


class ModuleBL():

    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()
        self.__da = ModuleDA()
        self.__tenancy_da = TenancyDA()

    def list_modules(self):
        modules = self.__da.get_all_modules()
        return {'modules': [_module_dict(m) for m in modules], 'status': 200}

    def get_company_modules(self, company_id):
        if not self.__tenancy_da.get_company_by_id(company_id):
            return {'error': 'Company not found', 'status': 404}
        enabled = self.__da.get_enabled_codes_for_company(company_id)
        modules = []
        for module in self.__da.get_all_modules():
            item = _module_dict(module)
            item['is_enabled'] = module.code in enabled
            modules.append(item)
        return {'company_id': company_id, 'modules': modules, 'status': 200}

    def set_company_modules(self, company_id, module_codes):
        if not self.__tenancy_da.get_company_by_id(company_id):
            return {'error': 'Company not found', 'status': 404}
        if not isinstance(module_codes, list):
            return {'error': 'module_codes must be a list', 'status': 400}

        catalog = {m.code: m for m in self.__da.get_all_modules()}
        unknown = set(module_codes) - set(catalog)
        if unknown:
            return {'error': f'Unknown module codes: {sorted(unknown)}', 'status': 400}

        wanted = set(module_codes)
        missing = {}
        for code in wanted:
            not_selected = {r.code for r in catalog[code].requires.all()} - wanted
            if not_selected:
                missing[code] = sorted(not_selected)
        if missing:
            return {
                'error': 'Selected modules depend on modules that are not selected',
                'missing_dependencies': missing,
                'status': 400,
            }

        self.__da.set_company_modules(company_id, wanted)
        clear_company_modules_cache(company_id)
        return self.get_company_modules(company_id)
