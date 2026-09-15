import os
import uuid
import base64
from datetime import timedelta



from types import SimpleNamespace


from django.utils import timezone
from django.db import  transaction
from django.conf import settings
from django.db.models import Q
from datetime import datetime

from cryptography.fernet import Fernet

from pTracker.common.utility import Utility
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.common.logs import Logs
from pTracker.dataaccess.ptracker_access.ticket_da import TicketDA
from pTracker.dataaccess.ptracker_access.user_da import UserDA
from pTracker.dataaccess.ptracker_access.project_da import ProjectDA
from pTracker.api.ticket.notification_biz import NotificationBL
from pTracker.dataaccess.ptracker_access.holiday_da import HolidayDA
from pTracker.common.file_manager import FileManager
from pTracker.continuous_integration.git_lab import GitLabEngine


def new_dto():
    dto = SimpleNamespace()
    return dto

class TicketHelperBL():
    def __init__(self):
        self.__exception = ExceptionHandler()
        self.__utility = Utility()
        self.__log = Logs()
        self.cipher_suite = Fernet(settings.FERNET_KEY)
        self.__file_manager = FileManager()

    #Get the parent tickets that's want to choose.
    def get_parent_dropdown(self,project_ids,ticket_id,TICKET_STATUS_OPEN):

        try:
            project_tickets = []
            filter_criteria = {}
            filter_criteria['project_id__in'] = project_ids
            filter_criteria['status__in'] = TICKET_STATUS_OPEN
            project_tickets = TicketDA().get_all_tickets_filtered(filter_criteria)

            # if ticket_id then exclude the child tickets of the current ticket_id
            if ticket_id:
                project_tickets = project_tickets.filter(~Q(parent_id=ticket_id) & ~Q(ticket_id=ticket_id))
            project_tickets = [
                {
                    'ticket_id' : ticket.ticket_id,
                    'title' : ticket.subject,
                    'module_id': ticket.module_id,
                }
                for ticket in project_tickets
            ]

            if ticket_id:
                current_ticket = TicketDA().get_ticket_by_ticket_id(ticket_id)
                if not list(filter(lambda ticket: ticket['ticket_id'] == current_ticket.parent_id, project_tickets)):

                    parent_ticket = TicketDA().get_ticket_by_ticket_id(current_ticket.parent_id)
                    if parent_ticket:
                        project_tickets.append(
                            {
                                'ticket_id': parent_ticket.ticket_id,
                                'title': parent_ticket.subject,
                                'module_id': parent_ticket.module_id,
                            }
                        )
        except Exception as err:
            return project_tickets
        return project_tickets


    def get_ticket_sub_task_count(self,project_id):
        ticket_dict = {}
        tickets = TicketDA().get_all_tickets_by_project(project_id)
        if tickets:
            for ticket in tickets:
                parent_id = ticket.parent_id
                if not parent_id:
                    continue
                if parent_id in ticket_dict:
                    ticket_dict[parent_id] = ticket_dict[parent_id] +1
                else:
                    ticket_dict[parent_id] = 1
        return ticket_dict


    def get_all_sub_tickets(self, project_id, ticket_id):
        response = {"error": "", "sub_tickets_dict":{}, "status_counts":[]}

        sub_tickets = []
        ticket_ids = []
        sub_tickets_dict = {}
        total_logged_time = {}
        user_first_names = {}
        filter_criteria ={}
        
        status_counts = {
            'new': 0,
            'in progress': 0,
            'resolved': 0,
            'released to qa': 0,
            'verified by qa': 0,
            'reopen': 0,
            'readypushpro': 0,
            'completed': 0,
            'invalid': 0,
            'deferred': 0
        }

        try:

            active_users = UserDA().get_all_active_users()
            user_first_names = { user.id : {"name": user.first_name} for user in active_users }

            #sub tickets count with project id.
            ticket_count_dict = self.get_ticket_sub_task_count(project_id)

            #Get all subtask from ticket header
            filter_criteria['parent_id'] = ticket_id
            # filter_criteria['status__in'] = settings.TICKET_STATUS_OPEN
            sub_tickets = TicketDA().get_all_tickets_filtered(filter_criteria)
            ticket_ids = [ticket.ticket_id for ticket in sub_tickets]
            if ticket_ids:
                total_logged_time = self.get_work_logs_by_ticket_ids(ticket_ids)
            if sub_tickets:
                for ticket in sub_tickets:
                    #getting the sub_ticket_count with respective ticket id.
                    sub_ticket_count = ticket_count_dict.get(ticket.ticket_id, 0)
                    estimated_time = self.ticket_time_format(ticket.estimated_time)
                    work_log_sec =  total_logged_time.get(ticket.ticket_id,0)
                    work_log = self.ticket_time_format(work_log_sec)
                    status_key = str(ticket.status).lower()
                    if status_key in status_counts:
                        status_counts[status_key] += 1

                    ticket_data = {
                        'ticket_id': ticket.ticket_id,
                        'id_with_sub':f"{ticket.ticket_id} [{sub_ticket_count}]" if sub_ticket_count else f"{ticket.ticket_id}",
                        'title': ticket.subject,
                        'priority': ticket.priority,
                        'status': ticket.status,
                        'ticket_type': ticket.ticket_type,
                        'created_by': user_first_names.get(ticket.created_by, {'name': '-'})['name'],
                        'assigned_to': user_first_names.get(ticket.assigned_to, {'name': '-'})['name'],
                        'deadline': ticket.deadline.strftime("%d/%m/%Y") if ticket.deadline else '-',
                        'created_at': ticket.created_at,
                        'estimated_time': estimated_time,
                        'work_log': work_log
                    }
                    sub_tickets_dict[ticket.ticket_id] = ticket_data
                
                # Replace spaces with underscores in status_counts keys to maintain pep 8 standard 
                status_counts = {key.replace(" ", "_"): value for key, value in status_counts.items()}
                response['sub_tickets_dict'] = sub_tickets_dict
                response['status_counts'] = status_counts
        except Exception as err:
            return {"error":err}

        return response
        # return sub_tickets_dict


    def get_work_logs_by_ticket_ids(self,ticket_ids):
        total_logged_time = {}
        if ticket_ids:
            ticket_time_data = TicketDA().get_all_ticket_time_ticket_ids(ticket_ids)

            for each_time in ticket_time_data:
                ticket_id = each_time.ticket_id
                logged_time = each_time.log_time

                if ticket_id in total_logged_time:
                    total_logged_time[ticket_id] += logged_time
                else:
                    total_logged_time[ticket_id] = logged_time
        return total_logged_time


    def ticket_time_format(self,time_sec):

        ticket_time_format = '00:00'
        if time_sec not in [0, '0', 'null', None, 'None']:
            total_minutes = int(time_sec) // 60
            log_hour = total_minutes // 60
            log_min = total_minutes % 60
            ticket_time_format = f"{log_hour:02d}:{log_min:02d}"
        return ticket_time_format

    def is_parent_valid(self, parent_id, project_id, ticket_id=0):
        valid_status = settings.TICKET_STATUS_OPEN
        ticket = TicketDA().get_ticket_by_ticket_id(parent_id)
        if not ticket:
            return False
        if project_id != ticket.project_id:
            return False
        if str(ticket.status).lower()  not in  list(map(lambda x: x.lower(), valid_status)):
            return False
        if ticket_id==parent_id:
            return False

    def get_watchers_mail_list(self, watchers):
        watchers_mail_list = []
        watchers = [int(watcher) for watcher in watchers]
        all_users = UserDA().get_all_active_users()
        for user in all_users:
            if user.id in watchers:
                watchers_mail_list.append(user.email)
        return list(set(watchers_mail_list))


    def edit_ticket_comment(self, ticket_id, message):
        response = {"error": ""}
        ticket_detail=TicketDA().get_ticket_details_by_ticket_id(ticket_id).filter(action = "Commented").last()
        if not ticket_detail:
            ticket_detail=TicketDA().get_ticket_details_by_ticket_id(ticket_id).filter(action = "Created").last()

        if ticket_detail:
            latest_ticket_detail_id=ticket_detail
            created_at = latest_ticket_detail_id.created_at
            now = timezone.now()
            if now - created_at > timedelta(minutes=5):
                response['error'] = 'Minimum time is exceed to edit.'
                return response
            else:
                latest_ticket_detail_id = latest_ticket_detail_id.ticket_details_id
                action = 'Commented'
                is_comment_update=TicketDA().update_ticket_details_by_id(message,action,latest_ticket_detail_id)
                if is_comment_update:
                    response['message'] = 'Ticket updated successfully'
                    return response

    def send_ticket_event_email(self, message, ticket_header, created_by, project_name, watchers, is_create=True,ticket_changes=None):

        assignee_name = "-"
        deadline = "-"

        if is_create:
            if ticket_header.deadline:
                deadline_datetime = datetime.strptime(ticket_header.deadline, "%Y-%m-%d")
                deadline = deadline_datetime.strftime("%d/%m/%Y")
            email_subject = f"{project_name} Ticket #{ticket_header.ticket_id} has been created - {ticket_header.subject}"
        else:
            ticket_id = ticket_header.ticket_id
            ticket_header = None
            ticket_header = TicketDA().get_ticket_head_by_ticket_id(ticket_id)
            if ticket_header.deadline:
                deadline = ticket_header.deadline.strftime("%d/%m/%Y")
            email_subject = f"{project_name} Ticket #{ticket_header.ticket_id} has been updated - {ticket_header.subject}"
        
        assignee =UserDA().get_user_by_id(ticket_header.assigned_to)
        if assignee:
            assignee_name = assignee.first_name + " " + assignee.last_name

        email_content_dto = new_dto()
        email_content_dto.heading = email_subject
        email_content_dto.subject = email_subject
        email_content_dto.description = message
        email_content_dto.emp_name = created_by
        email_content_dto.assigned_to = assignee_name
        email_content_dto.priority = ticket_header.priority
        email_content_dto.project_name = project_name
        email_content_dto.category = ticket_header.category if ticket_header.category else '-'
        email_content_dto.ticket_type = ticket_header.ticket_type #if ticket_type else '-'
        email_content_dto.created_by = created_by
        email_content_dto.deadline = deadline

        email_content_dto.ticket_id = ticket_header.ticket_id
        #if ticket_changes:
        email_content_dto.ticket_changes = ticket_changes
        emp_mail = self.get_watchers_mail_list(watchers)

        if is_create:
            email_msg = NotificationBL().generate_ticket_create_email_messages(email_content_dto)
        else:
            email_msg = NotificationBL().generate_ticket_update_email_messages(email_content_dto)

        NotificationBL().send_ticket_mail(email_msg, created_by, emp_mail, email_subject)

    def setup_watchers(self, project_id, watchers, user_id, assigned_to):
        watchers.append(user_id)
        #Add lead of a project to watchers list:
        project_leads = ProjectDA().get_project_leads_by_project_id(project_id)
        if project_leads:
            for lead in project_leads:
                watchers.append(int(lead.user_id))
        if assigned_to not in ('', '0', 0, None):
            watchers.append(int(assigned_to))
        watchers = set(watchers)
        return watchers

    def write_ticket_attachment(self, each_file, ticket_id, ticket_details_id):
        ticket_attachment_data = None
        try:
            file = self.__generate_uuid_filename()
            file_name = each_file.name
            folder_path = self.get_ticket_attachment_folder(file_name, ticket_id)
            ticket_attachment_data = {
                'filename': file_name,
                'ticket_id': ticket_id,
                'ticket_details_id': ticket_details_id,
                'file': file
            }
            
            file_data = each_file.read()
            self.__file_manager.upload_encrypted_file(folder_path, file_data)

        except Exception as err:
            ticket_attachment_data = None

        return ticket_attachment_data


    def __generate_uuid_filename(self):
        return f"{str(uuid.uuid4())}.pdf"


    def get_ticket_attachment_folder(self, file_name, ticket_id):
        return f"{settings.CONFIDENTIAL_DOCS}ticket_attachment/{ticket_id}/{file_name}"

    #for Sag
    # def get_dashboard_details(self,user_id, role_id ,project_id):
    def get_dashboard_details(self,user_id,project_id):
        response = {"ticket_dict": {}, "project_user_dict":{},"error": None}
        try:
            #Sag Ticket Listing Logic
            # sag_project_ids = settings.COMMON_PROJECTS
            # is_permitted_to_view_all_tickets = self.is_manager(role_id)
            # is_sag_team_lead = False
            # is_sag_team_member = False

            # if project_id in sag_project_ids and not is_permitted_to_view_all_tickets:
            #     sag_team_members = []
            #     sag_team_leads = []

            #     #Sag project ids are retrieved and leads of each projects are added to list
            #     # for project_id in sag_project_ids:
            #     lead_id = ProjectDA().get_project_leads_by_project_id(int(project_id)).first().user_id
            #     sag_team_leads.append(lead_id)

            #     for lead_id in sag_team_leads:
            #         team_members = UserDA().get_current_team_members_by_lead_id(lead_id)
            #         team_members = list(map(lambda member: member.id, team_members))
            #         # sag_team_dict[lead_id] = team_members
            #         sag_team_members.extend(team_members)

            #     sag_team_members = list(set(sag_team_members))

            #     #Checking whether the user is Sag team member or Sag team lead
            #     is_sag_team_member = True if user_id in sag_team_members else False
            #     is_sag_team_lead = True if user_id in sag_team_leads else False

            #     if role_id == 4 and (not is_sag_team_lead and not is_sag_team_member):
            #         user_ids = UserDA().get_current_team_members_by_lead_id(user_id)
            #         user_ids = list(map(lambda user: user.id, user_ids))
            #         user_ids.append(user_id)

            team_overdue_count = un_assigned_tickets = unanswered_count = my_reported = 0
            my_assigned = my_open_ticket_count = team_open_tickets_count = my_overdue_count = team_overdue_today_count = 0
            ticket_assigned_users = []
            team_members = []
            ticket_dict = {}
            project_user_dict = {}
            current_date = datetime.now().date()
            current_datetime = datetime.now()
            min_days_last_update = timedelta(days=7)
            all_tickets = TicketDA().get_all_tickets_from_project_ids([project_id])

            #Sag Ticket Listing Logic
            # if project_id in sag_project_ids and not is_permitted_to_view_all_tickets:
            #     if not is_sag_team_member and not is_sag_team_lead:
            #         if role_id == 4:
            #             all_tickets = all_tickets.filter(project_id=project_id, created_by__in=user_ids)
            #         else:
            #             all_tickets = all_tickets.filter(project_id=project_id, created_by=user_id)
            if all_tickets:
                ticket_assigned_users = list(set(all_tickets.exclude(status__in=settings.TICKET_STATUS_CLOSED).values_list('assigned_to', flat=True)))

            project_leads = ProjectDA().get_project_leads_by_project_id(project_id)
            project_lead_ids = project_leads.values_list('user_id', flat=True)
            for lead_id in project_lead_ids:
                team_members.extend(UserDA().get_current_team_members_by_lead_id(lead_id))
            team_member_ids = [user.id for user in team_members]
            project_user_ids = ProjectDA().get_project_employees_from_project_id(project_id)

            # For taking the user ids the user contains in project user and team member.
            common_user_ids = list(set(team_member_ids) & set(project_user_ids))
            ticket_assigned_users = list(set(ticket_assigned_users) | set(common_user_ids))
            active_users = UserDA().get_all_users()
            project_users = active_users.filter(id__in=ticket_assigned_users)
            # all_users = { user.id : {"name": user.first_name + " " + user.last_name} for user in project_users }

            #project_user_dict is creating here.
            for user in project_users:
                project_user_dict[user.id] = {
                    'emp_id': user.id,
                    'emp_name': user.first_name + " " + user.last_name,
                    'my_open_ticket_count': 0,
                    'my_overdue_count': 0,
                    'unanswered_count': 0,
                    'last_week_work_hours': '-',
                    'reopened_count': 0
                }


            # TO GET WORK HOURS AND REOPENED TICKET COUNT
            project_users = project_user_dict.keys()
            work_hours = {}
            reopended_count = {}
            if project_users:
                end_date = datetime.now()
                start_date = end_date - timedelta(days=300)

                holiday_list = HolidayDA().get_holiday_dates_only(start_date, end_date)
                while self.__is_weekend(end_date) or self.__is_holiday(end_date, holiday_list):
                    end_date -= timedelta(days=1)

                current = 1
                start_date = end_date
                while current < 5:
                    start_date = start_date - timedelta(days=1)
                    while self.__is_weekend(start_date) or self.__is_holiday(start_date, holiday_list):
                        start_date -= timedelta(days=1)
                    current+=1

                allowed_tickets = []
                if all_tickets:
                    allowed_tickets = [x.ticket_id for x in all_tickets]
                work_hours = self.get_last_day_work_hours(project_users, start_date, end_date, allowed_tickets)
                reopended_count = self.get_reopened_ticket_count(project_users, start_date, end_date, allowed_tickets)


            ticket_dict['user_id'] = user_id
            for ticket in all_tickets:
                if ticket.created_by == user_id:
                    my_reported += 1
                if ticket.assigned_to == user_id:
                    my_assigned += 1
                    if ticket.deadline and ticket.deadline.date() < current_date and ticket.status not in settings.TICKET_STATUS_CLOSED:
                        my_overdue_count +=1
                if ticket.assigned_to == user_id and ticket.status in settings.TICKET_STATUS_OPEN:
                    my_open_ticket_count +=1
                if ticket.status in settings.TICKET_STATUS_OPEN:
                    team_open_tickets_count +=1
                if ticket.deadline and ticket.deadline.date() == current_date and ticket.status not in settings.TICKET_STATUS_CLOSED:
                    team_overdue_today_count +=1
                if ticket.deadline and ticket.deadline.date() < current_date and ticket.status not in settings.TICKET_STATUS_CLOSED:
                    team_overdue_count += 1
                if not ticket.assigned_to and ticket.status not in settings.TICKET_STATUS_CLOSED:
                    un_assigned_tickets += 1
                if ticket.status not in settings.TICKET_STATUS_CLOSED and ticket.updated_at:
                    if ticket.updated_at + min_days_last_update < current_datetime:
                        unanswered_count += 1
                assigned_to = ticket.assigned_to
                if assigned_to and project_user_dict.keys(): #all_users.get(int(assigned_to)):
                    project_member_open = project_member_over_due = project_member_unanswer = 0
                    if ticket.status in settings.TICKET_STATUS_OPEN:
                        project_member_open = 1
                    if ticket.status not in settings.TICKET_STATUS_CLOSED and \
                        ticket.deadline and ticket.deadline.date() < current_date:
                        project_member_over_due = 1
                    if ticket.status not in settings.TICKET_STATUS_CLOSED and \
                    ticket.updated_at and ticket.updated_at + min_days_last_update < current_datetime:
                        project_member_unanswer = 1
                    if assigned_to in project_user_dict.keys():
                        project_user_dict[assigned_to]['my_open_ticket_count'] += project_member_open
                        project_user_dict[assigned_to]['my_overdue_count'] += project_member_over_due
                        project_user_dict[assigned_to]['unanswered_count'] += project_member_unanswer
                        if work_hours.get(assigned_to):
                            project_user_dict[assigned_to]['last_week_work_hours'] = work_hours[assigned_to]
                        if reopended_count.get(assigned_to):
                            project_user_dict[assigned_to]['reopened_count'] = reopended_count[assigned_to]

            ticket_dict['my_reported_count'] = my_reported
            ticket_dict['my_assigned_count'] = my_assigned
            ticket_dict['team_tickets_count'] = len(all_tickets)
            ticket_dict['my_open_ticket_count'] = my_open_ticket_count
            ticket_dict['team_open_tickets_count'] = team_open_tickets_count
            ticket_dict['my_overdue_count'] = my_overdue_count
            ticket_dict['team_overdue_today_count'] = team_overdue_today_count
            ticket_dict['team_overdue_count'] = team_overdue_count
            ticket_dict['un_assigned_tickets'] = un_assigned_tickets
            ticket_dict['unanswered_count'] = unanswered_count
            response['ticket_dict']=ticket_dict
            #Sort the outer dictionary by the 'emp_name' key in the inner dictionaries
            sorted_outer_dict = dict(sorted(project_user_dict.items(), key=lambda item: item[1]['emp_name']))



            response['project_user_dict'] = sorted_outer_dict
        except Exception as err:
            response['error'] = err
            self.__log.error(self.__exception.get_exception())
        return response

    def get_last_day_work_hours(self, users, start_date, end_date, allowed_tickets):
        result_dict = {}
        try:

            log_time = TicketDA().get_ticket_log_time_by_user_ids(users, start_date, end_date)
            if log_time:
                for each in log_time:
                    if each.ticket_id not in allowed_tickets:
                        continue
                    if each.user_id in result_dict.keys():
                        result_dict[each.user_id]+= each.log_time
                    else:
                        result_dict[each.user_id] = each.log_time
                result_dict = {key: self.__convert_seconds_to_log_time(value) for key, value in result_dict.items()}
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return result_dict

    def get_reopened_ticket_count(self, users, start_date, end_date, allowed_tickets):
        result_dict = {}
        try:
            chekced_ticket_ids = set()
            tickets = TicketDA().get_ticket_detail_by_status(users, start_date.date(), end_date.date())
            if tickets:
                for each in tickets:
                    if each.ticket_id not in allowed_tickets:
                        continue
                    if each.ticket_id in chekced_ticket_ids:
                        continue
                    if each.assigned_to in result_dict.keys():
                        result_dict[each.assigned_to] += 1
                    else:
                        result_dict[each.assigned_to] = 1
                    chekced_ticket_ids.add(each.ticket_id)
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return result_dict

    # def get_reopened_ticket_count(self, users, start_date, end_date, allowed_tickets):
    #     result_dict = {}
    #     try:
    #         # chekced_ticket_ids = set()
    #         checked_ticket_dict = {}
    #         tickets = TicketDA().get_ticket_detail_by_status(users, start_date.date(), end_date.date(),\
    #             status=None, ticket_ids=allowed_tickets)
    #         if tickets:
    #             for each in tickets:
    #                 if each.status == 'Reopen':
    #                     if each.ticket_id in checked_ticket_dict.keys() and checked_ticket_dict.get(each.ticket_id,'')=='Reopen':
    #                         continue
    #                     if each.assigned_to in result_dict.keys():
    #                         result_dict[each.assigned_to] += 1
    #                     else:
    #                         result_dict[each.assigned_to] = 1
    #                     checked_ticket_dict[each.ticket_id] = each.status
    #                     print(each.ticket_details_id)
    #                 else:
    #                     checked_ticket_dict[each.ticket_id] = each.status
    #                     continue
    #     except Exception as err:
    #         self.__log.error(self.__exception.get_exception())
    #     return result_dict

    def __is_weekend(self, date):
        return date.weekday() in [5, 6]  # Saturday is 5, Sunday is 6

    def __is_holiday(self, date, holiday_list):
        return date in holiday_list

    def __convert_seconds_to_log_time(self, seconds):

        total_hours = seconds / 3600
        log_hour = int(total_hours)
        log_min = int((total_hours - log_hour) * 60)

        return f"{log_hour}:{log_min:02d} Hrs"

    def configure_preferred_project(self, user_id, preferred_project_id):
        response = {"message": "","error": None,"status":200}
        try:
            project = ProjectDA().get_project_by_id(preferred_project_id)
            if not project:
                response["message"] = "You have attempted to access an invalid project. Please contact your lead/manager for assistance."
                response['error'] = True
                response['status'] = 499
                return response
            with transaction.atomic():
                ProjectDA().update_project_emp_mapping_by_emp_id(user_id, {'is_preferred_project':0})
                project = ProjectDA().update_project_emp_mapping(user_id, preferred_project_id,{'is_preferred_project':1})
                response["message"] = "The preferred project has been updated successfully."
        except Exception as err:
            response["message"] = settings.ERROR_MSG['application_error'].format(str(err), self.__log.error(self.__exception.get_exception()))
            response['error'] = True
            response['status'] = 499
        finally:
            return response


    def get_watchers_and_assigned_users(self, user_id, role_id, project_id,ticket_id=0):

        assigned_users = []
        watchers = []
        project_user_ids = []
        current_user_lead_ids = []
        common_projects = settings.COMMON_PROJECTS #need to take from constants

        active_users = UserDA().get_all_active_users()

        manager_watchers, manager_assigned_users = self.__get_all_managers(project_id, common_projects)
        watchers.extend(manager_watchers)
        assigned_users.extend(manager_assigned_users)



        #In case of Sag projects we need current user and his lead + sag team + managers in watchers,
        #And sag team in assigned users

        if project_id in common_projects:
            team_members = []
            #getting lead and project members of sag project (required for both watchers and assigned users)
            common_project_user_ids = []

            #here we are taking only lead and his team members, to avoid entire company employees being listed in sag projects assigned users
            project_leads = ProjectDA().get_project_leads_by_project_id(project_id)
            project_lead_ids = project_leads.values_list('user_id', flat=True)
            for lead_id in project_lead_ids:
                team_members.extend(UserDA().get_current_team_members_by_lead_id(lead_id))
            team_member_ids = [user.id for user in team_members]

            common_project_user_ids.extend(project_lead_ids)
            common_project_user_ids.extend(team_member_ids)

            common_project_users = active_users.filter(id__in=common_project_user_ids)

            for user in common_project_users:
                user_details = {
                    "emp_name": f"{user.first_name} {user.last_name}",
                    "emp_id": f"{user.id}",
                }
                if user_details not in watchers:
                    watchers.append(user_details)

                if user_details not in assigned_users:
                    assigned_users.append(user_details)

            #if ticket id is passed and the project is Sag, then current user and his lead is added to watchers
            if ticket_id and project_id in common_projects:
                ticket = TicketDA().get_ticket_by_ticket_id(ticket_id)
                ticket_creator = ticket.created_by
                ticket_creator_role_id, ticket_creator_name = UserDA().get_user_role_by_id(ticket_creator)

                if ticket_creator_role_id not in [1,2,3,4]:
                    ticket_creator_lead = UserDA().get_lead_id_by_user(ticket_creator)
                    current_user_lead_ids.append(ticket_creator_lead)
                current_user_lead_ids.append(ticket_creator)

            #Added Develper and his lead
            if role_id not in [1,2,3,4]:
                user_lead = UserDA().get_lead_id_by_user(user_id)
                current_user_lead_ids.append(user_lead)
            current_user_lead_ids.append(user_id)
            current_users = active_users.filter(id__in=current_user_lead_ids)

            for user in current_users:
                user_details = {
                    "emp_name": f"{user.first_name} {user.last_name}",
                    "emp_id": f"{user.id}",
                }

                watchers.append(user_details)

            watchers = self.remove_user_duplicates(watchers)
            assigned_users = self.remove_user_duplicates(assigned_users)

        #In case of other projects we need managers + project users as watchers
        #And managers + project users as assigned users
        else:
            watchers,assigned_users = self.__get_watchers_and_assigned_users_individual_project(project_id)


        return watchers, assigned_users


    def __get_all_managers(self, project_id, common_project):
        assigned_users = []
        watchers = []
        try:
            #currently taking all manager users (common for both sag and other projects in watchers)
            manager_users = UserDA().get_all_managers()
            if manager_users:
                for user in manager_users[0]:
                    user_details = {
                        "emp_name": f"{user[0]} {user[1]}",
                        "emp_id": f"{user[2]}",
                    }
                    if user_details not in watchers:
                        watchers.append(user_details)

                    #manager users is not required in assigned user for common project
                    if project_id not in common_project:
                        if user_details not in assigned_users:
                            assigned_users.append(user_details)
        except:
            self.__log.error(self.__exception.get_exception())

        return watchers,assigned_users

    def __get_watchers_and_assigned_users_individual_project(self, project_id):
        assigned_users = []
        watchers = []
        active_users = UserDA().get_all_active_users()
        project_user_ids = ProjectDA().get_project_employees_from_project_id(project_id)
        project_users = active_users.filter(id__in=project_user_ids)
        if project_users:
            for user in project_users:
                user_details = {
                        "emp_name": f"{user.first_name} {user.last_name}",
                        "emp_id": f"{user.id}",
                    }
                assigned_users.append(user_details)
                watchers.append(user_details)
            watchers = self.remove_user_duplicates(watchers)
            assigned_users = self.remove_user_duplicates(assigned_users)

        return watchers,assigned_users

    def remove_user_duplicates(self, users):
        users_list = []
        repeat_list = []
        for user in users:
            if user['emp_id'] in repeat_list:
                continue
            users_list.append(user)
            repeat_list.append(user['emp_id'])

        return users_list


    def is_ticket_comment_editable(self, ticket_id, user_id):
        is_comment_edit = False
        MAX_EDIT_TIME = 5
        try:
            ticket_details_data = TicketDA().get_ticket_details_by_ticket_id(ticket_id)
            if ticket_details_data:
                temp_ticket_data = ticket_details_data.filter(action="Commented").last()
                if not temp_ticket_data:
                    temp_ticket_data = ticket_details_data.filter(action="Created").last()

                if temp_ticket_data:
                    created_by = temp_ticket_data.created_by
                    created_at = temp_ticket_data.created_at
                    now = timezone.now()
                    if now - created_at <= timedelta(minutes=MAX_EDIT_TIME) and created_by==user_id:
                        is_comment_edit = True
        except:
            self.__log.error(self.__exception.get_exception())
        finally:
            return is_comment_edit


    def get_ticket_time_spent(self, user_id, ticket_id, users):
        response = {'ticket_details':[], 'work_log_format':0, 'error':None}
        ticket_details = []
        total_work_log_sec = 0
        try:
            ticket_times_data = TicketDA().get_all_ticket_log_time_by_user(user_id)
            if ticket_times_data:
                ticket_times = ticket_times_data.filter(ticket_id=ticket_id)
                for details_time in ticket_times:
                    if details_time.log_time > 3540:
                        total_time =TicketHelperBL().ticket_time_format(details_time.log_time)
                        total_time = f"{total_time} Hrs"
                    else:
                        log_min = details_time.log_time//60
                        total_time = f"{log_min} min"
                    ticket_details.append({
                        "type":  "Log Time",
                        'log_time':total_time,
                        'log_date': details_time.log_date.strftime("%d/%m/%Y"),
                        "changed_by": users.get(details_time.user_id, '-'),
                        "updated_at": details_time.created_at.strftime(" update on %A %d %B at %I:%M %p"),
                        "created_at": details_time.created_at
                    })
                    total_work_log_sec += details_time.log_time
            total_work_log_sec = self.ticket_time_format(total_work_log_sec)
        except:
            response['error'] = self.__log.error(self.__exception.get_exception())
        finally:
            response['ticket_details'] = ticket_details
            response['work_log_format'] = total_work_log_sec
            return response

    def get_property_comment(self, current_comment, previous_comment, users, cat_type):
        res =[]
        if cat_type == "Status":
            previous = previous_comment.status
            current = current_comment.status
        elif cat_type == "Ticket Type":
            previous = previous_comment.ticket_type
            current = current_comment.ticket_type
        elif cat_type == "Title":
            previous = previous_comment.subject if previous_comment.subject not in ['Null','null',None,'None','0',0,''] else 'No Title'
            current = current_comment.subject if current_comment.subject not in ['Null','null',None,'None','0',0,''] else 'No Title'
        elif cat_type == "Priority":
            previous = previous_comment.priority
            current = current_comment.priority
        elif cat_type == "Category":
            previous = previous_comment.category if previous_comment.category else 'No Category',
            current = current_comment.category if current_comment.category else 'No Category',
        elif cat_type == "Deadline":
            previous = previous_comment.deadline.strftime("%d/%m/%Y") if previous_comment.deadline else "Undated",
            current = current_comment.deadline.strftime("%d/%m/%Y")if current_comment.deadline else "Undated",
        elif cat_type == "Assignee":
            previous = users.get(previous_comment.assigned_to) if previous_comment.assigned_to else 'Nobody',
            current = users.get(current_comment.assigned_to) if current_comment.assigned_to else 'Nobody',
        elif cat_type == 'Estimated Time':
            previous = self.ticket_time_format(previous_comment.estimated_time) + ' Hrs' if previous_comment.estimated_time else 'No time'
            current = self.ticket_time_format(current_comment.estimated_time) + ' Hrs' if current_comment.estimated_time else 'No time'
        elif cat_type == "Module":
            module_dict = TicketDA().get_ticket_module_id_name()
            previous = module_dict[previous_comment.module_id] if previous_comment.module_id not in ['Null','null',None,'None','0',0,''] else 'No Module'
            current = module_dict[current_comment.module_id] if current_comment.module_id not in ['Null','null',None,'None','0',0,''] else 'No Module'

        if previous != current:
            res.append({
                "type":  cat_type,
                'previous': previous,
                'current': current,
                "changed_by": users.get(current_comment.created_by, '-'),
                "updated_at": current_comment.created_at.strftime("on %A %d %B at %I:%M %p"),
                "created_at": current_comment.created_at
                }
            )
        return res

    def get_estimated_time(self, ticket):
        estimated_time = None
        if ticket.estimated_time not in [0,'0','null',None,'None']:
            if int(ticket.estimated_time) >= 3600:
                estimated_time =self.ticket_time_format(ticket.estimated_time)
            else:
                estimated_time = {int(ticket.estimated_time)//60}
        return estimated_time


    def __get_ticket_watchers(self, ticket_id):
        watchers = []
        if ticket_id:
            watchers_list = TicketDA().get_ticket_watchers_by_ticket_id(ticket_id)
            watchers = list(map(str, watchers_list.values_list('watcher', flat=True)))
        return watchers

    def get_ticket_head_formatted(self, ticket, users):
        res = {
            "project_id": ticket.project_id,
            "subject": ticket.subject,
            "ticket_type": ticket.ticket_type,
            "status": ticket.status,
            "priority": ticket.priority,
            "action": f"Reported by {users[ticket.created_by]} on {ticket.created_at.strftime('%d %b at %I:%M %p')}",
            "tag_name": ticket.tag_name,
            "watchers": self.__get_ticket_watchers(ticket.ticket_id),
            "start_date": ticket.start_date.strftime("%d/%m/%Y") if ticket.start_date else None,
            "end_date": ticket.end_date.strftime("%d/%m/%Y") if ticket.end_date else None,
            "deadline": ticket.deadline.strftime("%d/%m/%Y") if ticket.deadline else "-",
            "estimated_time": self.get_estimated_time(ticket),
            "estimated_time_format": self.ticket_time_format(ticket.estimated_time),
            "work_log": "00:00",
            "assigned_to": users.get(ticket.assigned_to, ""),
            "assigned_user":ticket.assigned_to if ticket.assigned_to else "-",
            "ticket_id": ticket.ticket_id,
            "parent_id": ticket.parent_id,
            "category": ticket.category,
            # "repo_uri": ticket.repo_uri,
            "repo_id": ticket.repo_id,
            "is_cicd_enabled": ticket.is_cicd_enabled,
            "module_id": ticket.module_id,
        }
        return res


    def get_ticket_attachments(self, ticket_id):
        attachment_details = {}
        try:
            attachments = TicketDA().get_all_attachments_by_ticket_id(ticket_id)
            if attachments:
                for attachment in attachments:
                    if attachment.ticket_details_id in attachment_details:
                        attachment_details[attachment.ticket_details_id].append({"file_name": attachment.filename,'id': attachment.attachment_id})
                        # temp_list = attachment_details[attachment.ticket_details_id]
                        # temp_list.append({"file_name": attachment.filename, 'id': attachment.attachment_id})
                        # attachment_details[attachment.ticket_details_id] = temp_list
                    else:
                        attachment_details[attachment.ticket_details_id] = [{"file_name": attachment.filename, 'id': attachment.attachment_id}]
        except:
            self.__log.error(self.__exception.get_exception())
        finally:
            return attachment_details


    def get_parent_tickets_with_status_in_dict(self, parent_id):
        try:
            parent_ticket_dict = {}
            current_parent_id = parent_id
            while current_parent_id:
                parent_ticket = TicketDA().get_ticket_head_by_ticket_id(current_parent_id)
                # current_parent_id = parent_ticket.parent_id
                current_parent_id = 0
                parent_ticket_dict[parent_ticket.ticket_id] = {
                    'ticket_id': parent_ticket.ticket_id,
                    'status': parent_ticket.status
                }
        except:
            self.__log.error(self.__exception.get_exception())
        finally:
            return parent_ticket_dict
        
    def get_all_repo_names_by_project_id(self, project_id):

        try:
            project_repo_list = []
            repo_filter_criteria = {}
            mapping_filter_criteria = {}
            repo_filter_criteria['project_id'] = project_id
            repo_mapping = ProjectDA().get_all_repo_mapping_by_filter_criteria(repo_filter_criteria)
            if repo_mapping:
                repo_mapping_ids = repo_mapping.values_list('repo_id', flat=True)
            if repo_mapping_ids:
                mapping_filter_criteria['repo_id__in'] = repo_mapping_ids
                project_repo = ProjectDA().get_all_project_repo_by_filter_criteria(mapping_filter_criteria)
                if project_repo:
                    project_repo = project_repo.order_by('repo_name')
                    for repo in project_repo:
                        project_repo_dict = {
                            "repo_id":repo.repo_id,
                            "repo_name":repo.repo_name,
                        }
                        project_repo_list.append(project_repo_dict)
        except Exception as err:
            return project_repo_list
        return project_repo_list

    def get_all_project_modules_by_project_id(self, project_id):

        try:
            project_module_list = []
            project_modules = ProjectDA().get_all_active_modules_by_project(project_id)
            if project_modules:
                for module in project_modules:
                    project_modules_dict = {
                        "module_id":module.module_id,
                        "module_name":module.name,
                    }
                    project_module_list.append(project_modules_dict)
        except Exception as err:
            return project_module_list
        return project_module_list
    
    def __encrypt_value(self, value):

        try:
            value_bytes = str(value).encode('utf-8')
            encrypted_value = self.cipher_suite.encrypt(value_bytes)
            encrypted_value_base64 = base64.b64encode(encrypted_value).decode('utf-8')
        except Exception as err:
            encrypted_value_base64 = settings.ERROR_MSG['application_error'].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )

        return encrypted_value_base64

    def __decrypt_value(self, encrypted_value_base64):

        try:
            encrypted_value = base64.b64decode(encrypted_value_base64.encode('utf-8'))
            decrypted_value = self.cipher_suite.decrypt(encrypted_value)
            decrypted_value_str = decrypted_value.decode('utf-8')
        except Exception as err:
            decrypted_value_str = settings.ERROR_MSG['application_error'].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )

        return decrypted_value_str
    

    def is_manager(self, role_id):
        is_manager = False
        if role_id in (1, '1', 2, '2', 3, '3'):
            is_manager = True
        return is_manager
    

    def create_git_branch(self, user_id, repo_id, project_id, ticket_id, emp_name, project_name, watchers):
        error = None
        try:
            project_repo = ProjectDA().get_project_repo_by_id(repo_id)
            if not project_repo:
                error = f"Unable to find the repository configuration for the repo ID {repo_id}. CI/CD process cannot proceed."
                self.send_ticket_repo_mail(ticket_id=ticket_id, watchers=watchers, error=error, emp_name=emp_name, project_name=project_name)
                return error

            project_repo_mappings = ProjectDA().get_project_repo_mapping_by_repoid(repo_id)
            if not project_repo_mappings:
                error = f"The project {project_name} is not associated with any repository. The CI/CD process cannot proceed in this scenario."
                self.send_ticket_repo_mail(ticket_id=ticket_id, watchers=watchers, error=error, emp_name=emp_name, project_name=project_name)
                return error
            
            if project_repo_mappings:
                if project_repo_mappings[0].project_id != project_id:
                    error = f"The project {project_name} is not mapped with the repository ID:#{repo_id}. The CI/CD process cannot proceed in this scenario."
                    self.send_ticket_repo_mail(ticket_id=ticket_id, watchers=watchers, error=error, emp_name=emp_name, project_name=project_name)
                    return error                       
            
            if str(project_repo.provider).lower() == 'gitlab':
                #git_project_id, new_branch, source_branch, ticket_key
                git_uri = project_repo.base_url
                project_repo_user = ProjectDA().get_project_repo_user_mapping_by_repoid(user_id, repo_id)
                token = project_repo_user.token # self.__decrypt_value(project_repo.token)
                git_project_id = project_repo.repo_project_id                
                new_branch = str(project_repo.branch_prefix).lower() + "-" + str(ticket_id) + "-" + str(project_repo.branch_suffix).lower() 
                source_branch = project_repo.source_branch
                ticket_key = str(project_repo.branch_prefix).lower() + "-" + str(ticket_id) 

                gitlab_response = GitLabEngine().create_new_branch(git_uri, token, git_project_id, new_branch, source_branch, ticket_key)
                #response = {"message": "", "error": False}
                if gitlab_response['error']:
                    error = gitlab_response['error']
                    self.send_ticket_repo_mail(ticket_id=ticket_id, watchers=watchers, error=error, emp_name=emp_name, project_name=project_name)
                    return error
                else:
                    message = gitlab_response['message']
                    self.send_ticket_repo_mail(ticket_id=ticket_id, watchers=watchers, message=message, emp_name=emp_name, project_name=project_name)
                    return error
        
           
        except Exception as e:
            self.__log.error(self.__exception.get_exception())
            error = str(e)
            self.send_ticket_repo_mail(ticket_id=ticket_id, watchers=watchers, error=error, emp_name=emp_name, project_name=project_name)
            
        return error
        

    
    def delete_git_branch(self, user_id, repo_id, project_id, ticket_id, emp_name, project_name, watchers):
        error = None
        try:
            project_repo = ProjectDA().get_project_repo_by_id(repo_id)
            if not project_repo:
                error = f"Unable to find the repository configuration for the repo ID {repo_id}. CI/CD process cannot proceed."
                self.send_ticket_repo_mail(ticket_id=ticket_id, watchers=watchers, error=error, emp_name=emp_name, project_name=project_name)
                return error

            project_repo_mappings = ProjectDA().get_project_repo_mapping_by_repoid(repo_id)
            if not project_repo_mappings:
                error = f"The project {project_name} is not associated with any repository. The CI/CD process cannot proceed in this scenario."
                self.send_ticket_repo_mail(ticket_id=ticket_id, watchers=watchers, error=error, emp_name=emp_name, project_name=project_name)
                return error
            
            if project_repo_mappings:
                if project_repo_mappings[0].project_id != project_id:
                    error = f"The project {project_name} is not mapped with the repository ID:#{repo_id}. The CI/CD process cannot proceed in this scenario."
                    self.send_ticket_repo_mail(ticket_id=ticket_id, watchers=watchers, error=error, emp_name=emp_name, project_name=project_name)
                    return error           
            
            if str(project_repo.provider).lower() == 'gitlab':
                
                git_uri = project_repo.base_url
                # token = project_repo.token # self.__decrypt_value(project_repo.token)
                project_repo_user = ProjectDA().get_project_repo_user_mapping_by_repoid(user_id, repo_id)
                token = project_repo_user.token
                git_project_id = project_repo.repo_project_id                
                branch_name = str(project_repo.branch_prefix).lower() + "-" + str(ticket_id) + "-" + str(project_repo.branch_suffix).lower() 
                #source_branch = project_repo.source_branch
                ticket_key = str(project_repo.branch_prefix).lower() + "-" + str(ticket_id) 

                gitlab_response = GitLabEngine().delete_branch(git_uri, token, git_project_id, branch_name, ticket_key)
                if gitlab_response['error']:
                    error = gitlab_response['error']
                    self.send_ticket_repo_mail(ticket_id=ticket_id, watchers=watchers, error=error, emp_name=emp_name, project_name=project_name)
                    return error
                else:
                    message = gitlab_response['message']
                    self.send_ticket_repo_mail(ticket_id=ticket_id, watchers=watchers, message=message, emp_name=emp_name, project_name=project_name)
                    return error
            
           
        except:
            self.__log.error(self.__exception.get_exception())
            #mail send
        #finally:
        return error
        

    def merge_git_branch(self, user_id, repo_id, project_id, ticket_id, emp_name, project_name, watchers):
        error = None
        try:
            project_repo = ProjectDA().get_project_repo_by_id(repo_id)
            if not project_repo:
                error = f"Unable to find the repository configuration for the repo ID {repo_id}. CI/CD process cannot proceed."
                self.send_ticket_repo_mail(ticket_id=ticket_id, watchers=watchers, error=error, emp_name=emp_name, project_name=project_name)
                return error

            project_repo_mappings = ProjectDA().get_project_repo_mapping_by_repoid(repo_id)
            if not project_repo_mappings:
                error = f"The project {project_name} is not associated with any repository. The CI/CD process cannot proceed in this scenario."
                self.send_ticket_repo_mail(ticket_id=ticket_id, watchers=watchers, error=error, emp_name=emp_name, project_name=project_name)
                return error
            
            if project_repo_mappings:
                if project_repo_mappings[0].project_id != project_id:
                    error = f"The project {project_name} is not mapped with the repository ID:#{repo_id}. The CI/CD process cannot proceed in this scenario."
                    self.send_ticket_repo_mail(ticket_id=ticket_id, watchers=watchers, error=error, emp_name=emp_name, project_name=project_name)
                    return error   
            
            if str(project_repo.provider).lower() == 'gitlab':
                #git_project_id, new_branch, source_branch, ticket_key
                git_uri = project_repo.base_url
                # token = project_repo.token # self.__decrypt_value(project_repo.token)
                project_repo_user = ProjectDA().get_project_repo_user_mapping_by_repoid(user_id, repo_id)
                token = project_repo_user.token
                git_project_id = project_repo.repo_project_id                
                source_branch = str(project_repo.branch_prefix).lower() + "-" + str(ticket_id) + "-" + str(project_repo.branch_suffix).lower() 
                target_branch = project_repo.target_branch
                ticket_key = str(project_repo.branch_prefix).lower() + "-" + str(ticket_id) 

                gitlab_response = GitLabEngine().merge_and_push(git_uri, token, git_project_id, source_branch, target_branch, ticket_key)
                
                #response = {"message": "", "error": False}
                if gitlab_response['error']:
                    error = gitlab_response['error']
                    self.send_ticket_repo_mail(ticket_id=ticket_id, watchers=watchers, error=error, emp_name=emp_name, project_name=project_name)
                    return error
                else:
                    message = gitlab_response['message']
                    self.send_ticket_repo_mail(ticket_id=ticket_id, watchers=watchers, message=message, emp_name=emp_name, project_name=project_name)
                    return error
        
        
        except Exception as e:
            self.__log.error(self.__exception.get_exception())
            error = str(e)
            self.send_ticket_repo_mail(ticket_id=ticket_id, watchers=watchers, error=error)
            #mail send
        finally:
            return error
        


    def send_ticket_repo_mail(self, ticket_id, watchers, emp_name, project_name, message=None, error=None):
        error_message = 'Ticket repo update failed' if error else None
        success_message = 'Ticket repo update successful' if message else None

        email_content_dto = new_dto()
        email_content_dto.ticket_id = ticket_id
        email_content_dto.project_name = project_name

        if error:
            email_subject = error_message
            email_content_dto.heading = error_message
            email_content_dto.error = error
            email_content_dto.message = None
        
        if message:
            email_subject = success_message
            email_content_dto.heading = success_message
            email_content_dto.error = None
            email_content_dto.message = message

        emp_mail = self.get_watchers_mail_list(watchers)

        email_msg = NotificationBL().generate_ticket_repo_email_messages(email_content_dto)

        NotificationBL().send_ticket_mail(email_msg, emp_name, emp_mail, email_subject)
