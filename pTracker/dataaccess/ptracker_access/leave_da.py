import datetime
from types import SimpleNamespace
from django.conf import settings

from django.contrib.auth.models import User
from django.db.models import Q
from django.contrib.auth.models import Group

from pTracker.dataaccess.db import Connection
from pTracker.dataaccess.company_scope import ALL_COMPANIES, filter_by_company
from pTracker.common.utility import Utility
from pTracker.dataaccess.ptracker_access.leave_models import CompensatoryLeaveRequestLog, Leave
from pTracker.dataaccess.ptracker_access.leave_models import LeaveQuota, LeaveType
from pTracker.dataaccess.ptracker_access.leave_models import LeaveRequestLog
from pTracker.dataaccess.ptracker_access.leave_models import LeaveRequests
from pTracker.dataaccess.ptracker_access.leave_models import LeavePeriod
from pTracker.dataaccess.ptracker_access.leave_models import LeaveQuota
from pTracker.dataaccess.ptracker_access.leave_models import CompensatoryLeaveRequest
from pTracker.dataaccess.ptracker_access.user_models import UserProfile
from pTracker.settings import constants


def new_dto():
    dto = SimpleNamespace()
    return dto

class LeaveDA():

    def __init__(self):
        pass

    def create_leave_quota(self, quota_data):
        return LeaveQuota.objects.create(**quota_data)

    def get_employee_leave_by_date(self, start_date, end_date, emp_id):
        return Leave.objects.filter(employee_id=emp_id, leave_date__gte=start_date, leave_date__lte=end_date)


    def get_leave_by_user_id(self,user_id,from_date,to_date):
        try:
            results = Leave.objects.filter(leave_date__range=[from_date,to_date],
                            status= constants.LEAVE_REQUEST_STATUS['Approved'])
        except Exception as err:
            results=None
        return results

    def get_all_leave_types(self, company_id=ALL_COMPANIES):
        """ Enabled leave types of one company (none for company_id=None); the
        ALL_COMPANIES default is only for id -> name lookups. """
        return filter_by_company(LeaveType.objects.filter(available_flag=1), company_id)

    def get_leave_type_code_name_dict(self):
        """ leave_type_id -> (system code or None, name), across all companies. """
        return {type_id: (code, name) for type_id, code, name in
                LeaveType.objects.values_list('leave_type_id', 'code', 'leave_type_name')}

    def get_leave_type_by_code(self, company_id, code):
        return LeaveType.objects.filter(company_id=company_id, code=code).first()

    def get_company_leave_types(self, company_id):
        """ Every leave type of the company, disabled ones included (admin list). """
        return filter_by_company(LeaveType.objects.all(), company_id).order_by('leave_type_name')

    def get_company_leave_type(self, company_id, leave_type_id):
        return LeaveType.objects.filter(company_id=company_id, leave_type_id=leave_type_id).first()

    def leave_type_name_exists(self, company_id, name, exclude_id=None):
        leave_types = LeaveType.objects.filter(company_id=company_id, leave_type_name__iexact=name)
        if exclude_id:
            leave_types = leave_types.exclude(leave_type_id=exclude_id)
        return leave_types.exists()

    def seed_leave_types(self, company_id, leave_types):
        """ leave_types: (code, name, default_no_of_leaves) tuples. """
        LeaveType.objects.bulk_create([
            LeaveType(company_id=company_id, code=code, leave_type_name=name,
                      default_no_of_leaves=default_days, available_flag=1)
            for code, name, default_days in leave_types])

    def create_leave_type(self, data):
        return LeaveType.objects.create(**data)

    def update_leave_type(self, leave_type_id, data):
        return LeaveType.objects.filter(leave_type_id=leave_type_id).update(**data)

    def get_leaves_by_user_id(self, user_id, period):
        try:
            q = f'''SELECT l.status ,l.length_hours ,l.type_id ,l.leave_date
                    FROM leaves l
                    JOIN leave_requests lr
                    WHERE lr.request_id = l.leave_request_id
                    AND lr.leave_period_id = {period}
                    AND l.employee_id = {user_id}'''
            conn = Connection('default')
            results, error = conn.execute(q)
            if error:
                results = None
                Utility().log(error)
        except Exception as err:
            Utility().log(err)
            return None
        finally:
            return results

    def get_leave_quota_by_user_id(self, user_id, period):
        return LeaveQuota.objects.filter(leave_period_id=period, employee_id=user_id)


    def get_leave_requests_by_user_id(self, user_id, period):
        return LeaveRequests.objects\
            .filter(leave_period_id=period, employee_id=user_id).order_by('-request_id')


    # def get_leave_period_by_date(self, current_date):
    #     try:
    #         period = LeavePeriod.objects.get(
    #             leave_period_start_date__lt=current_date,
    #             leave_period_end_date__gt=current_date
    #         )
    #         return period.leave_period_id
    #     except Exception as err:
    #         Utility().log(err)
    #         return None

    def get_leave_action_log_(self):
        try:
            return LeaveRequestLog.objects.all()
        except Exception as err:
            Utility().log(err)
            return None

    def get_leave_request_action_log(self, request_id):
        return LeaveRequestLog.objects.filter(request_id=request_id)


    def update_leave_status(self, req_id, status, comment="", approver=0):

        if status in (3, 4): #Remove leave if status is cancelled or rejected
            Leave.objects.filter(leave_request_id=int(req_id)).delete()
        else:
            Leave.objects.filter(leave_request_id=int(req_id)).update(status=status)

        if status in (2, 4): #Approve #TODO confirm with lead
            return LeaveRequests.objects.filter\
                (request_id=req_id).update(status=status, comment=comment, approver=approver)
        else:
            return LeaveRequests.objects.filter\
                (request_id=req_id).update(status=status, comment=comment)


    def get_leave_date_overlap(self,start_date,end_date,user_id):
        try:
            results=Leave.objects.filter(
                                Q(status=settings.LEAVE_REQUEST_STATUS['Requested'])
                                | Q(status=settings.LEAVE_REQUEST_STATUS['Approved']),
                                employee_id=user_id,leave_date__range=[start_date,end_date])
        except Exception as err:
            results=None
        return results

    def create_leave_request(self, leave_request_data):
        return LeaveRequests.objects.create(**leave_request_data)

    def create_leave(self, leave_data):
        return Leave.objects.create(**leave_data)

    def  get_leave_taken(self,leave_type_id, user_id, leave_period_id):
        try:
            return Leave.objects.filter(
                            Q(status= settings.LEAVE_REQUEST_STATUS['Requested']) |
                            Q(status= settings.LEAVE_REQUEST_STATUS['Approved']),
                            employee_id=user_id,leave_period_id=leave_period_id,
                            type_id=leave_type_id)

        except Exception as err:
            return None

    def get_leave_quota(self,user_id,leave_period_id,leave_type_id):
        try:
            return LeaveQuota.objects.get(leave_type_id=leave_type_id,
                        employee_id=user_id,leave_period_id=leave_period_id)
        except Exception as err:
            return None

    def create_leave_log(self, leave_log):
        return LeaveRequestLog.objects.create(**leave_log)

    def get_leave_period_by__date(self, start_date, company_id):
        return self.get_leave_period_by_date(start_date, company_id)

    def get_leave_request(self,request_id):
        try:
            leave_request = LeaveRequests.objects.get(request_id=request_id)
            return leave_request
        except Exception as err:
            return None

    def get_team_leave_requests(self, period_id, employee_ids, statuses):
        return LeaveRequests.objects.filter(leave_period_id=period_id, employee_id__in=list(employee_ids),
                                            status__in=list(statuses)).order_by('-start_date', '-request_id')

    def get_leave_day_types(self, request_ids):
        """ request_id -> leave_day_type of its first leave day (1 full, 2 / 3 half). """
        day_types = {}
        for request_id, day_type in Leave.objects.filter(leave_request_id__in=list(request_ids))\
                .order_by('leave_date').values_list('leave_request_id', 'leave_day_type'):
            day_types.setdefault(request_id, day_type)
        return day_types

    def get_leave_day_type(self,request_id):
        try:
            leave = Leave.objects.get(leave_request_id=request_id)
            return leave.leave_day_type
        except Exception as err:
            return None

    def delete_leaves(self, edit_request_id):
        return  Leave.objects.filter(leave_request_id=edit_request_id).delete()

    def update_leave_request(self,edit_request_id,leave_request_data):
        try:
            update = LeaveRequests.objects.filter(request_id=edit_request_id).update(**leave_request_data)
            return update
        except Exception as err:
            return None

    def get_leaves_by_date_range(self, start_date, end_date):
        return Leave.objects.filter(leave_date__gte=start_date, leave_date__lte=end_date)
    
    def get_leaves_by_date_range_v1(self, start_date, end_date, emp_id):
        return Leave.objects.filter(leave_date__gte=start_date, leave_date__lte=end_date, employee_id=emp_id)

    def get_all_active_users_profile(self):
        return  UserProfile.objects.all()

    def get_all_leave_requests(self):
        return LeaveRequests.objects.all()
    
    def get_employee_leave_by_date_v1(self, start_date, end_date, emp_id):
        # This method is created to obtain full-day leaves only.
        return Leave.objects.filter(employee_id=emp_id, leave_date__gte=start_date, \
            leave_date__lte=end_date,leave_day_type=1).values_list('leave_date', flat=True)




































    def get_team_leaves_by_user_id(self, user_id, period):
        try:
            return LeaveRequests.objects.filter(employee_id = user_id, leave_period_id = period).order_by('-request_id')
        except Exception as err:
            Utility().log(err)
            return None

    def get_leave_period_by_date(self, obj_date, company_id):
        """ The company's leave period covering obj_date, or None (also when
        company_id is None - never another company's period). """
        if company_id is None or obj_date is None:
            return None
        if isinstance(obj_date, datetime.datetime):
            obj_date = obj_date.date()
        return LeavePeriod.objects.filter(company_id=company_id, leave_period_start_date__lte=obj_date,
                                          leave_period_end_date__gte=obj_date).first()

    def get_employee_leave_period(self, employee_id, obj_date):
        """ The leave period covering obj_date in the employee's company. """
        company_id = UserProfile.objects.filter(user_id=employee_id).values_list('company_id', flat=True).first()
        return self.get_leave_period_by_date(obj_date, company_id)

    def create_leave_period(self, company_id, start_date, end_date):
        return LeavePeriod.objects.create(company_id=company_id, leave_period_start_date=start_date,
                                          leave_period_end_date=end_date)


    def get_all_leaves_by_date_range(self, start_date, end_date, status):
        return Leave.objects.filter(
                leave_date__range=[start_date, end_date],
                status__in=status).order_by('-leave_id')

    def get_comp_off_dates_overlap(self,start,end,user_id):
        try:
            #TODO Review the logic
            results=CompensatoryLeaveRequest.objects.filter(
                            Q(status=settings.LEAVE_REQUEST_STATUS['Requested'])
                            | Q(status=settings.LEAVE_REQUEST_STATUS['Approved']),
                            employee_id=user_id,start_date__lte=end,end_date__gte=start)
        except Exception as err:
            results = None
        return results

    def create_comp_off_request(self,comp_off_data):
        return CompensatoryLeaveRequest.objects.create(**comp_off_data)

    def create_comp_off_log(self,comp_off_log_data):
        return CompensatoryLeaveRequestLog.objects.create(**comp_off_log_data)

    def get_all_my_comp_off_requests(self,user_id,leave_period_id):
        return CompensatoryLeaveRequest.objects.filter(employee_id=user_id,\
            leave_period_id=leave_period_id).order_by('-comp_off_id')

    def get_all_comp_off_requests_by_status(self,leave_period_id):
        return CompensatoryLeaveRequest.objects.filter(leave_period_id=leave_period_id).order_by('-comp_off_id')

    def get_all_comp_off_logs(self):
        return CompensatoryLeaveRequestLog.objects.all()

    def update_comp_off_request(self, comp_off_id, comp_off_data, user_id=0):
        if not user_id:
            return  CompensatoryLeaveRequest.objects.filter(comp_off_id=comp_off_id).update(**comp_off_data)
        else:
            return  CompensatoryLeaveRequest.objects.filter(comp_off_id=comp_off_id, employee_id=user_id).update(**comp_off_data)

    def get_total_leave_quota_by_period(self, period):
        str_sql = f'''SELECT  employee_id, sum(no_of_days_allotted)
        FROM leave_quota
        WHERE leave_period_id={period}
        GROUP BY employee_id'''
        conn = Connection('default')
        return conn.execute(str_sql)

    def get_compensatory_leave_by_id(self,comp_off_id):
        try:
            return CompensatoryLeaveRequest.objects.get(comp_off_id=comp_off_id)
        except:
            return None

    def updateLeaveQuota(self,leave_type_id,employee_id,comp_off_duration,leave_period_id):
        data = LeaveQuota.objects.get(employee_id = employee_id,leave_period_id = leave_period_id,leave_type_id = leave_type_id)
        total = data.no_of_days_allotted + comp_off_duration
        data.no_of_days_allotted = total
        data.save()
        return data

    def get_all_employees_leave_quota(self, leave_period_id, employee_ids=None):
        quotas = LeaveQuota.objects.filter(leave_period_id = leave_period_id)
        if employee_ids is not None:
            quotas = quotas.filter(employee_id__in=employee_ids)
        return quotas

    def count_quotas_of_employees(self, quota_ids, employee_ids):
        return LeaveQuota.objects.filter(quota_id__in=quota_ids, employee_id__in=employee_ids).count()

    def update_leave_quota_by_id(self,quota_id, no_of_days_allotted):
        return LeaveQuota.objects.filter(quota_id = quota_id).update(no_of_days_allotted = no_of_days_allotted)

    def get_all_leave_requests_by_period(self, period):
        return LeaveRequests.objects.filter(leave_period_id = period).order_by('-request_id')

    def get_leave_requests_by_date_and_emp_id(self, obj_date, user_id):
        try:
            return LeaveRequests.objects.get(employee_id = user_id, start_date = obj_date,\
                 status = settings.LEAVE_REQUEST_STATUS['Requested'])
        except:
            return None

    def get_leave_request_by_comp_off_id(self, req_id):
        try:
            return LeaveRequests.objects.get(comp_off_id = req_id)
        except:
            return None

    def get_leave_log_by_req_id(self, req_id):
        try:
            return LeaveRequestLog.objects.filter(request_id = req_id)
        except:
            return None
    
    def get_leave_request_by_status_v1(self, status = 0):
        try:
            return LeaveRequests.objects.filter(status = status)
        except:
            return None

    def get_leave_details_by_period_id_and_leave_day_types(self, period, leave_day_types):
        return Leave.objects.filter(leave_period_id = period, leave_day_type__in =leave_day_types)

    def count_leave_requests(self, period_id, status, employee_ids):
        return LeaveRequests.objects.filter(leave_period_id=period_id, status=status,
                                            employee_id__in=employee_ids).count()

    def get_all_leave_requests_by_period_and_status(self, period, status):
        return LeaveRequests.objects.filter(leave_period_id = period,status = status).order_by('-request_id')
    
    def get_available_leaves(self, user_id, leave_period_id, leave_type_id):
        return LeaveQuota.objects.filter(employee_id=user_id,leave_period_id=leave_period_id, leave_type_id=leave_type_id)








