from pTracker.common.company_master_data import CompanyMasterDataBL, TEXT
from pTracker.dataaccess.ptracker_access.project_da import ProjectDA


class ProjectActivityBL(CompanyMasterDataBL):
    """ Admin CRUD for the active company's timesheet activities. """
    capability = 'project.manage'
    label = 'Activity'
    list_key = 'activities'
    item_key = 'activity'
    name_field = 'name'
    fields = (
        ('name', 'Name', TEXT, True, 150),
        ('description', 'Description', TEXT, False, 45),
    )
    create_defaults = {'description': ''}

    def _rows(self, company_id):
        return ProjectDA().get_all_project_activity(company_id)

    def _row(self, company_id, row_id):
        return ProjectDA().get_company_project_activity(company_id, row_id)

    def _name_exists(self, company_id, name, exclude_id=None):
        return ProjectDA().project_activity_exists(company_id, name, exclude_id)

    def _create(self, data):
        return ProjectDA().create_project_activity(data)

    def _update(self, row_id, data):
        return ProjectDA().update_project_activity(row_id, data)

    def _to_dict(self, row):
        return {'id': row.activity_id, 'name': row.name, 'description': row.description}
