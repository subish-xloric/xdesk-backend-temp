from pTracker.common.company_master_data import CompanyMasterDataBL, TEXT, INT
from pTracker.dataaccess.ptracker_access.leave_da import LeaveDA


class LeaveTypeBL(CompanyMasterDataBL):
    """ Admin CRUD for the active company's leave types. Leave types have no
    is_deleted column: deleting one disables it (available_flag = 0). """
    capability = 'leave.manage_all'
    label = 'Leave type'
    list_key = 'leave_types'
    item_key = 'leave_type'
    name_field = 'leave_type_name'
    fields = (
        ('leave_type_name', 'Name', TEXT, True, 50),
        ('default_no_of_leaves', 'Default number of leaves', INT, False, (0, 366)),
        ('available_flag', 'Enabled', INT, False, (0, 1)),
    )
    create_defaults = {'default_no_of_leaves': 0, 'available_flag': 1}

    def _rows(self, company_id):
        return LeaveDA().get_company_leave_types(company_id)

    def _row(self, company_id, row_id):
        return LeaveDA().get_company_leave_type(company_id, row_id)

    def _name_exists(self, company_id, name, exclude_id=None):
        return LeaveDA().leave_type_name_exists(company_id, name, exclude_id)

    def _create(self, data):
        return LeaveDA().create_leave_type(data)

    def _update(self, row_id, data):
        return LeaveDA().update_leave_type(row_id, data)

    def _deactivate_fields(self):
        return {'available_flag': 0}

    def _validate_update(self, row, fields):
        if row.code and fields.get('available_flag') == 0:
            return f'Leave type "{row.leave_type_name}" is required by the system and cannot be disabled'
        return None

    def _to_dict(self, row):
        return {'id': row.leave_type_id, 'leave_type': row.leave_type_name, 'code': row.code,
                'default_no_of_leaves': row.default_no_of_leaves, 'available_flag': row.available_flag}
