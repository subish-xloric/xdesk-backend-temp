""" Blocks requests to a product module's endpoints when the caller's company
has not enabled that module.

Nearly every view sets its own authentication_classes, and JWT auth only
completes inside the view, so this authenticates with the *view's own*
authenticators from process_view. That keeps every view and URL unchanged and
works for both JWT and the token-authenticated external ticket API.

Requests that are unauthenticated, or not an employee identity, are passed
through untouched so the view returns its normal 401/403. An employee with no
active membership, or an X-Company-Id they do not belong to, is rejected here
(see company_context.py); there is no legacy fallback. On success the active
company is kept for the request so has_capability() can use it.
"""

from django.contrib.auth import get_user_model
from django.http import JsonResponse

from pTracker.common.module_registry import is_context_only_view_class
from pTracker.common.module_registry import module_for_view_class
from pTracker.common.company_modules import get_enabled_module_codes
from pTracker.common.company_context import COMPANY_HEADER
from pTracker.common.company_context import CompanyContextError
from pTracker.common.company_context import resolve_active_company
from pTracker.common.company_context import set_active_company
from pTracker.common.company_context import clear_active_company


class ModuleGateMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        clear_active_company()
        try:
            return self.get_response(request)
        finally:
            clear_active_company()

    def process_view(self, request, view_func, view_args, view_kwargs):
        view_class = getattr(view_func, 'cls', None)
        if view_class is None:
            return None

        module_code = module_for_view_class(view_class)
        if module_code is None:
            if is_context_only_view_class(view_class):
                return self._set_context_if_resolvable(view_class, request)
            return None

        user = self._authenticate(view_class, request)
        if not self._is_employee(user):
            return None

        try:
            active = resolve_active_company(user.pk, request.META)
        except CompanyContextError as error:
            return JsonResponse({'error': error.message, 'code': error.code, 'status': error.status},
                                status=error.status)

        if module_code in get_enabled_module_codes(active.company_id):
            set_active_company(active)
            return None

        return JsonResponse({
            'error': f"Module '{module_code}' is not enabled for your company",
            'module': module_code,
            'status': 403,
        }, status=403)

    def _set_context_if_resolvable(self, view_class, request):
        """ Context-only views still run without a company (no membership, or
        several and no header) so logout/password change keep working - their
        capability checks then fail closed. But an X-Company-Id the caller sent
        explicitly must be one they belong to: it is rejected, never ignored. """
        user = self._authenticate(view_class, request)
        if not self._is_employee(user):
            return None
        try:
            set_active_company(resolve_active_company(user.pk, request.META))
        except CompanyContextError as error:
            if request.META.get(COMPANY_HEADER) not in (None, ''):
                return JsonResponse({'error': error.message, 'code': error.code, 'status': error.status},
                                    status=error.status)
        return None

    def _is_employee(self, user):
        """ Platform operators and machine principals (e.g. attendance
        collectors) are not employees: they carry no membership and are
        authorized by their own view permissions. """
        return user is not None and isinstance(user, get_user_model())

    def _authenticate(self, view_class, request):
        try:
            drf_request = view_class().initialize_request(request)
            user = drf_request.user
        except Exception:
            return None
        if user is None or not getattr(user, 'is_authenticated', False):
            return None
        return user
