""" Shared admin CRUD for the company-scoped master-data lists: job titles,
employment statuses, leave types and project activities.

Every row belongs to one company. All operations act on the active company of
the request (X-Company-Id) and require the list's managing capability there;
a row of another company is reported as not found. Rows carrying a system
`code` (the ones the code depends on, e.g. the "resigned" status or the "lop"
leave type) can be renamed but not deleted or disabled.

Subclasses (in each module's biz layer) declare the fields and wire the DA calls.
"""

from django.conf import settings

from pTracker.common.company_authorization import has_capability
from pTracker.common.company_context import get_active_company_id
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.common.logs import Logs

TEXT = 'text'
INT = 'int'


class CompanyMasterDataBL():
    capability = ''     # capability that manages this list
    label = ''          # e.g. 'Job title', used in messages
    list_key = ''       # response key for the list
    item_key = ''       # response key for one row
    name_field = ''     # field that must be unique within a company
    # (field, label, kind, required on create, max length for TEXT / (min, max) for INT)
    fields = ()
    create_defaults = {}

    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()

    # ------------------------------------------------------------ DA hooks
    def _rows(self, company_id):
        raise NotImplementedError

    def _row(self, company_id, row_id):
        raise NotImplementedError

    def _name_exists(self, company_id, name, exclude_id=None):
        raise NotImplementedError

    def _create(self, data):
        raise NotImplementedError

    def _update(self, row_id, data):
        raise NotImplementedError

    def _deactivate_fields(self):
        """ Fields that soft-delete a row. """
        return {'is_deleted': 1}

    def _to_dict(self, row):
        raise NotImplementedError

    def _validate_update(self, row, fields):
        """ Extra per-list rules; returns an error message or None. """
        return None

    # ---------------------------------------------------------- operations
    def list(self, user_id):
        return self.__run(self.__list, user_id)

    def create(self, user_id, data):
        return self.__run(self.__create, user_id, data)

    def update(self, user_id, row_id, data):
        return self.__run(self.__update, user_id, row_id, data)

    def delete(self, user_id, row_id):
        return self.__run(self.__delete, user_id, row_id)

    def __run(self, operation, user_id, *args):
        try:
            company_id = get_active_company_id()
            if company_id is None or not has_capability(user_id, self.capability):
                return {'error': settings.ERROR_MSG['access_denied'], 'status': 403}
            return operation(company_id, *args)
        except Exception:
            log_id = self.__log.error(self.__exception.get_exception())
            return {'error': f'Request failed. LogID: {log_id}', 'status': 500}

    def __list(self, company_id):
        return {self.list_key: [self._to_dict(row) for row in self._rows(company_id)], 'status': 200}

    def __create(self, company_id, data):
        fields, error = self.__clean(data, creating=True)
        if error:
            return {'error': error, 'status': 400}
        if self._name_exists(company_id, fields[self.name_field]):
            return {'error': f'{self.label} "{fields[self.name_field]}" already exists', 'status': 400}
        values = dict(self.create_defaults)
        values.update(fields)
        values['company_id'] = company_id
        row = self._create(values)
        return {self.item_key: self._to_dict(row), 'status': 201}

    def __update(self, company_id, row_id, data):
        row = self._row(company_id, row_id)
        if not row:
            return {'error': f'{self.label} not found', 'status': 404}
        fields, error = self.__clean(data, creating=False)
        if not error:
            error = self._validate_update(row, fields)
        if error:
            return {'error': error, 'status': 400}
        name = fields.get(self.name_field)
        if name and self._name_exists(company_id, name, exclude_id=row_id):
            return {'error': f'{self.label} "{name}" already exists', 'status': 400}
        if fields:
            self._update(row_id, fields)
        return {self.item_key: self._to_dict(self._row(company_id, row_id)), 'status': 200}

    def __delete(self, company_id, row_id):
        row = self._row(company_id, row_id)
        if not row:
            return {'error': f'{self.label} not found', 'status': 404}
        if getattr(row, 'code', None):
            return {'error': f'{self.label} "{getattr(row, self.name_field)}" is required by the system '
                             'and cannot be deleted; rename it instead', 'status': 400}
        self._update(row_id, self._deactivate_fields())
        return {'message': f'{self.label} deleted', 'status': 200}

    def __clean(self, data, creating):
        """ Validated values for the declared fields present in data. """
        if not isinstance(data, dict):
            return None, 'Invalid request body'
        cleaned = {}
        for field, label, kind, required, limit in self.fields:
            if field not in data or data.get(field) is None:
                if creating and required:
                    return None, f'{label} is required'
                continue
            value = data.get(field)
            if kind == TEXT:
                if not isinstance(value, str):
                    return None, f'{label} must be text'
                value = value.strip()
                if required and not value:
                    return None, f'{label} is required'
                if len(value) > limit:
                    return None, f'{label} must be at most {limit} characters'
            else:
                if isinstance(value, bool):
                    return None, f'{label} must be a whole number'
                try:
                    value = int(value)
                except (TypeError, ValueError):
                    return None, f'{label} must be a whole number'
                low, high = limit
                if value < low or value > high:
                    return None, f'{label} must be between {low} and {high}'
            cleaned[field] = value
        return cleaned, None
