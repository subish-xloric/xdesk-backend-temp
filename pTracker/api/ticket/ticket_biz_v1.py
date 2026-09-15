
# from datetime import datetime, date, timedelta
# from django.http import HttpResponse
# from django.utils import timezone
# from datetime import timedelta
from types import SimpleNamespace
# import uuid
# from django.db import  transaction
# from django.db.models import Q

# from datetime import datetime
# from itertools import chain
# from django.utils.safestring import mark_safe

from django.conf import Settings, settings

# from django.core.paginator import Paginator
# from django.db import transaction
from django.db.models import Q

from pTracker.common.utility import Utility
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.common.logs import Logs

# from pTracker.api.ticket.notification_biz import NotificationBL

from pTracker.dataaccess.ptracker_access.user_da import UserDA
from pTracker.dataaccess.ptracker_access.ticket_da import TicketDA
from pTracker.dataaccess.ptracker_access.project_da import ProjectDA

# from pTracker.settings import constants
# from pTracker.cronjobs.email_sender import send_email_notification

# from cryptography.fernet import Fernet

# from bs4 import BeautifulSoup

# import os
# import re



# ALLOWED_EXTENSIONS = ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'jpeg', 'jpg', 'png', 'gif', 'bmp', 'tiff', 'txt', 'csv', 'odt']



def new_dto():
    dto = SimpleNamespace()
    return dto

class TicketBL_V1():
    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()
        self.__utility = Utility()


    def get_ticket_summary_by_ticket_id(self, request, ticket_id):
        response = {
            "status": [],
            "head": [],
            "ticket_details": [],
            "latest_tickets": [],
            "is_comment_edit":False
            }
        ticket_header_data = None
        ticket_attachment_data = None
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

            #TODO
            # project = ProjectDA().get_project_by_id(project_id)
            # if not project:
            #     response["error"] = "You have attempted to access ticket of an invalid project. Please contact your lead/manager for assistance."
            #     response["status"] = 403
            #     return response

            #ticket_header_data = TicketDA().get_ticket_header_details_by_ticket_id(ticket_id)
            all_users = UserDA().get_all_users()
            users = { user.id : {"name": user.first_name + " " + user.last_name} for user in all_users }

            response["head"] = {
                "project_id": ticket_head.project_id,
                "subject": ticket_head.subject,
                "ticket_type": ticket_head.ticket_type,
                "status": ticket_head.status,
                "priority": ticket_head.priority,
                "action": f"Reported by {users[ticket_head.created_by]['name']} on {ticket_head.created_at.strftime('%d %b at %I:%M %p')}",
                "tag_name": ticket_head.tag_name,
                "start_date": ticket_head.start_date.strftime("%d/%m/%Y") if ticket_head.start_date else None,
                "end_date": ticket_head.end_date.strftime("%d/%m/%Y") if ticket_head.end_date else None,
                "deadline": ticket_head.deadline.strftime("%d/%m/%Y") if ticket_head.deadline else None,
                "estimated_time": ticket_head.estimated_time,
                "assigned_to": "",
                "assigned_user":0,
                "ticket_id": ticket_head.ticket_id,
            }

            try:
                assigned_to = users[ticket_head.assigned_to]['name']
            except:
                assigned_to = "-"

            if assigned_to:
                response["head"]["assigned_to"] = assigned_to
                response["head"]["assigned_user"] = ticket_head.assigned_to

            ticket_details_data = TicketDA().get_ticket_details_by_ticket_id(ticket_id)

            previous_comment = None
            ticket_details = []

            ticket_times_data = TicketDA().get_all_ticket_log_time_by_user(user_id)
            if ticket_times_data:
                ticket_times = ticket_times_data.filter(ticket_id=ticket_id)
                for details_time in ticket_times:
                    if details_time.log_time > 3540:
                        total_minutes = details_time.log_time // 60
                        log_hour = total_minutes//60
                        log_min = total_minutes%60
                        total_time = f"{log_hour}:{log_min} Hrs"
                    else:
                        log_min = details_time.log_time//60
                        total_time = f"{log_min} minutes"
                    ticket_details.append({
                        "type":  "Log Time",
                        'logged_time':total_time,
                        'logged_date': details_time.log_date.strftime("%d/%m/%Y"),
                        "changed_by": users[details_time.user_id]["name"],
                        "updated_at": details_time.created_at.strftime("updated on %A %d %B at %I:%M %p"),
                        "created_at": details_time.created_at,
                    })
            if ticket_details_data:
                for details_data in ticket_details_data:
                    if previous_comment:
                        if previous_comment.status != details_data.status:
                            ticket_details.append({
                            "type":  "Status",
                            'previous': previous_comment.status,
                            'current': details_data.status,
                            "changed_by": users[details_data.created_by]["name"],
                            "updated_at": details_data.created_at.strftime("on %A %d %B at %I:%M %p"),
                            "created_at": details_data.created_at,
                        })

                        if previous_comment.priority != details_data.priority:
                            ticket_details.append({
                            "type":  "Priority",
                            'previous': previous_comment.priority,
                            'current': details_data.priority,
                            "changed_by": users[details_data.created_by]["name"],
                            "updated_at": details_data.created_at.strftime("on %A %d %B at %I:%M %p"),
                            "created_at": details_data.created_at,
                        })

                        if previous_comment.deadline != details_data.deadline:
                            ticket_details.append({
                            "type":  "Deadline",
                            'previous': previous_comment.deadline.strftime("%d/%m/%Y") if previous_comment.deadline else "No Date",
                            'current': details_data.deadline.strftime("%d/%m/%Y")if details_data.deadline else "No Date",
                            "changed_by": users[details_data.created_by]["name"],
                            "updated_at": details_data.created_at.strftime("on %A %d %B at %I:%M %p"),
                            "created_at": details_data.created_at,
                        })

                        if previous_comment.ticket_type != details_data.ticket_type:
                            ticket_details.append({
                            "type":  "Ticket Type",
                            'previous': previous_comment.ticket_type,
                            'current': details_data.ticket_type,
                            "changed_by": users[details_data.created_by]["name"],
                            "updated_at": details_data.created_at.strftime("on %A %d %B at %I:%M %p"),
                            "created_at": details_data.created_at,
                        })

                        if previous_comment.assigned_to != details_data.assigned_to:
                            ticket_details.append({
                            "type":  "Assignee",
                            'previous': users[previous_comment.assigned_to]["name"] if previous_comment.assigned_to else 'NoBody',
                            'current': users[details_data.assigned_to]["name"] if details_data.assigned_to else 'NoBody',
                            "changed_by": users[details_data.created_by]["name"],
                            "updated_at": details_data.created_at.strftime("on %A %d %B at %I:%M %p"),
                            "created_at": details_data.created_at,
                        })
                        
                        if previous_comment.subject != details_data.subject:
                            ticket_details.append({
                            "type":  "Title",
                            'previous': previous_comment.subject,
                            'current': details_data.subject,
                            "changed_by": users[details_data.created_by]["name"],
                            "updated_at": details_data.created_at.strftime("on %A %d %B at %I:%M %p"),
                            "created_at": details_data.created_at,
                        })
                        
                    previous_comment = details_data

            ticket_details = sorted(ticket_details, key=lambda dict:dict['created_at'], reverse=False)
            response["ticket_details"] = ticket_details

        except Exception as err:
            response['success'] = False
            response["error"] = settings.ERROR_MSG['application_error'].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    def is_project_accessible(self, user_id, project_id):
        return ProjectDA().is_project_accessible(project_id, user_id)

    def is_manager(self, role_id):
        is_user = False
        if role_id in (1, '1', 2, '2', 3, '3'):
            is_user = True
        return is_user