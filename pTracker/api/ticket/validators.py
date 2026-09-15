
from datetime import datetime, date, timedelta, time
# from django.http import HttpResponse
# from django.utils import timezone
# from datetime import timedelta
# from types import SimpleNamespace
# import uuid
# from django.db import  transaction
# from django.db.models import Q

from datetime import datetime
from bs4 import BeautifulSoup
from django.utils.safestring import mark_safe
from django.conf import settings
from django.db.models import Sum
from pTracker.dataaccess.ptracker_access.ticket_da import TicketDA
from pTracker.dataaccess.ptracker_access.project_da import ProjectDA
from pTracker.dataaccess.ptracker_access.ticket_models import TicketHeader
import datetime as datetimeconvert
import re

ALLOWED_EXTENSIONS = ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'jpeg', 'jpg', 'png', 'gif', 'bmp', 'tiff', 'txt', 'csv', 'odt','mp4']

#STATUS_CHECK_LIST = ['In Progress','Resolved','Completed','Released to QA','Verified by QA','ReadyPushPro','Completed']

MSG_STATUS_CHECK = ['In Progress', 'Resolved', 'Released to QA', 'Verified by QA', 'Reopen', 'Invalid', 'Deferred']

class TicketValidatorBL():
    def __init__(self):
        # self.__log = Logs()
        # self.__exception = ExceptionHandler()
        # self.__utility = Utility()
        pass

    def start_date_validation(self, start_date, is_create, ticket_status):
        pass
        # error_msg = None
        # current_date = datetime.now().date()
        # if is_create:
        #     if start_date.date() < current_date:
        #         error_msg = "The Start date should be either today or a date in the future."
        # else:
        #     pass
        # return error_msg

    def validate_files(self, file_objs):
        response = {"error": None, "status": 200}
        allowed_extensions = ALLOWED_EXTENSIONS
        if len(file_objs) > 3:
            response["error"] = "You are not allowed to upload more than 3 files at once."
            response["status"] = 499

        for each_file in file_objs:
            file_name = each_file.name
            file_size = each_file.size  # Size in bytes

            # Check the file extension
            ext = file_name.split('.')[-1].lower()
            if ext == 'mp4':
                if file_size > (10 * 1024 * 1024):
                    response["error"] = "File is too large. The maximum file size allowed is 10MB."
                    response["status"] = 499
                    break
            else:
                if file_size > (2 * 1024 * 1024):
                    response["error"] = "File is too large. The maximum file size allowed is 2MB."
                    response["status"] = 499
                    break

            if ext not in allowed_extensions:
                response["error"] = "Unsupported file type. Please upload a document, image, or MP4 file."
                response["status"] = 499
                break

        return response

    def validate_progress_dates(self,created_date=None, start_date=None, end_date=None, deadline=None,status=None,ticket=None):
        response = {"error": None, "status": 200, "success": True}
        try:
            current_date = datetime.now().date()
            created_date = self.convert_to_date(created_date)
            start_date = self.convert_to_date(start_date)
            end_date = self.convert_to_date(end_date)
            deadline = self.convert_to_date(deadline)
            deadline_check_flag = False
            start_date_check_flag = False
            end_date_check_flag = False

            if ticket:
                if ticket.deadline:
                    ticket_deadline = (ticket.deadline).date()
                    if ticket_deadline and ticket_deadline == deadline:
                        deadline_check_flag = True
                if ticket.start_date:
                    ticket_start_date = (ticket.start_date).date()
                    if ticket_start_date and ticket_start_date == start_date:
                        start_date_check_flag = True
                if ticket.end_date:
                    ticket_end_date = (ticket.end_date).date()
                    if ticket_end_date and ticket_end_date == end_date:
                        end_date_check_flag = True


            if deadline:
                if not deadline_check_flag and deadline < current_date:
                    response['error'] = 'The deadline should be either today or a future date.'
                    response["status"] = 499
                    response["success"] = False
                    return response
            else:
                if status and status in settings.STATUS_DEADLINE:
                    response['error'] = f'Deadline field cannot be empty if you select "{status}" as status, you should provide deadline'
                    response["status"] = 499

            if created_date:
                if start_date:
                    if not start_date_check_flag and start_date < created_date:
                        response['error'] = 'The start date should be on or after the created date.'
                        response["status"] = 499
                        response["success"] = False
                        return response

                if end_date:
                    if not end_date_check_flag and end_date < created_date:
                        response['error'] = 'The end date should be after or equal to the created date.'
                        response["status"] = 499
                        response["success"] = False
                        return response

                if start_date:
                    if not start_date_check_flag and start_date > current_date:
                        response['error'] = 'The start date should be the same as or less than the current date.'
                        response["status"] = 499
                        response["success"] = False
                        return response

                if end_date :
                    if not end_date_check_flag and end_date > current_date:
                        response['error'] = 'The end date should be the same as or less than the current date.'
                        response["status"] = 499
                        response["success"] = False
                        return response
            else:
                #the start date and end date should be same as current date in create ticket method
                if start_date:
                    if not start_date_check_flag and (start_date > current_date or start_date < current_date):
                        response['error'] = 'The start date should be equal to the current date.'
                        response["status"] = 499
                        response["success"] = False
                        return response

                if end_date:
                    if not end_date_check_flag and (end_date > current_date or end_date < current_date):
                        response['error'] = 'The end date should be equal to the  current date.'
                        response["status"] = 499
                        response["success"] = False
                        return response

            if start_date and end_date:
                if (not start_date_check_flag or not end_date_check_flag) and end_date < start_date:
                    response['error'] = 'The end date should be the same as or later than the start date.'
                    response["status"] = 499
                    response["success"] = False
                    return response
            response['start_date'] = start_date
            response['end_date'] = end_date
            response['deadline'] = deadline
        except Exception as err:
            response["error"] = err
        return response


    def convert_to_date(self,date_str):
        return datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else None

    def date_to_datetime(self,date_str=None):
        return datetime.strptime(date_str, "%Y-%m-%d") if date_str else None

    def date_obj_to_date(self, date_obj=None):
        return date_obj.date() if date_obj else None

    def is_str_length_valid(self, str_value, max_limit):
        is_valid =True
        if len(str_value) > max_limit:
            is_valid = False
        return is_valid


    def subject_length_validator(self, subject):
        error = None
        if not len(subject) <= 250:
            error = 'The title should be concise and clear, with a limit of 250 characters.'
        return error


    def message_validator(self, message):
        message = mark_safe(message)
        full_message = message
        message = BeautifulSoup(message, 'html.parser')
        message = message.text
        message = message.lstrip().rstrip()


        #The following validator will validate the following scenarios
        # 1) it should not accept numbers only text data
        # 2) it should not accept space only text data
        # 3) it should accept text data having numbers and letters
        # 4) it should accept letters only text data
        # 5) it should have minimum length of 4
        # 6) it should not accept special characters only text data
        # 7) it should accept text data having special character and letters, if there is special characters then there must be a letter
        # 8) It should accept letters only text data with spaces in beggining and end, or beggining or end
        # 9) It should also accept spaces in between words and letters
        # 10) It should accept letters only text data with spaces in beggining and end, or beggining or end while spaces in between.

        message_validator = r'^(?=.*[a-zA-Z])[a-zA-Z0-9!@#$%^&*()-_+=|\\[\]{};:\'",.<>/?\s]*[a-zA-Z]+[a-zA-Z0-9!@#$%^&*()-_+=|\\[\]{};:\'",.<>/?\s]*$'
        non_ascii_validator = r'[^\x00-\x7F]'
        error = 'Invalid "Message" field. Your message may have triggered one or more of the following issues: it contains only numbers, only special characters, is empty, is shorter than 4 characters, or includes non-ASCII or non-UTF characters'

        if re.match(non_ascii_validator, message):
            return error, full_message
        elif not re.match(message_validator, message) or len(message) < 4:
            return error, full_message
        else:
            return None, full_message

    def check_for_circular_parent_v1(self, parent_id, ticket_id):
        """
        Checks for circular parent-child relationships starting from the given parent_id.
        """
        visited = set()
        stack = [ticket_id]
        is_parent_child = False

        while stack:
            current_id = stack.pop()
            if current_id in visited:
                continue
            visited.add(current_id)
            if parent_id in visited:
                is_parent_child = True
                break
            children = TicketHeader.objects.filter(parent_id=current_id)
            for child in children:
                stack.append(child.ticket_id)

        return is_parent_child


    def check_for_circular_parent(self, parent_id, ticket_id):
        """
        Checks for circular parent-child relationships starting from the given parent_id.
        """
        visited = set()
        stack = [ticket_id]
        is_parent_child = False


        while stack:
            current_id = stack.pop()

            if current_id in visited:
                is_parent_child = True
                return is_parent_child

            visited.add(current_id)
            try:
                # Check if the current ticket is the ticket we're validating
                # if current_id == ticket_id:
                #     is_parent_child = True
                #     return is_parent_child

                current_ticket = TicketHeader.objects.get(ticket_id=current_id)


                # Push all children of the current ticket onto the stack
                children = TicketHeader.objects.filter(parent_id=current_id)
                for child in children:
                    stack.append(child.ticket_id)

            except TicketHeader.DoesNotExist:
                # If the ticket does not exist, ignore it.
                continue
        return is_parent_child

    def is_parent_valid(self, parent_id, project_id, ticket_id=0):
        valid_status = settings.TICKET_STATUS_OPEN
        if not parent_id:
            return True

        parent_ticket = TicketDA().get_ticket_by_ticket_id(parent_id)
        if not parent_ticket:
            return False

        if int(project_id) != int(parent_ticket.project_id):
            return False

        if str(parent_ticket.status).lower() not in list(map(lambda x: x.lower(), valid_status)):
            return False

        if ticket_id==parent_id:
            return False

        if ticket_id:
            current_ticket = TicketDA().get_ticket_by_ticket_id(ticket_id)
            if current_ticket.parent_id == parent_id:
                return True
        return True


    def is_ticket_status_valid(self, status, is_create=False):
        if is_create:
            valid_status = [status.lower() for status in settings.NEW_TICKET_STATUS]
        else:
            valid_status = [status[0].lower() for status in settings.TICKETS_STATUS_CHOICES]
        if str(status).lower() not in valid_status:
            return False
        return True

    def reopen_status_valid(self, status, previous_status):
        error_msg = None
        if str(status).lower() == 'reopen':
            valid_status = [status.lower() for status in settings.REOPEN_REQUIRED_STATUS]
            status_names = ', '.join(settings.REOPEN_REQUIRED_STATUS)
            if str(previous_status).lower() not in valid_status:
                error_msg = f"If you need to change the status to Reopen, the previous status should be one of the following: {status_names}."
        return error_msg

    def is_ticket_type_valid(self, ticket_type):
        valid_types = [ticket_type[0].lower() for ticket_type in settings.TICKETS_TYPE_CHOICES]
        if str(ticket_type).lower() not in valid_types:
            return False
        return True

    def estimated_time_validation(self, estimated_time_sec, status):
        MAX_HOURS = 288000 # 80 Hours in seconds
        error_msg = None

        try:
            estimated_time_sec = int(estimated_time_sec)
        except:
            estimated_time_sec = 0

        if estimated_time_sec > MAX_HOURS:
            error_msg = "The maximum estimated time limit for a ticket is 80 hours. If you need more time, please split the ticket into smaller tickets."
            return error_msg

        valid_status = [status.lower() for status in settings.STATUS_DEADLINE]
        if status.lower() in valid_status:
            if estimated_time_sec <= 0:
                error_msg = f'The Estimated Time field cannot be empty if you select "{status}" as the status. Please provide an estimated time.'
                return error_msg

        return error_msg

    def is_ticket_category_valid(self, ticket_category):
        valid_categories = [category[0].lower() for category in settings.TICKET_CATEGORIES]
        if not ticket_category:
            return True
        if str(ticket_category).lower() not in valid_categories:
            return False
        return True

    def is_ticket_priority_valid(self, priority):
        valid_priority = [priority[0].lower() for priority in settings.TICKETS_PRIORITY_CHOICES]
        if str(priority).lower() not in valid_priority:
            return False
        return True

    def message_validate_by_status(self, status=None):
        response = {"error": None, "status": 200, "success": True}
        valid_status = [status.lower() for status in settings.MSG_REQUIRED_STATUS]
        if str(status).lower() in valid_status:
            response["error"] = f'Message field cannot be empty if you select "{status}" as status, you should provide "{status}" status details'
            response["status"] = 499
            response["success"] = False
        return response

    def time_log_validtor(self, log_time, log_date, user_id, ticket=None):
        response = {"error":'', "status":499, 'log_time':0, 'log_date':None}
        MAX_HOURS = 57600 #16 Hours in seconds
        total_log_time = 0
        log_time_sec = 0

        try:
            today = datetime.now().date()
            log_time = int(log_time)
            if not log_time:
                response['log_time'] = 0
                response['log_date'] = None
                return response

            log_time_sec = log_time*60

            if not log_date:
                log_date = datetime.now().date()
            else:
                log_date = self.convert_to_date(log_date)

            if not ticket:
                ticket_create_date = today
            else:
                ticket_create_date = ticket.created_at.date()


            ticket_time = TicketDA().get_all_ticket_log_time_by_user(user_id, log_date)
            if ticket_time:
                total_log_time = ticket_time.aggregate(total=Sum('log_time'))['total'] or 0

            total_log_time += log_time_sec
            if total_log_time > MAX_HOURS:
                response["error"] = "You are not able to log more than 16 hours in a day."
                return response

            if not (log_date>=ticket_create_date and log_date<=today):
                response["error"] = "The log date must be within the ticket creation date and today."
                return response

            response['log_time'] = log_time
            response['log_date'] = log_date

        except Exception as err:
            response["error"] = err

        return response

    def check_sub_tickets_completion(self, sub_tickets_dict, parent_status):
        """
        Parameters:
            sub_tickets_dict (dict): Dictionary containing sub-tickets with their details.
            parent_status (str): The status of the main ticket.

        Returns:
            dict: Updated response dictionary.
        """
        response = {"error": None, "status": 200, "success": True}

        status_requirements = {
            "Completed": settings.TICKET_STATUS_OPEN,
            "Resolved": settings.TICKET_STATUS_CLOSED + ["Resolved", "Released to QA", "Verified by QA", "ReadyPushPro"],
            "Released to QA": settings.TICKET_STATUS_CLOSED + ["Released to QA", "Verified by QA", "ReadyPushPro"],
            "Verified by QA": settings.TICKET_STATUS_CLOSED + ["Verified by QA", "ReadyPushPro"],
            "ReadyPushPro": settings.TICKET_STATUS_CLOSED + ["ReadyPushPro"],
            "Invalid": settings.TICKET_STATUS_CLOSED
        }

        required_statuses = status_requirements.get(parent_status)

        if sub_tickets_dict and required_statuses:
            for key, value in sub_tickets_dict.items():
                if parent_status == "Completed" and value["status"] in required_statuses:
                    response["error"] = f'A sub ticket with id #"{value["ticket_id"]}" is open, please close the sub ticket first.'
                    response["status"] = 499
                    break

                elif parent_status != "Completed" and value["status"] not in required_statuses:
                    response["error"] = f'Sub-ticket with ID #"{value["ticket_id"]}" is in a lower status than its parent ticket, which is marked as "{parent_status}".'
                    response["status"] = 499
                    break

        return response

    def forced_to_reopen(self, current_status, new_status):
        current_status = str(current_status).lower()
        new_status = str(new_status).lower()
        msg = "You can only 'Reopen' this ticket at this moment; no other 'open' status is valid at this time."
        error_msg = None
        closed_status = [status.lower() for status in settings.TICKET_STATUS_CLOSED]
        if current_status in closed_status:
            if new_status != 'reopen':
                error_msg = msg

        elif current_status == 'released to qa':
            valid_status = settings.TICKET_STATUS_CLOSED + ['Released to QA', 'Verified by QA', 'Reopen', 'ReadyPushPro', 'Deferred', 'Resolved']
            valid_status_lst = [status.lower() for status in valid_status]
            if new_status not in valid_status_lst:
                error_msg = "You can only 'Reopen' this ticket at this moment; no other 'open' status except 'Resolved', 'Verified by QA', 'ReadyPushPro' and 'Deferred' is valid at this time."

        elif current_status == 'verified by qa':
            valid_status = settings.TICKET_STATUS_CLOSED + ['Verified by QA', 'ReadyPushPro', 'Reopen', 'Deferred']
            valid_status_lst = [status.lower() for status in valid_status]
            if new_status not in valid_status_lst:
                error_msg = "You can only 'Reopen' this ticket at this moment; no other 'open' status except 'ReadyPushPro' and 'Deferred' is valid at this time."

        elif current_status == 'readypushpro':
            valid_status = settings.TICKET_STATUS_CLOSED + ['ReadyPushPro', 'Reopen', 'Deferred']
            #valid_status.append('Reopen')
            #valid_status.append('Deferred')
            valid_status_lst = [status.lower() for status in valid_status]
            if new_status not in valid_status_lst:
                error_msg = "You can only 'Reopen' this ticket at this moment; no other 'open' status except 'Deferred' is valid at this time."

        return error_msg



    def validate_parent_ticket_status_by_child(self, parent_id, child_status):
        response = {"parent_ticket_current_status": None, "error":False}
        try:
            #parent_ticket_id = parent_id

            response = {"error": None, "status": 200, "success": True}

            if str(child_status).lower() == "new":
                return response

            status_requirements = {
                "New": ["New", "In Progress", "Deferred", "Reopen"],
                "In Progress": ["New", "In Progress", "Deferred", "Reopen"],
                "Reopen": ["New", "In Progress", "Deferred", "Reopen"],
                "Resolved": ["Resolved", "New", "In Progress", "Deferred"],
                "Released to QA": ["Released to QA", "Resolved", "New", "In Progress", "Deferred", "Reopen"],
                "Verified by QA": ["Verified by QA", "Released to QA", "Resolved", "New", "In Progress", "Deferred", "Reopen"],
                "ReadyPushPro": ["ReadyPushPro", "Verified by QA", "Released to QA", "Resolved", "New", "In Progress", "Deferred", "Reopen"],
                "Deferred": ["New", "In Progress", "Deferred", "Reopen"],
            }

            parent_ticket_id = parent_id
            parent_ticket = TicketDA().get_ticket_head_by_ticket_id(parent_ticket_id)
            parent_status = parent_ticket.status  #str(parent_ticket.status).lower()

            required_statuses = status_requirements.get(child_status, [])

            if parent_status not in ['Resolved', 'Released to QA', 'Verified by QA', 'ReadyPushPro', 'Completed', 'Invalid']:
                return response
            
            if child_status in settings.TICKET_STATUS_CLOSED:
                return response

            if parent_status in settings.TICKET_STATUS_CLOSED and child_status not in settings.TICKET_STATUS_CLOSED:
                response["error"] = f'The parent ticket with id #{parent_id} is in a closed status, so this child should also be closed. If you need to make changes, please reopen the parent ticket first.'
                response["status"] = 499
                return response

            elif parent_status not in settings.TICKET_STATUS_CLOSED and parent_status not in required_statuses:
                response["error"] = f"The parent ticket with ID #{parent_id} is in a higher status ({parent_status}) than the child ticket ({child_status}). Either reopen the parent ticket or update the child ticket status to match the parent ticket's status."
                response["status"] = 499
                return response
            return response

        except:
            self.__log.error(self.__exception.get_exception())
            return response


    def get_parent_ticket_status_validator(self, parent_id, child_ticket_previous_status, child_ticket_current_status):
        response = {"parent_ticket_current_status": None, "error":False}
        try:
            parent_ticket_id = parent_id
            parent_ticket = TicketDA().get_ticket_head_by_ticket_id(parent_ticket_id)
            parent_ticket_previous_status = parent_ticket.status
            parent_ticket_current_status = child_ticket_current_status

            parent_ticket_current_status = child_ticket_current_status

            if not parent_ticket_previous_status in ['Resolved', 'Released to QA', 'Verified by QA', 'ReadyPushPro', 'Completed']:
                response['error'] = "Parent ticket not in ['Resolved', 'Released to QA', 'Verified by QA', 'ReadyPushPro', 'Completed']"
                return response


            if child_ticket_previous_status in settings.TICKET_STATUS_CLOSED and child_ticket_current_status in settings.TICKET_STATUS_OPEN:
                # parent_ticket_current_status = child_ticket_current_status
                if child_ticket_current_status in ['In Progress', 'Deferred']:
                    parent_ticket_current_status = 'Reopen'
                else:
                    parent_ticket_current_status = child_ticket_current_status
            if child_ticket_previous_status in ['Resolved'] and child_ticket_current_status in ['New', 'In Progress', 'Reopen', 'Deferred']:
                if parent_ticket_previous_status in ['Resolved', 'Released to QA', 'Verified by QA', 'ReadyPushPro','Completed']:
                    parent_ticket_current_status = 'Reopen'
            if child_ticket_previous_status in ['Invalid'] and child_ticket_current_status in settings.TICKET_STATUS_OPEN:
                if child_ticket_current_status in ['New', 'In Progress', 'Deferred']:
                    parent_ticket_current_status = 'Reopen'
                if child_ticket_current_status in ['Resolved', 'Released to QA', 'Verified by QA', 'Reopen', 'ReadyPushPro', 'Deferred']:
                    parent_ticket_current_status = child_ticket_current_status

            if child_ticket_previous_status in ['Released to QA']:
                if child_ticket_current_status in ['Resolved', 'Reopen']:
                    parent_ticket_current_status = child_ticket_current_status
                elif child_ticket_current_status in ['Deferred']:
                    parent_ticket_current_status = 'Reopen'
            if child_ticket_previous_status in ['Verified by QA']:
                if child_ticket_current_status in ['In Progress', 'New', 'Deferred']:
                    parent_ticket_current_status = 'Reopen'
                elif child_ticket_current_status in ['Released to QA', 'Resolved', 'Reopen']:
                    parent_ticket_current_status = child_ticket_current_status

            if child_ticket_previous_status in ['ReadyPushPro']:
                if child_ticket_current_status in ['Verified by QA', 'Released to QA', 'Resolved']:
                    parent_ticket_current_status = child_ticket_current_status
                elif child_ticket_current_status in ['In Progress', 'New', 'Deferred']:
                    parent_ticket_current_status = 'Reopen'

            if child_ticket_previous_status in ['Completed'] and child_ticket_current_status not in ['Invalid']:
                if child_ticket_current_status in ['Verified by QA', 'Released to QA', 'Resolved']:
                    parent_ticket_current_status = child_ticket_current_status
                elif child_ticket_current_status in ['In Progress', 'New', 'Deferred']:
                    parent_ticket_current_status = 'Reopen'

            if parent_ticket_current_status == parent_ticket_previous_status:
                response['error'] = "There is no change in parent ticket status"
            else:
                response['parent_ticket_current_status'] = parent_ticket_current_status

        except:
            self.__log.error(self.__exception.get_exception())
        finally:
            return response
        
    
    def check_ticket_status_validty(self, current_status, new_status):
        error_message = None  
        
        if str(current_status).lower() == str(new_status).lower():
            return error_message
        
        if str(current_status).lower() == "new" :            
            valid_status = list(map(lambda x: x.lower(), settings.NEW_REQUIRED_STATUS)) 
            if str(new_status).lower() not in valid_status :
                error_message = "You can only move a 'New' ticket to 'Acknowledged', 'In Progress,' 'Invalid,' or 'Deferred' status."
            
        elif str(current_status).lower() == "reopen" :            
            valid_status = list(map(lambda x: x.lower(), settings.NEW_REQUIRED_STATUS)) 
            if str(new_status).lower() not in valid_status :
                error_message = "You can only move a 'Reopen' ticket to 'Acknowledged', 'In Progress,' 'Invalid,' or 'Deferred' status."
        
        return error_message 
    
    def repo_id_vallidate(self, repo_id):
        response = {"error":'', 'is_repo_id_valid':0}
        
        try:
            filter_criteria = {}
            filter_criteria['repo_id'] = repo_id
            is_repo_id_valid = ProjectDA().get_all_project_repo_by_filter_criteria(filter_criteria)
            if is_repo_id_valid:
                response['is_repo_id_valid'] = is_repo_id_valid
            else:
                response['error'] = "The repo id you have entered is not valid"
        except:
            response['error'] = self.__log.error(self.__exception.get_exception())
        return response

    def module_id_vallidate(self, module_id):
        response = {"error":'', 'is_module_id_valid':0}
        
        try:
            is_module_id_valid = ProjectDA().get_project_module(module_id)
            if is_module_id_valid:
                response['is_module_id_valid'] = is_module_id_valid
            else:
                response['error'] = "The module id you have entered is not valid"
        except:
            response['error'] = self.__log.error(self.__exception.get_exception())
        return response
