""" Maps backend code packages to product module codes (Module.code in
pTracker/dataaccess/platform_access/module_models.py).

Keyed on the view's Python package, not the URL prefix: several modules are
mounted under more than one prefix (/api/..., /v1/api/..., wfh, tax), and one
package check covers all of them.

This is an allowlist. Any package not listed is NOT gated - deliberately, so
login/2FA/password-reset (pTracker.api.user), dj_rest_auth, the platform
operator API, the mobile app-version check and the wiki can never be blocked
by a module flag.
"""

PACKAGE_TO_MODULE = {
    'pTracker.api.attendance': 'attendance',
    'pTracker.api.attendance_v2': 'attendance',
    'pTracker.api.leave': 'leave',
    'pTracker.api.timesheet': 'timesheet',
    'pTracker.api.projects': 'project',
    'pTracker.api.resource': 'project',
    'pTracker.api.ticket': 'ticket',
    'pTracker.api.asset_management': 'asset',
    'pTracker.api.appraisal': 'appraisal',
    'pTracker.api.assessment': 'assessment',
    'pTracker.api.induction': 'induction',
    'pTracker.api.onboarding': 'onboarding',
    'pTracker.api.offboard': 'offboard',
    'pTracker.api.interview': 'interview',
    'pTracker.api.finance': 'payroll',
    'pTracker.api.rewards': 'rewards',
}

# Packages that are not a product module but whose biz layer makes capability
# checks (e.g. employee list, profile). Their authenticated views get the active
# company resolved so has_capability() works, but are never blocked by a module
# flag - and never blocked at all if no company can be resolved (the capability
# check then fails closed on its own), so logout/password change keep working.
CONTEXT_ONLY_PACKAGES = (
    'pTracker.api.user',
)


def is_context_only_view_class(view_class):
    python_module = view_class.__module__ + '.'
    return any(python_module.startswith(package + '.') for package in CONTEXT_ONLY_PACKAGES)


def module_for_view_class(view_class):
    python_module = view_class.__module__ + '.'
    for package, module_code in PACKAGE_TO_MODULE.items():
        if python_module.startswith(package + '.'):
            return module_code
    return None
