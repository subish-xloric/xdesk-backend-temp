from  datetime import datetime, date, timedelta
from types import SimpleNamespace

from django.conf import Settings, settings
from django.db.models import query
from django.db.models import Q
from django.utils import timezone

from pTracker.common.utility import Utility
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.common.logs import Logs

from pTracker.dataaccess.ptracker_access.ticket_models import TicketHeader
from pTracker.dataaccess.ptracker_access.ticket_models import TicketAttachment
from pTracker.dataaccess.ptracker_access.ticket_models import TicketDetails
from pTracker.dataaccess.ptracker_access.ticket_models import TicketLogTime
from pTracker.dataaccess.ptracker_access.ticket_models import TicketWatcher
from pTracker.dataaccess.ptracker_access.project_models import ProjectEmployee, Project, ProjectModule


import os


def new_dto():
    dto = SimpleNamespace()
    return dto



class TicketDA():

    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()
        self.__utility = Utility()



    def get_ticket_by_id(self, ticket_id):
        return TicketHeader.objects.get(ticket_id=ticket_id)


    def get_all_tickets_by_project(self, project_id):
        tickets = TicketHeader.objects.filter(project_id=project_id)
        return tickets

    def get_latest_users_from_each_ticket(self, ticket_ids):
        ticket_details = []
        try:
            ticket_details = TicketDetails.objects.filter(ticket_id__in=ticket_ids).values_list('ticket_id', 'created_by', 'action', 'created_at')
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return ticket_details


    def get_ticket_watchers_by_ticket_id(self, ticket_id):
        watchers = []
        try:
            watchers = TicketWatcher.objects.filter(ticket_id=ticket_id)
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return watchers


    def get_ticket_head_by_ticket_id(self, ticket_id):
        project = None
        try:
            project = TicketHeader.objects.filter(ticket_id=ticket_id).first()#.project_id
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return project


    def get_all_tickets_filtered(self, filter_criteria,is_unanswered=False):
        tickets = None
        current_datetime = datetime.now()
        min_days_last_update = timedelta(days=7)
        try:
            if is_unanswered:
                tickets = TicketHeader.objects.filter(Q(updated_at__lt=current_datetime - min_days_last_update),**filter_criteria).order_by('-updated_at').exclude(status__in=settings.TICKET_STATUS_CLOSED)
            else:
                tickets = TicketHeader.objects.filter(**filter_criteria).order_by('-updated_at')
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return tickets

    def get_all_tickets_filtered_v1(self, filter_criteria,is_unanswered=False, sort_field='-updated_at'):
        # Created for adding sort option.
        tickets = None
        current_datetime = datetime.now()
        min_days_last_update = timedelta(days=7)
        try:
            if is_unanswered:
                tickets = TicketHeader.objects.filter(Q(updated_at__lt=current_datetime - min_days_last_update),**filter_criteria).order_by(sort_field).exclude(status__in=settings.TICKET_STATUS_CLOSED)
            else:
                tickets = TicketHeader.objects.filter(**filter_criteria).order_by(sort_field)
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return tickets


    # def get_all_tickets_filtered(self, filter_criteria, project_ids):
    #     tickets = None
    #     try:
    #         tickets = TicketHeader.objects.filter(project_id__in=project_ids, **filter_criteria).order_by('-updated_at')
    #     except Exception as err:
    #         self.__log.error(self.__exception.get_exception())
    #     return tickets


    def get_all_ticket_description(self):
        ticket_descriptions = None
        try:
            ticket_descriptions = TicketDetails.objects.filter(is_header=1)
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return ticket_descriptions
    

    def get_all_ticket_messages_by_ticket_ids(self, ticket_ids):
        ticket_descriptions = None
        try:
            ticket_descriptions = TicketDetails.objects.filter(ticket_id__in=ticket_ids)
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return ticket_descriptions


    def get_all_tickets_from_project_ids(self, project_ids):
        tickets = None
        try:
            tickets = TicketHeader.objects.filter(project_id__in=project_ids)
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return tickets


    def get_all_sub_tickets_by_ticket_id(self, parent_ticket_id):
        tickets = None
        try:
            tickets = TicketHeader.objects.filter(parent_id=parent_ticket_id)
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return tickets


    def get_latest_updated_tickets_from_project_ids(self, project_ids):
        tickets = None
        try:
            tickets = TicketHeader.objects.filter(project_id__in=project_ids)
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return tickets


    def get_latest_updated_tickets_from_project_id(self, project_id):
        tickets = None
        try:
            tickets = TicketHeader.objects.filter(project_id=project_id).order_by('-updated_at')[:5]
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return tickets


    def get_latest_updated_user_created_tickets_from_project_id(self, project_id, user_ids):
        tickets = None
        try:
            tickets = TicketHeader.objects.filter(project_id=project_id, created_by__in=user_ids).order_by('-updated_at')[:5]
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return tickets


    def create_ticket_data_ticket_headers(self,data_dict):
        data = TicketHeader.objects.create(**data_dict)
        return data


    def create_ticket_data_ticket_attachments(self, data_dict):
        data = TicketAttachment.objects.create(**data_dict)
        return data


    def create_ticket_data_ticket_details(self, data_dict):
        data = TicketDetails.objects.create(**data_dict)
        return data


    def create_ticket_data_ticket_watcher(self, data_dict):
        watcher_dict = []
        try:
            for each_item, value in data_dict.items():
                watcher_dict.append(TicketWatcher(watcher = value['watcher'],
                ticket_id = value['ticket_id']
                ))
            data =TicketWatcher.objects.bulk_create(watcher_dict)
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return data


    def delete_ticket_data_ticket_watcher(self, ticket_id, user_list):
        try:
            deleted = TicketWatcher.objects.filter(ticket_id=ticket_id, watcher__in=user_list).delete()
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return deleted


    # def get_ticket_header_details_by_ticket_id(self, ticket_id):
    #     data = None
    #     try:
    #         data = TicketHeader.objects.filter(ticket_id = ticket_id).first()
    #     except Exception as err:
    #         self.__log.error(self.__exception.get_exception())
    #     return data


    def get_ticket_details_by_ticket_id(self, ticket_id):
        data = None
        try:
            data = TicketDetails.objects.filter(ticket_id=ticket_id)
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return data

    def get_ticket_details_by_ticket_id_last(self, ticket_id):
        data = None
        try:
            data = TicketDetails.objects.filter(ticket_id = ticket_id).last()
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return data


    def get_ticket_by_ticket_id(self, ticket_id):
        ticket = None
        try:
            ticket = TicketHeader.objects.filter(ticket_id = ticket_id).first()
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return ticket


    def get_ticket_attachment_by_ticket_details_id_ticket_id(self, ticket_details_id):
        data = None
        try:
            data = TicketAttachment.objects.filter(ticket_details_id=ticket_details_id)
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return data


    def get_ticket_attachment_by_attachment_id(self, attachment_id):
        attachment = None
        try:
            attachment = TicketAttachment.objects.filter(attachment_id=attachment_id).first()
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return attachment


    def get_all_attachments_by_ticket_id(self, ticket_id):
        return TicketAttachment.objects.filter(ticket_id=ticket_id)



    def update_ticket_data_ticket_headers(self, ticket_header_data, ticket_id):
        return TicketHeader.objects.filter(ticket_id=ticket_id).update(**ticket_header_data)

    # def get_deadline_tickets(self, deadline_date):
    #     data = None
    #     try:
    #         data = TicketHeader.objects.filter(deadline__lt=deadline_date)
    #     except Exception as err:
    #         self.__log.error(self.__exception.get_exception())
    #     return data

    def get_last_one_ticket_detail_by_ticket_id(self, ticket_id):
        data = None
        try:
            data = TicketDetails.objects.filter(ticket_id=ticket_id).last()
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return data


    def update_ticket_details_by_id(self, message, action, ticket_details_id):
        data = None
        try:
            data = TicketDetails.objects.get(ticket_details_id=ticket_details_id)
            data.message = message
            data.action = action
            data.updated_at = timezone.now()
            data.save()
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return data



    #TicketLogTime
    def create_ticket_log_time(self, data_dict):
        data = TicketLogTime.objects.create(**data_dict)
        return data

    def get_all_ticket_log_time_by_user(self, user_id,log_date=None):
        if log_date:
            ticket_time = TicketLogTime.objects.filter(user_id=user_id, log_date=log_date)
        else:
            ticket_time = TicketLogTime.objects.filter(user_id=user_id)

        return ticket_time

    def get_all_ticket_time_ticket_ids(self, ticket_ids):
        ticket_time = None
        try:
            ticket_time = TicketLogTime.objects.filter(ticket_id__in=ticket_ids)
        except:
            ticket_time = None
        return ticket_time

    def get_ticket_log_time_by_user_ids(self, user_ids, start, end):
        ticket_time = TicketLogTime.objects.filter(user_id__in=user_ids, log_date__gte=start, log_date__lte=end)
        return ticket_time

    def get_ticket_detail_by_status(self, users, start_date, end_date, status='Reopen'):
        data = None
        try:
            data = TicketDetails.objects.filter(assigned_to__in=users,status=status,\
                 created_at__date__gte=start_date, created_at__date__lte=end_date).order_by('-ticket_details_id')
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return data
    
    def get_children_tickets(self, ticket_id):
        return TicketHeader.objects.filter(parent_id=ticket_id)
    
    def get_ticket_module_id_name(self):
        try:
            all_modules = ProjectModule.objects.all()
            data = dict(map(lambda module: (module.module_id, module.name), all_modules))
        except Exception as e:
            data = {}
        return data

    # def get_ticket_detail_by_status(self, users, start_date, end_date, ticket_ids=[], status=None):
    #     data = None
    #     try:
    #         data = TicketDetails.objects.filter(assigned_to__in=users, created_at__date__gte=start_date,
    #         created_at__date__lte=end_date)
    #         if status:
    #             data = data.filter(status=status)
    #         if ticket_ids:
    #             data = data.filter(ticket_id__in=ticket_ids)
    #     except Exception as err:
    #         self.__log.error(self.__exception.get_exception())
    #     return data