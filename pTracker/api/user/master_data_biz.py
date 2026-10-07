from pTracker.common.company_master_data import CompanyMasterDataBL, TEXT, INT
from pTracker.dataaccess.ptracker_access.user_da import UserDA


class JobTitleBL(CompanyMasterDataBL):
    """ Admin CRUD for the active company's job titles. """
    capability = 'employee.manage'
    label = 'Job title'
    list_key = 'job_titles'
    item_key = 'job_title'
    name_field = 'job_title'
    fields = (
        ('job_title', 'Job title', TEXT, True, 100),
        ('job_description', 'Description', TEXT, False, 400),
        ('note', 'Note', TEXT, False, 400),
    )
    create_defaults = {'job_description': '', 'note': ''}

    def _rows(self, company_id):
        return UserDA().get_all_job_titles(company_id)

    def _row(self, company_id, row_id):
        return UserDA().get_company_job_title(company_id, row_id)

    def _name_exists(self, company_id, name, exclude_id=None):
        return UserDA().job_title_exists(company_id, name, exclude_id)

    def _create(self, data):
        return UserDA().create_job_title(data)

    def _update(self, row_id, data):
        return UserDA().update_job_title(row_id, data)

    def _to_dict(self, row):
        return {'id': row.id, 'title': row.job_title,
                'job_description': row.job_description, 'note': row.note}


class EmploymentStatusBL(CompanyMasterDataBL):
    """ Admin CRUD for the active company's employment statuses. """
    capability = 'employee.manage'
    label = 'Employment status'
    list_key = 'employment_statuses'
    item_key = 'employment_status'
    name_field = 'name'
    fields = (
        ('name', 'Name', TEXT, True, 50),
        ('sort_order', 'Sort order', INT, False, (0, 1000)),
    )
    create_defaults = {'sort_order': 0}

    def _rows(self, company_id):
        return UserDA().get_employment_statuses(company_id)

    def _row(self, company_id, row_id):
        return UserDA().get_company_employment_status(company_id, row_id)

    def _name_exists(self, company_id, name, exclude_id=None):
        return UserDA().employment_status_exists(company_id, name, exclude_id)

    def _create(self, data):
        return UserDA().create_employment_status(data)

    def _update(self, row_id, data):
        return UserDA().update_employment_status(row_id, data)

    def _to_dict(self, row):
        return {'id': row.id, 'status': row.name, 'code': row.code, 'sort_order': row.sort_order}
