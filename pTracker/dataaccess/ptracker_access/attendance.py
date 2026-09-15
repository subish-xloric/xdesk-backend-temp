from pTracker.dataaccess.ptracker_access.models import DailyAttendance
from pTracker.dataaccess.ptracker_access.models import WFHRequest

from pTracker.common.utility import Utility
from pTracker.dataaccess.db import Connection

from django.conf import settings
from django.db.models import Q


class AttendanceDA:

    def create_daily_attendance(self, dto):
        try:
            attendance = DailyAttendance(
                attendance_date=dto.attendance_date,
                company_id=dto.company_id,
                emp_code=dto.emp_code,
                total_hours=dto.total_hours,
                work_hours=dto.total_floor_hours,
                break_hours=dto.break_hours,
                arrival=Utility().convert_string_to_date_time(str(dto.arrival)),
                departure=Utility().convert_string_to_date_time(str(dto.departure)))
            attendance.save()
        except Exception as e:
            msg = """Error in the method create_daily_attendance,
            Error: {0}""".format(str(e))
            Utility().log(msg)

    def get_attendance_by_range(self, start_date, end_date):
        try:
            att_list = DailyAttendance.objects.filter(attendance_date__gte=start_date, attendance_date__lte=end_date)

        except Exception as e:
            msg = """Error in the method get_attendance_by_range,
            Error: {0}""".format(str(e))
            Utility().log(msg)
        return att_list

    def get_all_wfh_requests_by_user_id(self, user_id):
        return WFHRequest.objects.filter(emp_id=user_id).order_by('-wfh_id')

    def get_all_wfh_requests_by_status(self, status):
        return WFHRequest.objects.filter(status=status).order_by('-wfh_id')


    def create_wfh_request(self, wfh_data):
        return WFHRequest.objects.create(**wfh_data)

    def update_wfh_request(self, wfh_id, wfh_data, user_id=0):
        if not user_id:
            return  WFHRequest.objects.filter(wfh_id=wfh_id).update(**wfh_data)
        else:
            return  WFHRequest.objects.filter(wfh_id=wfh_id, emp_id=user_id).update(**wfh_data)

    def get_approved_wfh_request(self,user_id,date):
        query = f"""SELECT wfh_id FROM wfh_requests
                        where '{date}' between start_date
                        and end_date and status=2
                        and emp_id={user_id};"""

        conn = Connection('default')
        results, error = conn.execute(query)
        if error:
            results = None
            Utility().log(error)
        return results
    
    
    def get_wfh_period_by_date(self, obj_date):
        try:
            period = WFHRequest.objects.get(start_date__lte=obj_date,end_date__gte=obj_date)
        except Exception as e:
            period = None
        return period
    
    
    def get_employee_wfh_by_date(self, start_date, end_date, emp_id):
        return WFHRequest.objects.filter(emp_id=emp_id, start_date__gte=start_date, end_date__lte=end_date)
    
    
    def get_wfhs_by_date_range(self, start_date, end_date):
        return WFHRequest.objects.filter(start_date__gte=start_date, end_date__lte=end_date)
    

    def get_all_wfh_requests(self):
        return WFHRequest.objects.all().order_by('-wfh_id')

    def get_wfh_request_by_id(self,wfh_id):
        return WFHRequest.objects.get(wfh_id = wfh_id)

    def get_wfh_request_date_overlap(self,start_date,end_date,user_id):
        # hard coded because in constants WFH_REQUEST_STATUS
        # 1 Requested
        # 2 Approved
        results=WFHRequest.objects.filter(
                            Q(status=1)
                            | Q(status=2),
                            emp_id=int(user_id),start_date__lte=end_date,end_date__gte=start_date)
        return results

    def get_team_wfh_requests_by_status(self,status):
        if status:
            return WFHRequest.objects.filter(status = int(status)).order_by('-wfh_id')
        else:
            return WFHRequest.objects.all().order_by('-wfh_id')

    def get_team_wfh_requests_by_status_list(self,status):
        if status:
            return WFHRequest.objects.filter(status__in = status).order_by('-start_date')
        else:
            return WFHRequest.objects.all().order_by('-wfh_id')

    def get_attendance_by_emp_id_and_date(self, emp_id, start_date):
        try:
            return DailyAttendance.objects.get(emp_code=emp_id, attendance_date=start_date)
        except:
            return None

    def get_wfh_request_by_user_id_and_status(self, user_id, status):
        return WFHRequest.objects.filter(emp_id=user_id, status = status)





