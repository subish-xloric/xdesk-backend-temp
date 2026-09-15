from types import SimpleNamespace

from django.http import HttpResponse

from pTracker.common.utility import Utility
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.common.logs import Logs

from pTracker.dataaccess.ptracker_access.user_da import UserDA
from pTracker.dataaccess.ptracker_access.ticket_da import TicketDA
from pTracker.dataaccess.ptracker_access.project_da import ProjectDA

import csv

from pTracker import settings


def new_dto():
    dto = SimpleNamespace()
    return dto


class TicketReportBL():

    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()
        self.__utility = Utility()
        
    
    def get_all_ticket_details_in_csv(self, request):
        response = dict()
        tickets = []
        filter_criteria = {}
        try:
            user_id = request.user.id
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            
            is_permitted_to_view_all_tickets = self.is_user_super_permitted(role_id)

            for key, value in request.query_params.items():
                if value and key not in ['page', 'per_page', 'is_assigned', 'is_reported']:
                    filter_criteria[f'{key}'] = f'{value}'
            project_id = request.query_params.get('project_id') if request.query_params.get('project_id') else 0
            
            is_assigned = request.query_params.get('is_assigned') if request.query_params.get('is_assigned') else None
            is_reported = request.query_params.get('is_reported') if request.query_params.get('is_reported') else None
            
            if is_assigned and is_assigned in ['True', 'true', True]:
                filter_criteria['assigned_to'] = user_id
            elif is_reported and is_reported in ['True', 'true', True]:
                filter_criteria['created_by'] = user_id
            
            all_projects = ProjectDA().get_all_projects()
            all_users = UserDA().get_all_active_users()
            ticket_descriptions = TicketDA().get_all_ticket_description()
            project_ids = ProjectDA().get_all_project_ids_of_user(user_id)
            
            #For a user to view all tickets when a specific project is not selected in dropdown
            if int(project_id) in [None, 0]:
                if is_permitted_to_view_all_tickets:
                    user_tickets = TicketDA().get_all_tickets_filtered(filter_criteria)
                else:
                    filter_criteria['project_id__in'] = project_ids
                    user_tickets = TicketDA().get_all_tickets_filtered(filter_criteria)
                
            #For a user to view all tickets when a specific project is selected in dropdown
            elif int(project_id) in project_ids or is_permitted_to_view_all_tickets:
                user_tickets = TicketDA().get_all_tickets_filtered(filter_criteria)
            
            all_projects = {f"{project.project_id}":f"{project.name}" for project in all_projects }
            all_users = {f"{user.id}":{"id":f"{user.id}", "name":f"{user.first_name} {user.last_name}"} for user in all_users}
            ticket_descriptions = {f"{description.ticket_id}": f"{description.message}" for description in ticket_descriptions}
            
            
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="file.csv"'
            
            writer = csv.writer(response)
            
            writer.writerow(['Ticket ID', 'Title', 'Project Name', 'Assigned To', 'Created By', 'Status', 'Priority', 'Created On', 'Updated On', 'Description'])
            
            for ticket in user_tickets:
                data = [ticket.ticket_id, ticket.subject, all_projects[f"{ticket.project_id}"], all_users[f"{ticket.assigned_to}"]["name"],\
                    all_users[f"{ticket.created_by}"]["name"], ticket.status, ticket.priority, ticket.created_at.strftime("%d/%m/%Y"),\
                    ticket.updated_at.strftime("%d/%m/%Y"), ticket_descriptions[f"{ticket.ticket_id}"]]
                writer.writerow(data)


        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return response
    
    
    def is_user_super_permitted(self, role_id):
        is_user = False
        if role_id in (1, '1', 2, '2', 3, '3'):
            is_user = True
        return is_user