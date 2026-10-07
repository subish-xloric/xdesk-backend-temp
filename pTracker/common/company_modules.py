""" Resolves which product modules a company has enabled.

A company with no CompanyModule rows has no modules enabled (fail-closed).
The enabled set is cached briefly; the platform API clears it on change, and
the TTL bounds staleness across worker processes.
"""

from django.core.cache import cache

from pTracker.dataaccess.platform_access.module_da import ModuleDA

CACHE_TTL_SECONDS = 60
CATALOG_CACHE_KEY = 'platform:module_catalog'


def _cache_key(company_id):
    return f'platform:company_modules:{company_id}'


def get_enabled_module_codes(company_id):
    key = _cache_key(company_id)
    codes = cache.get(key)
    if codes is None:
        codes = sorted(ModuleDA().get_enabled_codes_for_company(company_id))
        cache.set(key, codes, CACHE_TTL_SECONDS)
    return set(codes)


def clear_company_modules_cache(company_id):
    cache.delete(_cache_key(company_id))


def get_catalog_module_codes():
    codes = cache.get(CATALOG_CACHE_KEY)
    if codes is None:
        codes = sorted(ModuleDA().get_all_module_codes())
        cache.set(CATALOG_CACHE_KEY, codes, CACHE_TTL_SECONDS)
    return set(codes)


def is_catalog_module_disabled(company_id, module_code):
    """True only if module_code is a real catalog module that the company
    has not enabled. Non-module prefixes (e.g. 'company') are never blocked."""
    if module_code not in get_catalog_module_codes():
        return False
    return module_code not in get_enabled_module_codes(company_id)
