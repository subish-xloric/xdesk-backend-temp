
from datetime import datetime, date, timedelta, time
from django.http import HttpResponse
from django.utils import timezone
from datetime import timedelta
from types import SimpleNamespace
import uuid
from django.db import  transaction
from django.db.models import Q

from datetime import datetime
from itertools import chain
from django.utils.safestring import mark_safe
from bs4 import BeautifulSoup

from django.conf import Settings, settings

from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Sum

from pTracker.common.utility import Utility
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.common.logs import Logs

from pTracker.api.ticket.notification_biz import NotificationBL
from pTracker.api.ticket.ticket_helper import TicketHelperBL

from pTracker.dataaccess.ptracker_access.user_da import UserDA
from pTracker.dataaccess.ptracker_access.ticket_da import TicketDA
from pTracker.dataaccess.ptracker_access.project_da import ProjectDA

from pTracker.settings import constants
from pTracker.cronjobs.email_sender import send_email_notification

from pTracker.api.ticket.validators import TicketValidatorBL

from cryptography.fernet import Fernet
from pTracker.common.file_manager import FileManager


def new_dto():
    dto = SimpleNamespace()
    return dto

class TicketBL():
    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()
        self.__utility = Utility()
        self.__validator = TicketValidatorBL()
        self.__helper = TicketHelperBL()
        self.__file_manager = FileManager()


    def get_attachment_file(self, request, attachment_id):
        response = {"message": "", "success": False, "url": "", "error": "", "status":200}
        content_types = {
            'pdf': 'application/pdf',
            'png': 'image/png',
            'jpeg': 'image/jpeg',
            'jpg': 'image/jpeg',
            'mp4':'video/mp4',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'csv': 'text/csv',
        }
        try:
            user_id = request.user.id
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            is_permitted_to_view_all_tickets = self.is_manager(role_id)
            attachment = TicketDA().get_ticket_attachment_by_attachment_id(attachment_id)
            ticket_id = attachment.ticket_id
            ticket = TicketDA().get_ticket_by_ticket_id(ticket_id)
            project_id = ticket.project_id
            is_part_of_project = self.is_project_accessible(user_id, project_id)

            if not is_permitted_to_view_all_tickets and not is_part_of_project:
                response["error"] = settings.ERROR_MSG.get("access_denied")
                response["status"] = 403
                return response

            file_type = attachment.file.split('.')[-1]
            folder_path = self.__helper.get_ticket_attachment_folder(attachment.filename, attachment.ticket_id)
            file_type_lower = file_type.lower()
            if file_type_lower in content_types:
                file_bytes = self.__file_manager.read_encrypted_file(folder_path)
                if file_bytes is not None:
                    response = HttpResponse(file_bytes, content_type=content_types[file_type_lower])
                    response['Content-Disposition'] = f'inline; filename="{attachment.filename}.{file_type_lower}"'
                    response['success'] = True
                    return response

        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error'].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
            response["status"] = 499
        return response


    #This for OVERVIEW
    def list_all_project_tickets(self, request):
        response = {"message": "", "success": False, "project_tickets":[], 'project_list': [], "error": "", "status":200}
        ticket_dict = {}
        user_tickets = None
        final_result = []
        project_list = []
        sag_project_ids = settings.COMMON_PROJECTS
        try:
            user_id = request.user.id
            role_id, role_name = UserDA().get_user_role_by_id(user_id)

            is_manager = self.is_manager(role_id)

            if is_manager:
                project_ids = ProjectDA().get_all_project_ids()
            else:
                project_ids = ProjectDA().get_all_project_ids_of_user(user_id)

            all_projects = ProjectDA().get_all_projects()
            all_projects = {f"{project.project_id}":f"{project.name}" for project in all_projects }

            all_users = UserDA().get_all_users()
            all_users = {f"{user.id}":{"id":f"{user.id}", "name":f"{user.first_name} {user.last_name}"} for user in all_users}

            ticket_descriptions = TicketDA().get_all_ticket_description()
            ticket_descriptions = {f"{description.ticket_id}": f"{description.message}" for description in ticket_descriptions}

            sag_team_members = []
            sag_team_leads = []

            #Get Sag team leads
            for project_id in sag_project_ids:
                lead_id = ProjectDA().get_project_leads_by_project_id(project_id).first().user_id
                sag_team_leads.append(lead_id)

            #Get Sag team members
            for lead_id in sag_team_leads:
                team_members = UserDA().get_current_team_members_by_lead_id(lead_id)
                team_members = list(map(lambda member: member.id, team_members))
                # sag_team_dict[lead_id] = team_members
                sag_team_members.extend(team_members)

            sag_team_members = list(set(sag_team_members))

            #Checking whether the user is Sag team member or Sag team lead
            is_sag_team_member = True if user_id in sag_team_members else False
            is_sag_team_lead = True if user_id in sag_team_leads else False

            #checking whether the user is lead (and not a sag team member or sag team lead as sag team member also have role_id as 4)
            #If the user is team lead then his team members user_ids are appended to a list, so that team members tickets can also be listed on leads account
            if role_id == 4 and (not is_sag_team_lead and not is_sag_team_member):
                user_ids = UserDA().get_current_team_members_by_lead_id(user_id)
                user_ids = list(map(lambda user: user.id, user_ids))
                user_ids.append(user_id)

            for project_id in project_ids:
                if str(project_id) not in all_projects:
                    continue
                project_list.append({'project_id': project_id,  'project_name': all_projects[str(project_id)]})

                #Checking whether user is a developer or a lead, and project is a sag project
                if (project_id in sag_project_ids and not is_manager) and (not is_sag_team_member and not is_sag_team_lead):
                    if role_id == 4:
                        ticket = TicketDA().get_latest_updated_user_created_tickets_from_project_id(project_id, user_ids)
                    else:
                        ticket = TicketDA().get_latest_updated_user_created_tickets_from_project_id(project_id, [user_id])
                else:
                    ticket = TicketDA().get_latest_updated_tickets_from_project_id(project_id)

                if ticket in [None]:
                    continue
                if user_tickets:
                    combined_qs = chain(user_tickets, ticket)
                    user_tickets = combined_qs
                else:
                    user_tickets = ticket

            user_tickets = list(user_tickets)
            # latest_ticket_ids = [ user_ticket.ticket_id for user_ticket in user_tickets ]
            latest_ticket_ids = []
            for user_ticket in user_tickets:
                if user_ticket in [None]:
                    continue
                latest_ticket_ids.append(user_ticket.ticket_id)

            latest_of_each_ticket = TicketDA().get_latest_users_from_each_ticket(latest_ticket_ids)
            latest_users = { each[0]:{ 'ticket_id':each[0], 'updated_by':each[1], 'update_action':each[2], 'updated_at':each[3] } for each in latest_of_each_ticket }

            for ticket in user_tickets:
                if not f"{ticket.project_id}" in ticket_dict:
                    ticket_dict[f"{ticket.project_id}"] = {"project_name": all_projects[f"{ticket.project_id}"],"ticket_list":[]}

                ticket_data = {}
                ticket_data['id'] = ticket.ticket_id
                ticket_data['assigned_to'] = all_users[f"{ticket.assigned_to}"]["name"] if ticket.assigned_to else 'NoBody'
                ticket_data['created_by'] = all_users[f"{ticket.created_by}"]["name"]
                ticket_data['status'] = ticket.status
                ticket_data['priority'] = ticket.priority
                ticket_data['title'] = ticket.subject
                ticket_data['created_at'] = ticket.created_at.strftime("%d/%m/%Y")
                ticket_data['updated_at'] = latest_users[ticket.ticket_id]['updated_at'].strftime("%b %d")
                ticket_data['description'] = ticket_descriptions[f"{ticket.ticket_id}"]
                ticket_data['updated'] = latest_users[ticket.ticket_id]['updated_at']
                ticket_data['created'] = ticket.created_at
                ticket_data['status'] = ticket.status
                ticket_data['updated_by'] = all_users[f"{latest_users[ticket.ticket_id]['updated_by']}"]["name"]
                ticket_data['update_action'] = latest_users[ticket.ticket_id]['update_action']

                ticket_dict[f"{ticket.project_id}"]["ticket_list"].append(ticket_data)

            for project_id, data in ticket_dict.items():
                final_result.append({'project_id': project_id, 'details': data})

            final_result = sorted(final_result, key=lambda project:project['details']['ticket_list'][0]['updated'], reverse=True)
            project_list_sorted = sorted(project_list, key=lambda x: x['project_name'].lower())

            if project_list:
                project_list = sorted(project_list, key=lambda d: d['project_name'])
            response['project_tickets'] = final_result
            response['project_list'] = project_list_sorted
            response['success'] = True
            response['message'] = 'Project Tickets Listed'

        except Exception as err:
            response['success'] = False
            response["error"] = settings.ERROR_MSG['application_error'].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
            response['status'] = 499
        return response


    #Project Ticket Listing
    def list_all_tickets(self, request):
        response = {"message": "", "success": False, "error":"", "status":200}
        tickets = []
        filter_criteria = {}
        current_datetime = datetime.now()
        current_date = current_datetime.date()

        start_of_today = datetime.combine(current_date, datetime.min.time())
        end_of_today = datetime.combine(current_date, datetime.max.time())
        sag_project_ids = settings.COMMON_PROJECTS
        try:
            is_unanswered = False
            user_id = request.user.id
            role_id, role_name = UserDA().get_user_role_by_id(user_id)

            is_permitted_to_view_all_tickets = self.is_manager(role_id)

            project_id = request.query_params.get('project_id') if request.query_params.get('project_id') else 0

            project = ProjectDA().get_project_by_id(int(project_id))
            if not project:
                response["error"] = "You have attempted to access an invalid project. Please contact your lead/manager for assistance."
                response['status'] = 499
                return response

            filter_criteria['project_id'] = project_id

            page = int(request.GET.get('page', 1)) if int(request.GET.get('page', 1)) > 0 else 1
            per_page = int(request.GET.get('per_page', 20))

            sort_field = request.GET.get('currentSortField', '-updated_at')
            temp_sort_field = '' #To Manually Sort Assigned Users, Reporters
            if sort_field in ('assigned_to','created_by', '-assigned_to','-created_by'):
                temp_sort_field = sort_field
                sort_field = '-updated_at'
            if sort_field in ('', None, 'undefined'):
                sort_field = '-updated_at'

            search_value = request.query_params.get('search_value') if request.query_params.get('search_value') else None

            is_assigned = request.query_params.get('is_assigned') if request.query_params.get('is_assigned') else None
            is_reported = request.query_params.get('is_reported') if request.query_params.get('is_reported') else None
            resolution = request.query_params.get('resolution')
            is_my_overdue = request.query_params.get('is_my_overdue') if request.query_params.get('is_my_overdue') else None
            is_team_overdue = request.query_params.get('is_team_overdue') if request.query_params.get('is_team_overdue') else None
            is_today_overdue = request.query_params.get('is_today_overdue') if request.query_params.get('is_today_overdue') else None
            is_unassign = request.query_params.get('is_unassign') if request.query_params.get('is_unassign') else None
            is_unanswer = request.query_params.get('is_unanswer') if request.query_params.get('is_unanswer') else None

            status = request.query_params.get('status') if request.query_params.get('status') else None
            priority = request.query_params.get('priority') if request.query_params.get('priority') else None
            ticket_type = request.query_params.get('ticket_type') if request.query_params.get('ticket_type') else None
            category = request.query_params.get('category') if request.query_params.get('category') else None
            assignee = int(request.query_params.get('assignee')) if request.query_params.get('assignee') \
                       and request.query_params.get('assignee') not in ['null', None, 0, '0'] else None
            reporter = int(request.query_params.get('reporter')) if request.query_params.get('reporter') \
                       and request.query_params.get('reporter') not in ['null', None, 0, '0'] else None
            
            module_id = int(request.query_params.get('module_id')) if request.query_params.get('module_id') \
                       and request.query_params.get('module_id') not in ['null', None, 0, '0'] else None

            start_date = datetime.strptime(request.query_params.get('start_date'), "%Y-%m-%d") if request.query_params.get('start_date') else None
            end_date = datetime.strptime(request.query_params.get('end_date'), "%Y-%m-%d") if request.query_params.get('end_date') else None
            date_filter_criteria = request.query_params.get('date_filter_criteria') if request.query_params.get('date_filter_criteria') else None

            if date_filter_criteria == 'Created':
                filter_criteria['created_at__gte'] = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
                filter_criteria['created_at__lte'] = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            elif date_filter_criteria == 'Updated':
                filter_criteria['updated_at__gte'] = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
                filter_criteria['updated_at__lte'] = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            elif date_filter_criteria == 'Due Date':
                filter_criteria['deadline__gte'] = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
                filter_criteria['deadline__lte'] = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)

            if is_assigned and is_assigned in ['True', 'true', True]:
                filter_criteria['assigned_to'] = user_id
            elif is_reported and is_reported in ['True', 'true', True]:
                filter_criteria['created_by'] = user_id

            if assignee:
                assignee_role_id, assignee_role_name = UserDA().get_user_role_by_id(assignee)
                is_assignee_manager = self.is_manager(assignee_role_id)
                is_assignee_part_of_project = self.is_project_accessible(assignee, project_id)
                if is_assignee_part_of_project or is_assignee_manager:
                    filter_criteria['assigned_to'] = assignee
                else:
                    response['success'] = False
                    response["error"] = "Assignee is not part of project"
                    response['status'] = 403
                    return response

            if reporter:
                reporter_role_id, reporter_role_name = UserDA().get_user_role_by_id(reporter)
                is_reporter_manager = self.is_manager(reporter_role_id)
                is_reporter_part_of_project = self.is_project_accessible(reporter, project_id)
                if is_reporter_part_of_project or is_reporter_manager:
                    filter_criteria['created_by'] = reporter
                else:
                    response['success'] = False
                    response["error"] = "Reporter is not part of project"
                    response['status'] = 403
                    return response


            if status:
                ticket_statuses = settings.TICKETS_STATUS_CHOICES
                ticket_statuses = list(map(lambda status: status[1], ticket_statuses))
                #Checking entered status is present in status list
                if status in ticket_statuses:
                    filter_criteria['status'] = status

            if priority:
                ticket_priorities = settings.TICKETS_PRIORITY_CHOICES
                ticket_priorities = list(map(lambda priority: priority[1], ticket_priorities))
                #Checking entered priority is present in priority list
                if priority in ticket_priorities:
                    filter_criteria['priority'] = priority

            if ticket_type:
                ticket_types = settings.TICKETS_TYPE_CHOICES
                ticket_types = list(map(lambda ticket_type: ticket_type[1], ticket_types))
                #Checking entered ticket type is present in ticket type list
                if ticket_type in ticket_types:
                    filter_criteria['ticket_type'] = ticket_type

            if category:
                categories = settings.TICKET_CATEGORIES
                categories = list(map(lambda category: category[1], categories))
                #Checking entered category is present in category list
                if category in categories:
                    filter_criteria['category'] = category


            # if is_my_overdue and is_my_overdue in ['True', 'true', True]:
            #     filter_criteria['deadline__lt'] = current_datetime
            if is_team_overdue and is_team_overdue in ['True', 'true', True] or is_my_overdue and is_my_overdue in ['True', 'true', True]:
                filter_criteria['deadline__date__lt'] = current_datetime
            elif is_today_overdue and is_today_overdue in ['True', 'true', True]:
                filter_criteria['deadline__gte'] = start_of_today
                filter_criteria['deadline__lte'] = end_of_today
            elif is_unassign and is_unassign in ['True', 'true', True]:
                filter_criteria['assigned_to'] = 0
            elif is_unanswer and is_unanswer in ['True', 'true', True]:
                is_unanswered = True

            all_projects = ProjectDA().get_all_projects()
            #all_users = UserDA().get_all_active_users()
            all_users = UserDA().get_all_users()
            ticket_descriptions = TicketDA().get_all_ticket_description()
            project_ids = ProjectDA().get_all_project_ids_of_user(user_id)

            try:
                project_id = int(project_id)
            except:
                response['success'] = False
                response["error"] = "Please enter a valid project id"
                response['status'] = 403
                return response

            #------- Now we are using project_id to view tickets including as managers so commenting the below -------

            #For a user to view all tickets when a specific project is not selected in dropdown
            # if int(project_id) in [None, 0]:
            #     filter_criteria.pop('project_id', None)

            #     if is_permitted_to_view_all_tickets:
            #         user_tickets = TicketDA().get_all_tickets_filtered(filter_criteria,is_unanswered)
            #     else:
            #         user_tickets = TicketDA().get_all_tickets_filtered(filter_criteria, project_ids,is_unanswered)

            #     if user_tickets:
            #         open_tickets = user_tickets.filter(status__in=settings.TICKET_STATUS_OPEN)
            #         closed_tickets = user_tickets.filter(status__in=settings.TICKET_STATUS_CLOSED)
            #         if resolution == 'open':
            #             user_tickets = open_tickets
            #         elif resolution == 'closed':
            #             user_tickets = closed_tickets
            #         open_count = open_tickets.count()
            #         closed_count = closed_tickets.count()
            #     else:
            #         open_count = 0
            #         closed_count = 0
            #     paginator = Paginator(user_tickets, per_page)
            #     page_obj = paginator.get_page(page)


            #For a user to view all tickets when a specific project is selected in dropdown
            if int(project_id) in project_ids or is_permitted_to_view_all_tickets:
                user_tickets = TicketDA().get_all_tickets_filtered_v1(filter_criteria,is_unanswered, sort_field)

                if int(filter_criteria['project_id']) in sag_project_ids and not is_permitted_to_view_all_tickets:
                    # sag_team_dict = {}
                    sag_team_members = []
                    sag_team_leads = []

                    #Sag project ids are retrieved and leads of each projects are added to list
                    # for project_id in sag_project_ids:
                    lead_id = ProjectDA().get_project_leads_by_project_id(int(filter_criteria['project_id'])).first().user_id
                    sag_team_leads.append(lead_id)

                    #Each lead_id are iterated and his team members are added to a dict as a list where lead_id is key.
                    for lead_id in sag_team_leads:
                        team_members = UserDA().get_current_team_members_by_lead_id(lead_id)
                        team_members = list(map(lambda member: member.id, team_members))
                        # sag_team_dict[lead_id] = team_members
                        sag_team_members.extend(team_members)

                    sag_team_members = list(set(sag_team_members))

                    #Checking whether the user is Sag team member or Sag team lead
                    is_sag_team_member = True if user_id in sag_team_members else False
                    is_sag_team_lead = True if user_id in sag_team_leads else False

                    #If user is a lead, then all of his team members are added to a list (as Sag team member have role_id as 4 and Sag lead has role_id as 3, so avoiding them)
                    if role_id == 4 and (not is_sag_team_lead and not is_sag_team_member):
                        user_ids = UserDA().get_current_team_members_by_lead_id(user_id)
                        user_ids = list(map(lambda user: user.id, user_ids))
                        user_ids.append(user_id)

                    #Logic for Non-Sag members -> for lead, all the sag tickets created by him and his team members will be listed, for a developer, tickets created by him only will be listed
                    if not is_sag_team_member and not is_sag_team_lead:
                        if role_id == 4:
                            user_tickets = user_tickets.filter(project_id=project_id, created_by__in=user_ids).order_by(sort_field)
                        else:
                            user_tickets = user_tickets.filter(project_id=project_id, created_by=user_id).order_by(sort_field)

                # This logic also taken for open and closed ticket counts

                all_projects = {f"{project.project_id}":f"{project.name}" for project in all_projects }
                all_users = {f"{user.id}":{"id":f"{user.id}", "name":f"{user.first_name} {user.last_name}", "firstname":f"{user.first_name}", "lastname":f"{user.last_name}"} for user in all_users}
                ticket_descriptions = {f"{description.ticket_id}": f"{description.message}" for description in ticket_descriptions}

                if search_value not in ['null', '', None, 'undefined'] and user_tickets:
                    #storing user_tickets into new variable to apply description search condition
                    user_ticket_v1 = user_tickets
                    user_tickets = user_tickets.filter(Q(tag_name__icontains=search_value) | Q(subject__icontains=search_value))
                    
                    #description search condition
                    user_ticket_ids_for_desc_filter = list(map(lambda x:x.ticket_id, user_ticket_v1))
                    ticket_messages = TicketDA().get_all_ticket_messages_by_ticket_ids(user_ticket_ids_for_desc_filter)
                    ticket_descriptions_v1 = {}
                    for desc in ticket_messages:
                        #Beautifulsoup is used to remove html content from text
                        if desc.ticket_id in ticket_descriptions_v1.keys():
                            ticket_descriptions_v1[desc.ticket_id].append(BeautifulSoup(desc.message, 'html.parser').get_text())
                        else:
                            ticket_descriptions_v1[desc.ticket_id] = []
                            ticket_descriptions_v1[desc.ticket_id].append(BeautifulSoup(desc.message, 'html.parser').get_text())
                    
                    #this filters out user tickets in such a way that if there is any string searched is present in any message of tickets filtered out
                    user_ticket_descs = dict(filter(lambda item: int(item[0]) in user_ticket_ids_for_desc_filter and any(search_value in s for s in item[1]), ticket_descriptions_v1.items()))
                    desc_search_ticket_ids = list(user_ticket_descs.keys())
                    desc_filtered_tickets = user_ticket_v1.filter(ticket_id__in=desc_search_ticket_ids)
                    user_tickets = user_tickets | desc_filtered_tickets

                if module_id:
                    user_tickets = user_tickets.filter(module_id=module_id)

                if user_tickets:

                    open_tickets = user_tickets.filter(status__in=settings.TICKET_STATUS_OPEN)
                    closed_tickets = user_tickets.filter(status__in=settings.TICKET_STATUS_CLOSED)
                    if resolution == 'open':
                        user_tickets = open_tickets
                    elif resolution == 'closed':
                        user_tickets = closed_tickets
                    open_count = open_tickets.count()
                    closed_count = closed_tickets.count()
                else:
                    open_count = 0
                    closed_count = 0
                if temp_sort_field:
                    for each in user_tickets:
                        # each.assigned_to_name = all_users[f"{each.assigned_to}"]["firstname"] if each.assigned_to else '-'
                        # each.created_by_name = all_users[f"{each.created_by}"]["firstname"] if each.created_by else '-'

                        each.assigned_to_name = all_users[f"{each.assigned_to}"]["firstname"] if all_users.get(f"{each.assigned_to}") else "-"
                        each.created_by_name = all_users[f"{each.created_by}"]["firstname"]  if all_users.get(f"{each.created_by}") else "-"

                    # Sort based on temp_sort_field
                    if temp_sort_field == '-created_by':
                        user_tickets = sorted(user_tickets, key=lambda x: x.created_by_name, reverse=True)
                    elif temp_sort_field == 'created_by':
                        user_tickets = sorted(user_tickets, key=lambda x: x.created_by_name)
                    elif temp_sort_field == '-assigned_to':
                        user_tickets = sorted(user_tickets, key=lambda x: x.assigned_to_name, reverse=True)
                    else:
                        user_tickets = sorted(user_tickets, key=lambda x: x.assigned_to_name)

                paginator = Paginator(user_tickets, per_page)
                page_obj = paginator.get_page(page)
                ticket_ids = [ticket.ticket_id for ticket in page_obj]
                if ticket_ids:
                    total_logged_time = self.__helper.get_work_logs_by_ticket_ids(ticket_ids)
            else:
                response["error"] = settings.ERROR_MSG.get("access_denied")
                response["status"] = 403
                return response



            ticket_count_dict = self.__helper.get_ticket_sub_task_count(project_id)

            for ticket in page_obj:
                sub_ticket_count = ticket_count_dict.get(ticket.ticket_id, None)
                estimated_time = self.__helper.ticket_time_format(ticket.estimated_time)
                work_log_sec =  total_logged_time.get(ticket.ticket_id,0)
                work_log = self.__helper.ticket_time_format(work_log_sec)
                ticket_dict = {}
                ticket_dict['id'] = ticket.ticket_id
                ticket_dict['id_with_sub'] = f"#{ticket.ticket_id} [{sub_ticket_count}]" if sub_ticket_count else f"#{ticket.ticket_id}"
                ticket_dict['sub_count'] = f"{sub_ticket_count}" if sub_ticket_count else None
                ticket_dict['project'] = all_projects[f"{ticket.project_id}"]
                ticket_dict['project_id'] = ticket.project_id
                if not temp_sort_field:
                    ticket_dict['assigned_to'] = all_users[f"{ticket.assigned_to}"]["firstname"] if all_users.get(f"{ticket.assigned_to}") else "-"
                    ticket_dict['created_by'] = all_users[f"{ticket.created_by}"]["firstname"]  if all_users.get(f"{ticket.created_by}") else "-"
                else:
                    ticket_dict['assigned_to'] = ticket.assigned_to_name
                    ticket_dict['created_by'] = ticket.created_by_name
                ticket_dict['status'] = ticket.status
                ticket_dict['priority'] = ticket.priority
                ticket_dict['title'] = ticket.subject
                ticket_dict['type'] = ticket.ticket_type
                ticket_dict['category'] = ticket.category
                ticket_dict['created_at'] = ticket.created_at.strftime("%d/%m/%Y")
                ticket_dict['worklog'] = f"{work_log} / {estimated_time}"
                if ticket.deadline:
                    ticket_dict['deadline'] = ticket.deadline.strftime("%d/%m/%Y")
                else:
                    ticket_dict['deadline'] = '-'
                ticket_dict['updated_at'] = ticket.updated_at.strftime("%d/%m/%Y")
                ticket_dict['description'] = ticket_descriptions[f"{ticket.ticket_id}"]
                tickets.append(ticket_dict)

            response['pagination'] = {
                'total_pages': paginator.num_pages,
                'current_page': page_obj.number,
                'has_previous': page_obj.has_previous(),
                'has_next': page_obj.has_next(),
                'previous_page_number': page_obj.previous_page_number() if page_obj.number > 1 else 1,
                'next_page_number': page_obj.next_page_number() if page_obj.number < paginator.num_pages else paginator.num_pages,
            }
            response['open_count'] = open_count
            response['closed_count'] = closed_count
            response['tickets'] = tickets
            response['success'] = True
            response['message'] = 'Tickets Listed'

        except Exception as err:
            response['success'] = False
            response["error"] = settings.ERROR_MSG['application_error'].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
            response['status'] = 499
        return response


    def get_ticket_dropdown_params(self, request, project_id):
        response = {"project_status": [],"priority": [],"ticket_type": [],"ticket_category": [],"assigned_users": [],
            "watchers": [],"milestone": [],"project_repo": [],"project_modules": [],"error": None,"status": 200
        }
        project_status = settings.TICKETS_STATUS_CHOICES
        priority_choices = settings.TICKETS_PRIORITY_CHOICES
        ticket_type = settings.TICKETS_TYPE_CHOICES
        ticket_category = settings.TICKET_CATEGORIES

        try:
            user_id = request.user.id
            project_id = int(project_id)
            try:
                ticket_id = int(request.GET.get('ticket_id'))
            except:
                ticket_id = None

            if project_id != 0:
                project = ProjectDA().get_project_by_id(project_id)
                if not project:
                    response["error"] = "You have attempted to access an invalid project. Please contact your lead/manager for assistance."
                    response['status'] = 499
                    return response
                active_users = UserDA().get_all_active_users()
                active_users = {
                    user.id: {
                        "id": user.id,
                        "name": user.first_name + " " + user.last_name
                    } for user in active_users
                }
                project_employees_ids = ProjectDA().get_all_members_by_project(project_id).values_list('user_id', flat=True)
                manager_users = UserDA().get_all_managers()
                manager_users_ids = [user[2] for user in manager_users[0]]
                project_users = [ user_info for user_id, user_info in active_users.items() if user_id in project_employees_ids or user_id in manager_users_ids ]
                response['project_users'] = project_users
                role_id, role_name = UserDA().get_user_role_by_id(user_id)
                project_tickets = self.__helper.get_parent_dropdown([project_id],ticket_id,settings.TICKET_STATUS_OPEN)
                
                #for project repo
                project_repo_names = self.__helper.get_all_repo_names_by_project_id(project_id)
                
                #for project module
                project_modules = self.__helper.get_all_project_modules_by_project_id(project_id)
                
                response["project_repo"] = project_repo_names
                response["project_modules"] = project_modules
                response["project_tickets"] = project_tickets
                response['watchers'], response['assigned_users'] = self.__helper.get_watchers_and_assigned_users(user_id=user_id, role_id=role_id, project_id=project_id, ticket_id=ticket_id)
                response["project_status"] = project_status
                response["priority"] = priority_choices
                response["ticket_type"] = ticket_type
                response["ticket_category"] = ticket_category
                response['success'] = True

        except Exception as err:
            response['success'] = False
            response["error"] = settings.ERROR_MSG['application_error'].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
            response['status'] = 499
        return response


    def get_all_projects_dropdown(self,request):
        response = {"status": 200, "projects": [], "error":None}
        try:
            user_id = request.user.id
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            is_manager = self.is_manager(role_id)
            if is_manager:
                user_projects = ProjectDA().get_all_projects()
            else:
                user_projects = ProjectDA().get_all_user_projects(user_id)

            if user_projects:
                user_projects = user_projects.order_by("name")
                for project in user_projects:
                    project_dict = {
                        "project_id":f"{project.project_id}",
                        "project_name":f"{project.name}",
                    }
                    response["projects"].append(project_dict)

            #Get preferred project ID
            employee_projects = ProjectDA().get_project_user_mapping(user_id)
            if employee_projects:
                preferred_project = employee_projects.filter(is_preferred_project=1).last()
                if preferred_project:
                    preferred_project_id = preferred_project.project_id
                    response['preferred_project_id'] = preferred_project_id
        except Exception as err:
            response['success'] = False
            response["error"] = settings.ERROR_MSG['application_error'].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
            response['status'] = 499
        return response


    def create_ticket(self, request):
        response = {"success": False, "error": "", "status": 200}
        try:
            request_data = request.data

            user_id = request.user.id
            role_id, role_name = UserDA().get_user_role_by_id(user_id)

            #Set Project Details
            project_id = int(request_data.get('project_id', 0))
            project = ProjectDA().get_project_by_id(project_id)
            if not project:
                response["error"] = "You have attempted to access an invalid project. Please contact your lead/manager for assistance."
                response['status'] = 499
                return response
            project_name = project.name

            is_part_of_project = self.is_project_accessible(user_id, project_id)
            is_manager = self.is_manager(role_id)
            if not is_manager and not is_part_of_project:
                response["error"] = settings.ERROR_MSG.get("access_denied")
                response["status"] = 403
                return response

            assigned_to = request_data.get('assigned_to', 0)
            start_date = request_data.get('start_date', None)
            end_date = request_data.get('end_date', None)
            deadline = request_data.get('deadline', None)
            estimated_time = request_data.get('estimated_time', 0)
            log_time = request_data.get('log_time',0)
            log_date = request_data.get('log_date', None)
            is_private = request_data.get('is_private')
            milestone = request_data.get('milestone')
            file_objs = request_data.getlist('attachments')
            watchers = request_data.getlist('ticket_watchers')
            tag_name = request_data.get('tag_name')
            action = request_data.get('ticket_details')
            try:
                parent_id = int(request_data.get('parent_id', 0))
            except:
                parent_id = 0
            repo_uri = request_data.get('repo_uri', None)
            is_cicd_merged = int(request_data.get('is_cicd_merged')) if request_data.get('is_cicd_merged') else 0
            try:
                is_cicd_enabled = int(request_data.get('is_cicd_enabled', 0))
            except:
                is_cicd_enabled = 0
            try:
                repo_id = int(request_data.get('repo_id'))
            except:
                repo_id = 0
            try:
                module_id = int(request_data.get('module_id', 0))
            except:
                module_id = 0


            #Title Validation length
            subject = request_data.get('subject', '')
            if not self.__validator.is_str_length_valid(subject, 250):
                response['error'] = 'The title should be concise and clear, with a limit of 250 characters.'
                response["status"] = 499
                return response

            #Title validation
            error, subject = self.__validator.message_validator(subject)
            if error:
                response['error'] = 'Invalid "Title" field. Your title may have triggered one or more of the following issues: it contains only numbers, only special characters, is empty, is shorter than 4 characters, or includes non-ASCII or non-UTF characters'
                response["status"] = 499
                return response

            #Message validation
            message = request_data.get('message', '')
            error, message = self.__validator.message_validator(message)
            if error:
                response['error'] = error
                response["status"] = 499
                return response
            
            #repo_id validate
            if repo_id:
                is_repo_id_valid = self.__validator.repo_id_vallidate(repo_id)
                if is_repo_id_valid['error']:
                    response["error"] = is_repo_id_valid['error']
                    response['status'] = 499
                    return response
            
            #module_id validate
            if module_id:
                is_module_id_valid = self.__validator.module_id_vallidate(module_id)
                if is_module_id_valid['error']:
                    response["error"] = is_module_id_valid['error']
                    response['status'] = 499
                    return response

            #Status validation
            status = request_data.get('status')
            if not self.__validator.is_ticket_status_valid(status, True):
                response['error'] = "When creating a new ticket, the status should be set to 'New'."
                response["status"] = 499
                return response

            #Priority validation
            priority = request_data.get('priority')
            if not self.__validator.is_ticket_priority_valid(priority):
                response['error'] = "Invalid ticket 'Priority' selected."
                response["status"] = 499
                return response

            #Type validation
            ticket_type = request_data.get('ticket_type')
            if not self.__validator.is_ticket_type_valid(ticket_type):
                response['error'] = "Invalid ticket 'Type' selecetd."
                response["status"] = 499
                return response

            #Category validation
            category = request_data.get('ticket_category')
            if not self.__validator.is_ticket_category_valid(category):
                response['error'] = "Invalid ticket 'Category' selecetd."
                response["status"] = 499
                return response

            #Parent Validator
            if parent_id:
                if not self.__validator.is_parent_valid(parent_id, project_id):
                    response["error"] = "Invalid ticket selected as parent"
                    response["status"] = 499
                    return response

            if not self.__validator.is_str_length_valid(tag_name, 100):
                response['error'] = 'The "Tag" should be a limit of 100 characters.'
                response["status"] = 499
                return response

            #Log Time Validator
            log_time_response = self.__validator.time_log_validtor(log_time,log_date,user_id)
            if log_time_response['error']:
                return log_time_response
            log_time = log_time_response['log_time']
            log_date = log_time_response['log_date']

            #File Validations
            if file_objs:
                response = self.__validator.validate_files(file_objs)
                if response["error"]:
                    return response

            #progress dates validator
            date_response = self.__validator.validate_progress_dates(start_date=start_date,end_date=end_date,deadline=deadline,status=status)
            if date_response["error"]:
                return date_response
            start_date = date_response['start_date']
            end_date = date_response['end_date']
            deadline = date_response['deadline']

            watchers = self.__helper.setup_watchers(project_id, watchers, user_id, assigned_to)

            estimated_time_sec = 0
            if estimated_time not in [0,'0','null',None,'None']:
                estimated_time_sec = int(estimated_time) * 60

            estimated_time_err_msg = self.__validator.estimated_time_validation(estimated_time_sec, status)
            if estimated_time_err_msg:
                response["error"] = estimated_time_err_msg
                response["status"] = 499
                return response

            ticket_header_data = {
                'project_id': project_id,
                'subject': subject,
                'status': status,
                'priority': priority,
                'ticket_type': ticket_type,
                'assigned_to': assigned_to,
                'estimated_time': estimated_time_sec,
                'is_private': is_private,
                'milestone': milestone,
                'tag_name': tag_name,
                'created_by': user_id,
                'parent_id': parent_id,
                'category': category,
                'repo_id': repo_id,
                'repo_uri': repo_uri,
                'is_cicd_enabled': is_cicd_enabled,
                'is_cicd_merged': is_cicd_merged,
                'module_id': module_id,
            }

            if start_date:
                ticket_header_data['start_date'] = start_date.strftime("%Y-%m-%d")

            if deadline:
                ticket_header_data['deadline'] = deadline.strftime("%Y-%m-%d")

            if end_date:
                ticket_header_data['end_date'] = end_date.strftime("%Y-%m-%d")

            with transaction.atomic():
                ticket_header = TicketDA().create_ticket_data_ticket_headers(ticket_header_data)
                if not ticket_header:
                    response['error'] = 'Ticket Create Unsuccessful'
                    response["status"] = 499
                    return response

                ticket_id = ticket_header.ticket_id

                ticket_details_data = {
                    'message': message,
                    'action': action,
                    'ticket_id': ticket_id,
                    'created_by': user_id,
                    'is_header': 1,
                    'status': status,
                    'priority': priority,
                    'ticket_type': ticket_type,
                    'assigned_to': assigned_to,
                    'category': category,
                    'estimated_time': estimated_time_sec,
                    'subject': subject,
                    'module_id': module_id,
                }

                if deadline:
                    ticket_details_data['deadline'] = deadline.strftime("%Y-%m-%d")

                is_ticket_details_created = TicketDA().create_ticket_data_ticket_details(ticket_details_data)
                if not is_ticket_details_created:
                        response['error'] = 'Ticket Create Unsuccessful'
                        response["status"] = 499
                        return response

                if log_date and log_time:
                    log_time_sec = log_time*60
                    ticket_time_data = {
                        'ticket_id': ticket_id,
                        'user_id': user_id,
                        'log_date': log_date,
                        'log_time': log_time_sec
                    }
                    TicketDA().create_ticket_log_time(ticket_time_data)

                #Create ticket attachements
                if ticket_id and file_objs:
                    ticket_details_id = is_ticket_details_created.ticket_details_id
                    for each_file in file_objs:
                        ticket_attachment_data = self.__helper.write_ticket_attachment(each_file, ticket_id, ticket_details_id)
                        if ticket_attachment_data:
                            TicketDA().create_ticket_data_ticket_attachments(ticket_attachment_data)

                #Create Ticket watchers
                ticket_watchers_data = {
                    f'{watcher}': {'watcher':f'{watcher}', 'ticket_id': ticket_header.ticket_id} for watcher in watchers
                }
                TicketDA().create_ticket_data_ticket_watcher(ticket_watchers_data)

                emp_name = f"{request.user.first_name} {request.user.last_name}"
                
                #Here we are going  GIT implementation                
                if is_cicd_enabled:
                    self.__helper.create_git_branch(user_id, repo_id, project_id, ticket_id, emp_name, project_name, list(watchers))
                
                #Send Email Notification
                self.__helper.send_ticket_event_email(message, ticket_header, emp_name, project_name, watchers)

                response['success'] = True
                response['message'] = f'A ticket with ID #{ticket_id} has been successfully created in the {project_name} project.'

        except Exception as err:
            response['success'] = False
            response["error"] = settings.ERROR_MSG['application_error'].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
            response["status"] = 499
        return response


    #For the purpose of bread crumb.
    def get_ticket_project_by_ticket_id(self, request, ticket_id):
        response = {"status": 200,"project_name": [],"error":None}
        project_id = 0

        try:
            ticket_id = int(ticket_id)
            user_id = request.user.id
            role_id, role_name = UserDA().get_user_role_by_id(user_id)

            ticket_head = TicketDA().get_ticket_head_by_ticket_id(ticket_id)
            if not ticket_head:
                response["error"] = "You have attempted to access an invalid ticket. Please contact your lead/manager for assistance."
                response["status"] = 403
                return response

            project_id = ticket_head.project_id

            is_part_of_project = self.is_project_accessible(user_id, project_id)
            is_manager = self.is_manager(role_id)
            if not is_manager and not is_part_of_project:
                response["error"] = settings.ERROR_MSG.get("access_denied")
                response["status"] = 403
                return response

            project = ProjectDA().get_project_by_id(project_id)
            if not project:
                response["error"] = "You have attempted to access an invalid project. Please contact your lead/manager for assistance."
                response["status"] = 499
                return response

            if project:
                response["project_name"] = project.name
        except Exception as err:
            response['success'] = False
            response["error"] = settings.ERROR_MSG['application_error'].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
            response["status"] = 499
        return response


    def get_ticket_details_by_ticket_id(self, request, ticket_id):
        response = {
            "status": [],
            "head": [],
            "ticket_details": [],
            "latest_tickets": [],
            "status_count":[],
            "is_comment_edit":False
            }
        ticket_attachment_data = None
        project_id = 0
        total_work_log = 0
        try:
            ticket_id = int(ticket_id)
            user_id = request.user.id
            role_id, role_name = UserDA().get_user_role_by_id(user_id)

            ticket_head = TicketDA().get_ticket_head_by_ticket_id(ticket_id)
            if not ticket_head:
                response["error"] = "You have attempted to access an invalid ticket. Please contact your lead/manager for assistance."
                response["status"] = 403
                return response

            project_id = ticket_head.project_id

            is_part_of_project = self.is_project_accessible(user_id, project_id)
            is_manager = self.is_manager(role_id)
            if not is_manager and not is_part_of_project:
                response["error"] = settings.ERROR_MSG.get("access_denied")
                response["status"] = 403
                return response

            project = ProjectDA().get_project_by_id(project_id)
            if not project:
                response["error"] = "You have attempted to access an invalid project. Please contact your lead/manager for assistance."
                response["status"] = 403
                return response

            all_users = UserDA().get_all_users()
            users = {}
            #users = { user.id : {"name": user.first_name + " " + user.last_name} for user in all_users }
            users = { user.id : user.first_name + " " + user.last_name for user in all_users }

            response["head"] = self.__helper.get_ticket_head_formatted(ticket_head, users)
            if project:
                response["head"]['project_name'] = project.name
            response["is_comment_edit"] = self.__helper.is_ticket_comment_editable(ticket_id, user_id)

            ticket_details_data = TicketDA().get_ticket_details_by_ticket_id(ticket_id)


            sub_tickets_response = self.__helper.get_all_sub_tickets(project_id,ticket_head.ticket_id)
            if sub_tickets_response['error']:
                response["error"] = sub_tickets_response['error']
                response["status"] = 403
                return response
            sub_tickets_dict = sub_tickets_response['sub_tickets_dict']
            sub_tickets_status_count = sub_tickets_response['status_counts']

            previous_comment = None
            ticket_details = []

            if ticket_details_data:
                ticket_attachments_dict = self.__helper.get_ticket_attachments(ticket_id)
                #time_spent_data
                ticket_details_response = self.__helper.get_ticket_time_spent(user_id, ticket_id, users)
                response["head"]['work_log'] = ticket_details_response['work_log_format']
                ticket_details.extend(ticket_details_response['ticket_details'])

                for current_comment in ticket_details_data:
                    ticket_message = current_comment.message
                    file_names = ticket_attachments_dict.get(current_comment.ticket_details_id,None)
                    if ticket_message or file_names:
                        ticket_details.append({
                            'type': 'Commented',
                            "message" : ticket_message,
                            "action" :  f"{users[current_comment.created_by]} commented on {current_comment.created_at.strftime('%A %d %b at %I:%M %p')}",
                            "files": file_names or [],
                            "created_at": current_comment.created_at
                        })

                    if not previous_comment:
                        previous_comment = current_comment
                        continue

                    #if previous_comment:
                    if previous_comment.status != current_comment.status:
                        status_lst = self.__helper.get_property_comment(current_comment, previous_comment, users, "Status")
                        if status_lst:
                            ticket_details.extend(status_lst)

                    if previous_comment.priority != current_comment.priority:
                        priority_lst = self.__helper.get_property_comment(current_comment, previous_comment, users, "Priority")
                        if priority_lst:
                            ticket_details.extend(priority_lst)

                    if previous_comment.ticket_type != current_comment.ticket_type:
                        type_lst = self.__helper.get_property_comment(current_comment, previous_comment, users, "Ticket Type")
                        if type_lst:
                            ticket_details.extend(type_lst)
                    
                    if previous_comment.subject != current_comment.subject:
                        type_lst = self.__helper.get_property_comment(current_comment, previous_comment, users, "Title")
                        if type_lst:
                            ticket_details.extend(type_lst)
                    
                    if previous_comment.module_id != current_comment.module_id:
                        type_lst = self.__helper.get_property_comment(current_comment, previous_comment, users, "Module")
                        if type_lst:
                            ticket_details.extend(type_lst)

                    if previous_comment.category != current_comment.category:
                        category_lst = self.__helper.get_property_comment(current_comment, previous_comment, users, "Category")
                        if category_lst:
                            ticket_details.extend(category_lst)

                    if previous_comment.deadline != current_comment.deadline:
                        eta_lst = self.__helper.get_property_comment(current_comment, previous_comment, users, "Deadline")
                        if eta_lst:
                            ticket_details.extend(eta_lst)

                    if previous_comment.assigned_to != current_comment.assigned_to:
                        assigne_lst = self.__helper.get_property_comment(current_comment, previous_comment, users, "Assignee")
                        if assigne_lst:
                            ticket_details.extend(assigne_lst)

                    if previous_comment.estimated_time != current_comment.estimated_time:
                        est_lst = self.__helper.get_property_comment(current_comment, previous_comment, users, "Estimated Time")
                        if est_lst:
                            ticket_details.extend(est_lst)

                    previous_comment = current_comment
            ticket_details = sorted(ticket_details, key=lambda x: x["created_at"])
            for ticket_detail in ticket_details:
                del ticket_detail["created_at"]

            # response['sub_tickets'] = list(sub_tickets_dict.values())
            per_page = 10
            sub_ticket_count = len(sub_tickets_dict)
            total_pages = int(sub_ticket_count/per_page) + 1 if (sub_ticket_count % per_page) != 0 else int(sub_ticket_count/per_page)

            response['sub_tickets'] = []
            response['paginated_results'] = {}
            response['total_pages'] = [ i for i in range(1,total_pages+1)]

            for idx, ticket in enumerate(sub_tickets_dict.values()):
                response['sub_tickets'].append(ticket)
                current_page = int(idx/per_page) + 1
                if not current_page in response['paginated_results']:
                    response['paginated_results'][current_page] = []
                response['paginated_results'][current_page].append(ticket)
            response["ticket_details"] = ticket_details
            response['status_count'] = sub_tickets_status_count

        except Exception as err:
            response['success'] = False
            response["error"] = settings.ERROR_MSG['application_error'].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response

    def update_log_time(self, ticket_id, user_id, ticket_header, log_date, log_time, project_id):
        response = {"status": 200, "projects": [], "success": False, "error": ""}
        try:
            #Time Log Validation
            log_time_response = self.__validator.time_log_validtor(log_time,log_date,user_id,ticket_header)            
            if log_time_response['error']:
                return log_time_response
            log_time = log_time_response['log_time']
            log_date = log_time_response['log_date']
            
            previous_update = TicketDA().get_ticket_details_by_ticket_id_last(ticket_id)
            if not previous_update:
                response['error'] = 'Ticket Update Unsuccessful'
                response["status"] = 499
                return response

            project = ProjectDA().get_project_by_id(project_id)
            project_name = project.name if project else "-"
            ticket_details_data = {
                    'action': 'Property Changed',
                    'ticket_id': ticket_id,
                    'created_by': user_id,
                    'status': previous_update.status,
                    'priority': previous_update.priority,
                    'ticket_type': previous_update.ticket_type,
                    'assigned_to': previous_update.assigned_to,
                    'deadline': previous_update.deadline,
                    'category': previous_update.category,
                    'estimated_time': previous_update.estimated_time,
                }

            if ticket_details_data:
                is_ticket_details_updated = TicketDA().create_ticket_data_ticket_details(ticket_details_data)

            if not is_ticket_details_updated:
                response['error'] = 'Ticket Update Unsuccessful'
                response["status"] = 499
                return response

            #Time Log
            if log_date and log_time:
                log_time_sec = log_time*60
                ticket_time_data = {
                    'ticket_id': ticket_id,
                    'user_id': user_id,
                    'log_date': log_date,
                    'log_time': log_time_sec
                }
                TicketDA().create_ticket_log_time(ticket_time_data)
            response['success'] = True
            response['message'] = f'The ticket with ID #{ticket_id} has been successfully updated in the {project_name} project.'
        except Exception as err:
            response['success'] = False
            response["error"] = settings.ERROR_MSG['application_error'].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response

    def update_ticket(self, request, ticket_id):
        response = {"status": 200, "projects": [], "success": False, "error": ""}
        status_complete = 'completed'

        ci_cd_decision_matrix = {'branch_create':0, 'branch_delete':0, 'branch_merge':0, 'current_repo_id':0, 'new_repo_id':0}

        try:

            ticket_id = int(ticket_id)
            request_data = request.data
            watchers_list=[]
            ticket_header = TicketDA().get_ticket_head_by_ticket_id(ticket_id)
            if not ticket_header:
                response["error"] = settings.ERROR_MSG.get("access_denied")
                response["status"] = 403
                return response

            user_id = request.user.id
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            is_manager = self.is_manager(role_id)
            project_id = ticket_header.project_id #request_data.get('project_id')

            is_part_of_project = self.is_project_accessible(user_id, project_id)
            if not is_manager and not is_part_of_project:
                response["error"] = settings.ERROR_MSG.get("access_denied")
                response["status"] = 403
                return response

            #Edit a comment after posting with in 5 min
            edit_message = request_data.get('edit_message')
            if edit_message:
                error, edit_message = self.__validator.message_validator(edit_message)
                if error:
                    response['error'] = error
                    response["status"] = 499
                    return response
                response = self.__helper.edit_ticket_comment(ticket_id, edit_message)
                response['success'] = True
                return response


            assigned_to = request_data.get('assigned_to',0)
            log_time = request_data.get('log_time',0)
            log_date = request_data.get('log_date', None)
            start_date = request_data.get('start_date', None)
            end_date = request_data.get('end_date', None)
            deadline = request_data.get('deadline', None)
            estimated_time = request_data.get('estimated_time')
            is_private = 0
            milestone = ''
            file_objs = request_data.getlist('attachments')
            watchers = list(set(request_data.getlist('ticket_watchers')))
            tag_name = request_data.get('tag_name')
            parent_id = int(request_data.get('parent_id')) if request_data.get('parent_id') else 0
            #ticket_category = request_data.get('ticket_category')
            parent_changed = int(request_data.get('parent_changed')) if request_data.get('parent_changed') else 0
            message = request_data.get('message', '')
            status = request_data.get('status')
            priority = request_data.get('priority')
            ticket_type = request_data.get('ticket_type')
            ticket_category = request_data.get('ticket_category')
            subject = request_data.get('subject', '')
            #repo_id = request_data.get('repo_id', 0)
            #repo_url = request_data.get('repo_url', '')
            # try:
            #     is_cicd_enabled = request_data.get('is_cicd_enabled', 0)
            # except:
            #     is_cicd_enabled = 0

            #repo_uri = request_data.get('repo_uri', None)
            #TODO need to update in front end
            #is_cicd_merged = int(request_data.get('is_cicd_merged')) if request_data.get('is_cicd_merged') else 0
            current_watchers = TicketDA().get_ticket_watchers_by_ticket_id(ticket_id).values_list('watcher', flat=True)
            watchers_list = list({int(watcher) for watcher in watchers})

            if assigned_to not in ('', '0', 0, None):
                obj_assign = UserDA().get_user_by_id(assigned_to)
                if obj_assign and obj_assign.is_active==0:
                    if assigned_to in watchers_list:
                        watchers_list.remove(assigned_to)
                    try:
                        assigned_to = ProjectDA().get_project_leads_by_project_id(project_id).first().user_id
                    except:
                        assigned_to = 0                
            
            try:
                repo_id = int(request_data.get('repo_id'))
            except:
                repo_id = 0
            try:
                is_cicd_enabled = int(request_data.get('is_cicd_enabled', 0))
            except:
                is_cicd_enabled = 0
            try:
                module_id = int(request_data.get('module_id', 0))
            except:
                module_id = 0
                

            if estimated_time not in [0,'0','null',None,'None']:
                estimated_time_sec = int(estimated_time) * 60
            else:
                estimated_time_sec = 0

            if log_time:
                log_time = int(log_time)

            conditions = [
                ticket_header.status == status,
                ticket_header.priority == priority,
                ticket_header.ticket_type == ticket_type,
                ticket_header.assigned_to == int(assigned_to),
                ticket_header.estimated_time == estimated_time_sec,
                ticket_header.deadline == self.__validator.date_to_datetime(deadline),
                ticket_header.start_date == self.__validator.date_to_datetime(start_date),
                ticket_header.end_date == self.__validator.date_to_datetime(end_date),
                ticket_header.tag_name == tag_name,
                ticket_header.parent_id == parent_id,
                ticket_header.category == ticket_category,                
                not log_date,
                not log_time,
                set(watchers_list) == set(current_watchers),
                not file_objs,
                ticket_header.subject == subject,
                ticket_header.repo_id == repo_id,
                ticket_header.is_cicd_enabled == is_cicd_enabled,
                ticket_header.module_id == module_id
            ]
            

            #Block a update request with out any chages
            if not message and not edit_message:
                if all(conditions):
                    response["error"] = "Why did you try to update it? I can't see any changes!"
                    response["status"] = 499
                    return response
                
            is_ticket_parent = TicketDA().get_children_tickets(ticket_id)
            if is_ticket_parent and ticket_header.module_id != module_id:
                    response["error"] = "This ticket is parent to other ticket(s), you cannot edit a parent ticket\'s module!"
                    response["status"] = 499
                    return response

            #Save Log Time
            conditions.pop(11)  # Remove 'not log_date'
            conditions.pop(11)  # Remove 'not log_time'
            if log_time and all(conditions):
                response = self.update_log_time(ticket_id, user_id, ticket_header, log_date, log_time, project_id)
                return response

            # #repo_id validate
            # if repo_id:
            #     is_repo_id_valid = self.__validator.repo_id_vallidate(repo_id)
            #     if is_repo_id_valid['error']:
            #         response["error"] = is_repo_id_valid['error']
            #         response['status'] = 499
            #         return response
            
            #module_id validate
            if module_id:
                is_module_id_valid = self.__validator.module_id_vallidate(module_id)
                if is_module_id_valid['error']:
                    response["error"] = is_module_id_valid['error']
                    response['status'] = 499
                    return response 
            
            #Status validation
            if not self.__validator.is_ticket_status_valid(status):
                response['error'] = "Invalid ticket 'Status' selecetd."
                response["status"] = 499
                return response
            
            status_err = self.__validator.check_ticket_status_validty(ticket_header.status, status) 
            if status_err:
                response['error'] = status_err
                response["status"] = 499
                return response
            
            #Title Validation length
            if not self.__validator.is_str_length_valid(subject, 250):
                response['error'] = 'The title should be concise and clear, with a limit of 250 characters.'
                response["status"] = 499
                return response


            #Title validation
            error, subject = self.__validator.message_validator(subject)
            if error:
                response["error"] = 'Invalid "Title" field. Your title may have triggered one or more of the following issues: it contains only numbers, only special characters, is empty, is shorter than 4 characters, or includes non-ASCII or non-UTF characters'
                response["status"] = 499
                return response

            #sub tickets
            sub_tickets_response = self.__helper.get_all_sub_tickets(project_id,ticket_id)
            if sub_tickets_response['error']:
                response["error"] = sub_tickets_response['error']
                response["status"] = 403
                return response
            sub_tickets_dict = sub_tickets_response['sub_tickets_dict']

            # sub ticket completetion validator
            response = self.__validator.check_sub_tickets_completion(sub_tickets_dict,status)
            if response["error"]:
                return response

            #Reopen status validation
            previous_status = ticket_header.status
            error_msg = self.__validator.reopen_status_valid(status, previous_status)
            if error_msg:
                response['error'] = error_msg
                response["status"] = 499
                return response

            #forced_to_reopen
            previous_status = ticket_header.status
            error_msg = self.__validator.forced_to_reopen(previous_status, status)
            if error_msg:
                response['error'] = error_msg
                response["status"] = 499
                return response

            #Priority validation
            if not self.__validator.is_ticket_priority_valid(priority):
                response['error'] = "Invalid ticket 'Priority' selecetd."
                response["status"] = 499
                return response

            #Type validation
            if not self.__validator.is_ticket_type_valid(ticket_type):
                response['error'] = "Invalid ticket 'Type' selecetd."
                response["status"] = 499
                return response

            #Category validation
            if not self.__validator.is_ticket_category_valid(ticket_category):
                response['error'] = "Invalid ticket 'Category' selecetd."
                response["status"] = 499
                return response

            if parent_id:
                is_parent =  self.__validator.is_parent_valid(parent_id, project_id, ticket_id)
                if not is_parent:
                    response["error"] = "Invalid ticket selected as parent"
                    response["status"] = 499
                    return response

                if self.__validator.check_for_circular_parent_v1(parent_id, ticket_id):
                    response["error"] = "Circular parent-child relationship detected."
                    response["status"] = 499
                    return response



            # parent id validating if parent_id
            if not parent_id and not parent_changed:
                parent_id = ticket_header.parent_id


            #logic to handle child ticket change to be reflected in parent ticket
            # sub ticket completetion validator
            if parent_id:
                response = self.__validator.validate_parent_ticket_status_by_child(parent_id, status)
                if response["error"]:
                    return response            

            #progress dates validator
            response = self.__validator.validate_progress_dates(start_date=start_date,end_date=end_date,deadline=deadline,status=status,ticket=ticket_header)
            if response["error"]:
                return response
            start_date = response['start_date']
            end_date = response['end_date']
            deadline = response['deadline']

            if str(status).lower() == status_complete:
                if not start_date:
                    response['error'] = 'Start date is required.'
                    response["status"] = 499
                    return response
            if str(status).lower() == status_complete:
                if not end_date:
                    response['error'] = 'End date is required.'
                    response["status"] = 499
                    return response

            # if estimated_time not in [0,'0','null',None,'None']:
            #     estimated_time_sec = int(estimated_time) * 60
            # else:
            #     estimated_time_sec = 0
            estimated_time_err_msg = self.__validator.estimated_time_validation(estimated_time_sec, status)
            if estimated_time_err_msg:
                response["error"] = estimated_time_err_msg
                response["status"] = 499
                return response



            #Time Log Validation
            log_time_response = self.__validator.time_log_validtor(log_time,log_date,user_id,ticket_header)
            if log_time_response['error']:
                return log_time_response
            log_time = log_time_response['log_time']
            log_date = log_time_response['log_date']

            #Message validation
            if message:
                error, message = self.__validator.message_validator(message)
                if error:
                    response['error'] = error
                    response["status"] = 499
                    return response
            else:
                if ticket_header.status != status:
                    response = self.__validator.message_validate_by_status(status=status)
                    if response["error"]:
                        return response

            #File Validations
            if file_objs:
                response = self.__validator.validate_files(file_objs)
                if response["error"]:
                    return response

            if str(status).lower() == status_complete:
                if not start_date:
                    response['error'] = 'Start date is required.'
                    response["status"] = 499
                    return response
            if str(status).lower() == status_complete:
                if not end_date:
                    response['error'] = 'End date is required.'
                    response["status"] = 499
                    return response            

            
            #CI-CD validation
            if ticket_header.is_cicd_merged == 1:
                if ticket_header.is_cicd_enabled != is_cicd_enabled:
                    response['error'] = 'This ticket already merged. no changes allowed'
                    response["status"] = 499
                
                if ticket_header.repo_id != repo_id:
                    response['error'] = 'This ticket already merged. no changes allowed'
                    response["status"] = 499

            else:
                # 1. repo add , 2. repo change,  3. repo delete, 4. merge
                if ticket_header.is_cicd_enabled == 0 and is_cicd_enabled==1:
                     #create branch
                     ci_cd_decision_matrix['branch_create'] = 1
                if ticket_header.is_cicd_enabled == 1 and is_cicd_enabled==0:
                     #delete branch
                     ci_cd_decision_matrix['branch_delete'] = 1
                     ci_cd_decision_matrix['current_repo_id'] = ticket_header.repo_id
                     ci_cd_decision_matrix['new_repo_id'] = repo_id

                if ticket_header.is_cicd_enabled == 1 and is_cicd_enabled==1:
                    if ticket_header.repo_id != repo_id:
                        #delete branch
                        ci_cd_decision_matrix['branch_delete'] = 1
                        #create branch
                        ci_cd_decision_matrix['branch_create'] = 1
                        ci_cd_decision_matrix['current_repo_id'] = ticket_header.repo_id
                        ci_cd_decision_matrix['new_repo_id'] = repo_id

                if ticket_header.is_cicd_enabled == 1 and is_cicd_enabled==1:
                    #Check status ticket_header.status == status
                    if str(status).lower() == 'readypushpro':
                        if str(ticket_header.status).lower() != 'verified by qa':
                            response['error'] = "This ticket is CI/CD enabled, so it should be verified by QA before being moved to the 'Ready to Push' status."
                            response["status"] = 499
                        else:
                            #DO merging
                            ci_cd_decision_matrix['branch_merge'] = 1

                    elif str(status).lower() == 'completed':
                        #if str(ticket_header.status).lower() != 'readypushpro':
                        response['error'] = "This ticket is CI/CD enabled, so it should be verified by QA and 'Ready to Push' before being moved to the 'Completed' status."
                        response["status"] = 499  


            project = ProjectDA().get_project_by_id(project_id)
            project_name = project.name if project else "-"

            if assigned_to not in ('', '0', 0, None) and assigned_to not in watchers:
                watchers.append(int(assigned_to))

            watchers = list(map(lambda x: int(x), watchers))

            ticket_header_data = {
                'status': status,
                'priority': priority,
                'ticket_type': ticket_type,
                'assigned_to': assigned_to,
                'estimated_time': estimated_time_sec,
                'is_private': is_private,
                'milestone': milestone,
                'tag_name': tag_name,
                'category': ticket_category,
                'subject': subject,
                'updated_at': timezone.now(),
                'start_date':None,
                'end_date':None,
                'deadline':None,
                'repo_id':repo_id,
                #'repo_uri':repo_uri,
                'is_cicd_enabled':is_cicd_enabled,
                #'is_cicd_merged':is_cicd_merged,
                'module_id': module_id,
            }

            if start_date:
                ticket_header_data['start_date'] = start_date.strftime("%Y-%m-%d")
            if end_date:
                ticket_header_data['end_date'] = end_date.strftime("%Y-%m-%d")
            if deadline:
                ticket_header_data['deadline'] = deadline.strftime("%Y-%m-%d")

            assigned_to = int(assigned_to)
            create_watcher_list = []
            delete_watcher_list = []

            if message:
                message = mark_safe(message)
            else:
                message = ''

            created_watcher = ""
            delete_watcher = ""
            active_users = UserDA().get_all_active_users()
            users = { user.id : {"id": user.id, "name": user.first_name + " " + user.last_name, "username": user.username, "email": user.email, "is_active": user.is_active} for user in active_users }

            deleted_users = UserDA().get_all_non_active_users()
            non_active_users = { user.id : {"id": user.id, "name": user.first_name + " " + user.last_name, "username": user.username, "email": user.email, "is_active": user.is_active} for user in deleted_users }

            for watcher in watchers:
                if not int(watcher) in current_watchers:
                    create_watcher_list.append(int(watcher))
                    if created_watcher:
                        created_watcher += ", "
                    created_watcher += users.get(watcher, None)['name']
            for watcher in current_watchers:
                if not int(watcher) in watchers:
                    delete_watcher_list.append(int(watcher))
                    if delete_watcher:
                        delete_watcher += ", "
                    delete_watcher += users.get(watcher, None)['name']

            #Add lead of a project to watchers list:
            project_leads = ProjectDA().get_project_leads_by_project_id(project_id)
            if project_leads:
                for lead in project_leads:
                    if int(lead.user_id) not in delete_watcher_list:
                        watchers.append(int(lead.user_id))
            ticket_changes = []
            user_name = users.get(user_id, None)
            assigned_user_name = users.get(assigned_to, None)
            if ticket_header.assigned_to:
                old_assignee = users.get(ticket_header.assigned_to, None)
                if not old_assignee:
                    old_assignee = non_active_users.get(ticket_header.assigned_to, None)
                
                old_assignee_name = old_assignee.get('name', "No Name")

            else:
                old_assignee_name = "No name"

            if ticket_header.status != status:
                ticket_changes.append(f"Changed status from {ticket_header.status} to {status}. \n")
            if ticket_header.priority != priority:
                ticket_changes.append(f"Changed priority from {ticket_header.priority} to {priority}. \n")
            if ticket_header.ticket_type != ticket_type:
                ticket_changes.append(f"Changed ticket type from {ticket_header.ticket_type} to {ticket_type}. \n")
            if ticket_header.subject != subject:
                ticket_changes.append(f"Changed ticket title from {ticket_header.subject} to {subject}. \n")

            if ticket_header.category != ticket_category:
                category_old = "No Category" if ticket_header.category in ("null", None, "None", 0, "0", '') else ticket_header.category
                category_new = "No Category" if ticket_category in ("null", None, "None", 0, "0", '') else ticket_category
                ticket_changes.append(f"Changed ticket category from {category_old} to {category_new}. \n")

            if ticket_header.assigned_to != assigned_to:
                ticket_changes.append(f"Changed assignee from {old_assignee_name} to {assigned_user_name['name'] if assigned_user_name else None }. \n")

            if ticket_header.estimated_time != estimated_time_sec:
                old_estimated = "No time" if ticket_header.estimated_time in ("null", None, "None", 0, "0") else self.__helper.ticket_time_format(ticket_header.estimated_time)
                ticket_changes.append(f"Changed estimated time from {old_estimated} to {self.__helper.ticket_time_format(estimated_time_sec)}. \n")
            if self.__validator.date_obj_to_date(ticket_header.deadline) != deadline and deadline:
                old_deadline = ticket_header.deadline.strftime("%d/%m/%Y") if ticket_header.deadline else "No date"
                ticket_changes.append(f"Changed deadline from {old_deadline} to {deadline.strftime('%d/%m/%Y')}. \n")
            if start_date and self.__validator.date_obj_to_date(ticket_header.start_date) != start_date:
                old_start_date = ticket_header.start_date.strftime("%d/%m/%Y") if ticket_header.start_date else "No date"
                ticket_changes.append(f"Changed start date from {old_start_date} to {start_date.strftime('%d/%m/%Y')}. \n")
            if end_date and self.__validator.date_obj_to_date(ticket_header.end_date) != end_date:
                old_end_date= ticket_header.end_date.strftime("%d/%m/%Y") if ticket_header.end_date else "No date"
                ticket_changes.append(f"Changed end date from {old_end_date} to {end_date.strftime('%d/%m/%Y')}. \n")

            if created_watcher:
                ticket_changes.append(f"{created_watcher} is added to the watcher's list. \n")
            if delete_watcher:
                ticket_changes.append(f"{delete_watcher} is removed from the watcher's list. \n")

            #parent id updating to ticket header also the changes are appended to the mail sending.
            if int(ticket_header.parent_id) != parent_id:
                current_parent_ticket = f"#{ticket_header.parent_id}" if ticket_header.parent_id else 'No Parent'
                changed_parent_ticket = f"#{parent_id}" if parent_id else 'No Parent'
                ticket_changes.append(f"Parent ticket changed from { current_parent_ticket } to { changed_parent_ticket } \n")

                ticket_header_data['parent_id'] = parent_id

            if message:
                action = 'Commented'
            else:
                action = 'Property Changed'

            #DB Update start here
            with transaction.atomic():

                if ticket_header_data:
                    is_ticket_header_updated = TicketDA().update_ticket_data_ticket_headers(
                        ticket_header_data, ticket_id)

                if not is_ticket_header_updated:
                        response['error'] = 'Ticket Update Unsuccessful'
                        response["status"] = 499
                        return response
                

                ticket_details_data = {
                    'message': message,
                    'action': action,
                    'ticket_id': ticket_id,
                    'created_by': user_id,
                    'status': status,
                    'priority': priority,
                    'ticket_type': ticket_type,
                    'assigned_to': assigned_to,
                    'deadline': deadline,
                    'category': ticket_category,
                    'estimated_time': estimated_time_sec,
                    'subject': subject,
                    'module_id': module_id,
                }

                if ticket_details_data:
                    is_ticket_details_updated = TicketDA().create_ticket_data_ticket_details(ticket_details_data)

                if not is_ticket_details_updated:
                    response['error'] = 'Ticket Update Unsuccessful'
                    response["status"] = 499
                    return response

                #Time Log
                if log_date and log_time:
                    log_time_sec = log_time*60
                    ticket_time_data = {
                        'ticket_id': ticket_id,
                        'user_id': user_id,
                        'log_date': log_date,
                        'log_time': log_time_sec
                    }
                    TicketDA().create_ticket_log_time(ticket_time_data)

                #Create ticket attachements
                if ticket_id and file_objs:
                    ticket_details_id = is_ticket_details_updated.ticket_details_id
                    for each_file in file_objs:
                        ticket_attachment_data = self.__helper.write_ticket_attachment(each_file, ticket_id, ticket_details_id)
                        if ticket_attachment_data:
                            TicketDA().create_ticket_data_ticket_attachments(ticket_attachment_data)

                if create_watcher_list:
                    create_watchers_data = {
                        f'{watcher}': {'watcher':f'{watcher}', 'ticket_id': ticket_id} for watcher in create_watcher_list
                    }
                    create_watcher_data = TicketDA().create_ticket_data_ticket_watcher(create_watchers_data)

                if delete_watcher_list:
                    delete_watcher_data = TicketDA().delete_ticket_data_ticket_watcher(ticket_id, delete_watcher_list)

                emp_name = f"{request.user.first_name} {request.user.last_name}"
                self.__helper.send_ticket_event_email(message, ticket_header, emp_name, project_name, watchers, False, ticket_changes)

                response['success'] = True
                response['message'] = f'The ticket with ID #{ticket_id} has been successfully updated in the {project_name} project.'

                #ci_cd_decision_matrix = {'branch_create':0, 'branch_delete':0, 'branch_merge':0}

                if ci_cd_decision_matrix.get('branch_delete', 0):
                    self.__helper.delete_git_branch(user_id, ci_cd_decision_matrix.get('current_repo_id',0), project_id, ticket_id, emp_name, project_name, watchers)
                if ci_cd_decision_matrix.get('branch_create', 0):
                     self.__helper.create_git_branch(user_id, repo_id, project_id, ticket_id, emp_name, project_name, watchers)
                if ci_cd_decision_matrix.get('branch_merge', 0):
                     self.__helper.merge_git_branch(user_id, repo_id, project_id, ticket_id, emp_name, project_name, watchers)



        except Exception as err:
            response['success'] = False
            response["error"] = settings.ERROR_MSG['application_error'].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
            response["status"] = 499
        return response


    def get_ticket_dashboard(self, request, project_id):
        response = {"summary_count": [], "developer_summary":[],"message": "","success": False,"error": None,"status": 200}

        try:
            user_id = request.user.id
            project_id = int(project_id)
            project = ProjectDA().get_project_by_id(project_id)
            # role_id, role_name = UserDA().get_user_role_by_id(user_id)
            if not project:
                response["error"] = "You have attempted to access an invalid project. Please contact your lead/manager for assistance."
                response['status'] = 499
                return response
            #if user_id:
            #for Sag
            # dashboard_response =  self.__helper.get_dashboard_details(user_id, role_id, project_id)
            dashboard_response =  self.__helper.get_dashboard_details(user_id,project_id)
            if dashboard_response['error']:
                response['error'] = dashboard_response['error']
                response['status'] = 499
                return dashboard_response
            ticket_dict = dashboard_response['ticket_dict']
            project_user_dict = dashboard_response['project_user_dict']
            response["summary_count"] = [ticket_dict]
            response["developer_summary"] = list(project_user_dict.values())
            response['success'] = True
        except Exception as err:
            response['success'] = False
            response["error"] = settings.ERROR_MSG['application_error'].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
            response['status'] = 499
        del ticket_dict, project_user_dict
        return response


    def get_sub_ticket_details(self, request, project_id, ticket_id):
        response = {}

        try:
            user_id = request.user.id
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            is_part_of_project = self.is_project_accessible(user_id, project_id)
            is_manager = self.is_manager(role_id)
            if not is_manager and not is_part_of_project:
                response["error"] = settings.ERROR_MSG.get("access_denied")
                response["status"] = 403
                return response
            project = ProjectDA().get_project_by_id(project_id)
            if not project:
                response["error"] = "You have attempted to access an invalid project. Please contact your lead/manager for assistance."
                response['status'] = 499
                return response
            ticket = TicketDA().get_ticket_by_ticket_id(ticket_id)
            if not ticket:
                response["error"] = "You have attempted to access an invalid ticket. Please contact your lead/manager for assistance."
                response['status'] = 499
                return response

            sub_tickets_response = self.__helper.get_all_sub_tickets(project_id, ticket_id)
            if sub_tickets_response['error']:
                response["error"] = "This ticket doesn't have any subtickets"
                response['status'] = 499
                return response
            sub_ticket_dict = sub_tickets_response['sub_tickets_dict']
            # response['sub_tickets'] = [ ticket for ticket in sub_ticket_dict.values() ]

            per_page = 10
            sub_ticket_count = len(sub_ticket_dict)
            total_pages = int(sub_ticket_count/per_page) + 1 if (sub_ticket_count % per_page) != 0 else int(sub_ticket_count/per_page)

            response['sub_tickets'] = []
            response['paginated_results'] = {}
            response['total_pages'] = [ i for i in range(1,total_pages+1)]

            for idx, ticket in enumerate(sub_ticket_dict.values()):
                response['sub_tickets'].append(ticket)
                current_page = int(idx/per_page) + 1
                if not current_page in response['paginated_results']:
                    response['paginated_results'][current_page] = []
                response['paginated_results'][current_page].append(ticket)


        except Exception as err:
            response['success'] = False
            response["error"] = settings.ERROR_MSG['application_error'].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
            response['status'] = 499
        return response


    def create_or_update_preferred_project(self, request):
        response = {
            "message": "",
            "success": True,
            "error": None,
            "status": 200
        }
        try:
            user_id = request.user.id
            preferred_project = int(request.data.get('preferred_project'))
            res = self.__helper.configure_preferred_project(user_id, preferred_project)
            response['message'] = res['message']
            if res["error"]:
                response["error"] = res["error"]
                response['status'] = 499
        except Exception as err:
            response['success'] = False
            response["error"] = settings.ERROR_MSG['application_error'].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
            response['status'] = 499
        return response


    def is_project_accessible(self, user_id, project_id):
        return ProjectDA().is_project_accessible(project_id, user_id)


    def check_whether_user_is_watcher_of_ticket(self, user_id, ticket_id):
        is_watcher = False
        ticket_watchers = TicketDA().get_ticket_watchers_by_ticket_id(ticket_id).values_list('watcher', flat=True)
        if user_id in ticket_watchers:
            is_watcher = True
        return is_watcher


    def is_manager(self, role_id):
        is_manager = False
        if role_id in (1, '1', 2, '2', 3, '3'):
            is_manager = True
        return is_manager