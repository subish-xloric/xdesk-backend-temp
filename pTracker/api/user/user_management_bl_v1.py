from io import BytesIO
import os
from pickle import TRUE
from types import SimpleNamespace
from datetime import datetime, timedelta, date
from unittest import result
import uuid

from django.conf import settings
from django.template.loader import get_template
from django.core.mail import EmailMessage

from django.db import DatabaseError, transaction
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.core.files.images import get_image_dimensions

from pTracker.common.utility import Utility
from pTracker.common.company_context import get_active_company_id
from pTracker.common.company_modules import is_catalog_module_disabled
from pTracker.api.attendance_v2.checkin_biz import SelfCheckInBL
from pTracker.dataaccess.attendance_v2_access.constants import PUNCH_OUT
from pTracker.dataaccess.attendance_v2_access.org_da import OrgDA
from pTracker.common.company_authorization import data_scope, SCOPE_ALL, SCOPE_TEAM
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.common.logs import Logs
from pTracker.common.crypto_handler import CryptoHandler
from pTracker.common.file_manager import FileManager
from pTracker.api.user.access_biz import AccessBL

from pTracker.notification_center.email_engine import Email
from pTracker.dataaccess.ptracker_access.user_da import UserDA
from pTracker.dataaccess.ptracker_access.attendance import AttendanceDA
from pTracker.dataaccess.ptracker_access.leave_da import LeaveDA
from pTracker.api.user.anniversary_biz import AnniversaryBL
from pTracker.dataaccess.ptracker_access.project_da import ProjectDA
from pTracker.wiki.data_access.master.logs_da import LogsDA

from rest_framework.response import Response
from pTracker.common.company_authorization import has_capability
from pTracker.common.company_authorization import users_with_capability
from pTracker.common.company_context import get_active_company
from pTracker.dataaccess.platform_access.tenancy_da import TenancyDA






def new_dto():
    dto = SimpleNamespace()
    return dto

class UserManagementBL_V1():
    def __init__(self):
        self.__exception = ExceptionHandler()
        self.__utility = Utility()
        self.__logs = Logs()
        self.__file_manager = FileManager()

    def save_commen_headers(self, ret, headers):
        try:
            head = {}
            head["app_version"] = headers.get("HTTP_APP_VERSION", "")
            head["build_number"] = headers.get("HTTP_BUILD_NUMBER", "")
            head["device_type"] = headers.get("HTTP_DEVICE_TYPE", "")
            head["device_os_version"] = headers.get("HTTP_DEVICE_OS_VERSION", "")
            head["device_identifier"] = headers.get("HTTP_DEVICE_IDENTIFIER", "")
            head["user_id"] = ret.get("user")["pk"]
            UserDA().create_or_update_mobile_common_headers(ret.get("user")["pk"], head)
        except Exception as err:
            print(err)
            response = {}
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__logs.error(self.__exception.get_exception()))
            return Response(response)

    def save_commen_headers_by_user_id(self, user_id, headers):
        try:
            head = {}
            head["app_version"] = headers.get("HTTP_APP_VERSION", "")
            head["build_number"] = headers.get("HTTP_BUILD_NUMBER", "")
            head["device_type"] = headers.get("HTTP_DEVICE_TYPE", "")
            head["device_os_version"] = headers.get("HTTP_DEVICE_OS_VERSION", "")
            head["device_identifier"] = headers.get("HTTP_DEVICE_IDENTIFIER", "")
            head["user_id"] = user_id
            UserDA().create_or_update_mobile_common_headers(user_id, head)
        except Exception as err:
            print(err)
            response = {}
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__logs.error(self.__exception.get_exception()))
            return Response(response)

    def format_login_response(self, ret, data, headers={}):
        try:
            obj_crypto_handler = CryptoHandler()
            enc = obj_crypto_handler.encrypt(data.get("email")+"_##_"+data.get("password")+"##")
            token = uuid.uuid1()
            log = UserDA().create_encrypted_mobile_data(enc, token)
            res = {
                    "authToken": ret.get("token"),
                    "screenName": ret.get("user")["first_name"] + " " + ret.get("user")["last_name"],
                    "identityToken": token,
                }
            res.update(AccessBL().get_login_access(ret.get("user")["pk"]))
            return Response(res)
        except Exception as err:
            response = {}
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__logs.error(self.__exception.get_exception()))
            return Response(response)

    def format_login_error_response(self, ret):
        try:
            res = {"error": ""}
            data = ret.data
            if data.get("password"):
                res["error"]= data.get("password")[0]
            if data.get("non_field_errors"):
                res["error"]= data.get("non_field_errors")[0]
            return Response(res)
        except Exception as err:
            response = {}
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__logs.error(self.__exception.get_exception()))
            return Response(response)

    def format_verify_token_data(self, data):
        try:
            obj_crypto_handler = CryptoHandler()
            result = {}
            token = data.get("identityToken", None)
            if token:
                enc_data = UserDA().get_encrypted_mobile_date(token)

                if enc_data:
                    decrypted = obj_crypto_handler.decrypt(enc_data.encrypted_text)
                    result["email"] = decrypted.split("b'")[1].split("_##_")[0]
                    result["password"] = decrypted.split("b'")[1].split("_##_")[1]
            return result
        except Exception as err:
            response = {}
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__logs.error(self.__exception.get_exception()))
            return response

    def __clean_exclude_list(self, data):
        entries_to_remove = ["address_1", "address_2", "city_code", "provin_code",
        "district_code","zipcode","permanent_address_1","permanent_address_2",
        "permanent_city_code","permanent_coun_code","permanent_district_code",
        "permanent_zipcode","profile_photo","profile_photo","name","mobile_no",
        "relationship","id","reported_to","user_id"
         ]
        for k in entries_to_remove:
            data.pop(k, None)
        return data

    def __get_image_url(self, user_id):
        img_url = UserDA().get_user_profile_by_id(user_id)
        if img_url:
            return f"{settings.DEFAULT_SITE_MEDIA_URL}{img_url.profile_photo}"
        else:
            return None


    def format_employee_profile(self, result):
        if result.get("error"):
            result = {"error": result.get("error"), "status": result.get("status", 200)}
            return result

        result = result.get("emp_profile")
        if result:
            current_address = {}
            current_address["address_1"] = result.get('address_1')
            current_address["address_2"] = result.get('address_2')
            current_address["provin_code"] = result.get('provin_code')
            current_address["district"] =  settings.DISTRICTS[int(result.get('district_code'),0)]
            current_address["districtId"] =  result.get('district_code')
            current_address["city"] = result.get('city_code')
            current_address["zipcode"] = result.get('zipcode')
            current_address["state"] =  settings.STATES[int(result.get('provin_code'),0)]
            current_address["stateId"] =  result.get('provin_code')

            permanent_address = {}
            permanent_address["address_1"] = result.get('permanent_address_1')
            permanent_address["address_2"] = result.get('permanent_address_2')
            permanent_address["provin_code"] = result.get('permanent_provin_code')
            permanent_address["district"] =  settings.DISTRICTS[int(result.get('permanent_district_code'),0)]
            permanent_address["districtId"] =  result.get('permanent_district_code')
            permanent_address["city"] = result.get('permanent_city_code')
            permanent_address["zipcode"] = result.get('permanent_zipcode')
            permanent_address["state"] =  settings.STATES[int(result.get('permanent_provin_code'),0)]
            permanent_address["stateId"] =  result.get('permanent_provin_code')

            result["emp_image"] = self.__get_image_url(result.get("id"))
            emergency_contact = {}
            emergency_contact["contact_person"] = result.get("name")
            emergency_contact["relationship"] = result.get("relationship")
            emergency_contact["phone_number"] = result.get("mobile_no")

            result['emp_id'] = result.get('id')
            company_id= result.get('company_id')
            result['company_name'] = TenancyDA().get_company_name(company_id)

            job_title_id = result.get('job_title')
            job_title_obj = UserDA().get_job_title_by_id(job_title_id)
            result['job_title'] = job_title_obj.job_title
            result['job_title_id'] = job_title_id
            result['reporting_person'] = result.get("reported_to")
            result['job_status_id'] = result.get("job_status")
            result['job_status'] = UserDA().get_employment_status_name(result.get("job_status"))

            result["current_address"] = current_address
            result["permanent_address"] = permanent_address
            result["emergency_contact"] = emergency_contact
            result['status'] = 200

            result = self.__clean_exclude_list(result)
        else:
            result = {"error": "User profile does not exist. ", "status": 499}
        return result

    def get_team_members_v1(self, user_id):
        response = {"status": 200}
        try:
            res = []
            scope = data_scope(user_id, 'leave')
            if scope == SCOPE_ALL:
                team_members = UserDA().get_all_active_users()
            elif scope == SCOPE_TEAM:
                team_members = UserDA().get_current_team_members_by_lead_id(user_id)
            else:
                response['error'] = "Access Denied"
                response['status'] = 403
                return response

            if team_members:
                for each in team_members:
                    if each.id == user_id:
                        continue
                    temp = {}
                    temp["emp_id"] = each.id
                    temp["emp_name"] = each.first_name + ' ' + each.last_name
                    temp["emp_image"] = self.__get_image_url(each.id)
                    res.append(temp)
            response["team_members"] = res
            return response
        except Exception as err:
            response['status'] = 499
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__logs.error(self.__exception.get_exception()))
            return response

    def get_request_count(self, user_id, date=0):
        response = {}
        try:
            team_members_list = []
            leave_count = 0
            wfh_count = 0
            if data_scope(user_id, 'leave') == SCOPE_ALL:
                team_members = UserDA().get_all_active_users()
                team_members = team_members.exclude(id=user_id)
            else:
                team_members = UserDA().get_current_team_members_by_lead_id(user_id)
            if team_members:
                for each in team_members:
                    team_members_list.append(each.id)
                leave_requests = LeaveDA().get_leave_request_by_status_v1(1) # 1 for requests
                if leave_requests:
                    if date:
                        date = date
                    else:
                        date = datetime.today().date()
                    period = LeaveDA().get_employee_leave_period(user_id, date)
                    if period:
                        period_id = period.leave_period_id
                        leave_requests = leave_requests.filter(leave_period_id=period_id)
                        leave_count = leave_requests.filter(employee_id__in = team_members_list).count()
                    else:
                        leave_count = 0
                response["leave_requests"] = leave_count
                wfh_requests = AttendanceDA().get_all_wfh_requests_by_status(1)  # 1 for requests
                if wfh_requests:
                    # if date:
                        # wfh_requests = wfh_requests.filter(start_date=date)
                    wfh_count = wfh_requests.filter(emp_id__in = team_members_list).count()
                response["wfh_requests"] = wfh_count
            return response
        except Exception as err:
            response = {}
            response['status'] = 499
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__logs.error(self.__exception.get_exception()))
            return response

    def get_dashboard_anniversaries_v1(self, request):
        try:
            headers = self.save_commen_headers_by_user_id(request.user.id, request.META)

            attendace_data = {
                "is_checked_in": False,
                "working_hours": 0,
                "first_punch_in": "",
                "last_punch_out": "",
                "is_wfh": False
            }
            response = {
            "work_anniversaries": [],
            "holidays": [],
            "birthdays": [],
            "attendance": attendace_data,
            "emp_image":"",
            "status": 200
            }

            requsests = {"leave_requests": 0, "wfh_requests": 0}
            holiday_list = []
            company_id = get_active_company_id()
            anniversaries = AnniversaryBL().get_work_anniversaries(company_id)
            if anniversaries.get('error', None):
                response['error'] = anniversaries.get('error', None)
            response['work_anniversaries'] = anniversaries.get('anniversaries', [])
            holidays = AnniversaryBL().get_upcoming_holidays(company_id)
            if holidays.get('error', None):
                response['error'] = holidays.get('error', None)
            if holidays.get('holidays', []):
                holiday_list = holidays.get('holidays')
                for r,each in enumerate(holiday_list):
                    if each.get("date"):
                        new_date = datetime.strptime(each.get("date"), "%B %d, %Y").strftime("%Y-%m-%d")
                        holiday_list[r]["date"] = new_date
                    #holiday_list[r]["background_image"] = ""

            response['holidays'] = holiday_list
            birthdays = AnniversaryBL().get_employee_birthdays(company_id)
            if birthdays.get('error', None):
                response['error'] = birthdays.get('error', None)
            response['birthdays'] = birthdays.get('birthdays', [])
            response['requests'] = self.get_all_direct_reporting_leave_and_wfh_pending_request_count(request.user.id)
            response["attendance"] = self.__get_today_attendance_v2(request.user.id, attendace_data)
            response['emp_image'] = self.__get_image_url(request.user.id)
            return response
        except Exception as err:
            response = {}
            response['status'] = 499
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__logs.error(self.__exception.get_exception()))
            return response

    def __get_today_attendance_v2(self, user_id, attendance):
        """ Today's attendance from Attendance V2, in the dashboard's existing
        shape: times as '09:31 AM', working_hours in seconds. Left at the
        defaults when the active company has the attendance module disabled. """
        company_id = get_active_company_id()
        if company_id is None or is_catalog_module_disabled(company_id, 'attendance'):
            return attendance
        status = SelfCheckInBL().status(user_id)
        if status.get('error'):
            return attendance
        attendance['is_checked_in'] = status.get('suggested_punch_type') == PUNCH_OUT
        daily = status.get('daily') or {}
        attendance['working_hours'] = (daily.get('total_work_minutes') or 0) * 60
        attendance['first_punch_in'] = self.__format_punch_time(daily.get('first_in'))
        attendance['last_punch_out'] = self.__format_punch_time(daily.get('last_out'))
        attendance['is_wfh'] = OrgDA().has_approved_wfh(user_id, date.today())
        return attendance

    def __format_punch_time(self, value):
        if not value:
            return ""
        return datetime.strptime(value, '%Y-%m-%dT%H:%M:%S').strftime('%I:%M %p')

    def __get_image_url(self, user_id):
        try:
            img_url = UserDA().get_user_profile_by_id(user_id)
            if img_url:
                return f"{settings.DEFAULT_SITE_MEDIA_URL}{img_url.profile_photo}"
            else:
                return ""
        except:
            return ""



    def get_emp_code_by_emp_id(self, emp_id):
        emp = UserDA().get_user_by_emp_id(emp_id)
        return emp.username

    def get_application_data_v1(self, user_id, page=0):
        try:
            response = {
                "leave_type":[],
                "notify_list":[],
                "timesheet_activities": [],
                "projects": [],
                "job_titles": [],
                "job_status": []
            }
            leave_types = LeaveDA().get_all_leave_types(get_active_company_id())
            if leave_types:
                for each in leave_types:
                    temp = {}
                    temp["id"] = each.leave_type_id
                    temp["leave_type"] = each.leave_type_name
                    response["leave_type"].append(temp)
            supervisors, err = UserDA().get_all_supervisors_for_leave(
                users_with_capability('leave.approve'))
            # supervisors
            if supervisors:
                temp_list = []
                for supervisor in supervisors:
                    temp_list.append(
                        {"id": supervisor[0], "name": supervisor[1] + " " + supervisor[2]})
                response['notify_list'] = temp_list
            # projects
            project_list = []
            project_dict = {}

            active = get_active_company()
            projects = ProjectDA().get_all_projects_by_company(active.company_id) if active else None
            if projects:
                for project in projects:
                    project_dict[project.project_id] = project
            user_projects = ProjectDA().get_project_user_mapping(user_id)
            if user_projects:
                for user_project in user_projects:
                    project = project_dict.get(user_project.project_id, None)
                    if project:
                        project_list.append({
                            "id": project.project_id,
                            "name": project.name,
                            "is_billable": project.is_billable
                        })
                response['projects'] = project_list
            #time sheet activities
            activity_list = []
            activities = ProjectDA().get_all_project_activity(get_active_company_id())
            if activities:
                for activity in activities:
                    activity_list.append({"id": activity.activity_id, "name": activity.name})
                response['timesheet_activities'] = activity_list

            # job titles
            job_title_list = []
            job_titles = UserDA().get_all_job_titles(get_active_company_id())
            if job_titles:
                for job_title in job_titles:
                    job_title_list.append({"id": job_title.id, "title": job_title.job_title})
                response['job_titles'] = job_title_list

            #job statuses
            job_status_list = []
            for job_status in UserDA().get_employment_statuses(get_active_company_id()):
                job_status_list.append({"id": job_status.id, "status": job_status.name})
            response['job_status'] = job_status_list

            return response
        except Exception as err:
            response = {}
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__logs.error(self.__exception.get_exception()))
            return response



    def get_all_direct_reporting_leave_and_wfh_pending_request_count(self, user_id):
        """ Pending leave / WFH requests of the caller's direct reports (lead
        mapping) and pending profile changes, all within the active company. """
        company_employee_ids = self.__company_employee_ids()
        direct_reports = {member.id for member in UserDA().get_current_team_members_by_lead_id(user_id)}
        direct_reports = (direct_reports & company_employee_ids) - {user_id}
        result = {
            'leave_requests': self.__pending_leave_count(direct_reports),
            'wfh_requests': self.__pending_wfh_count(direct_reports),
            'profile_requests': 0,
        }
        if has_capability(user_id, 'employee.approve_profile_changes'):
            result['profile_requests'] = UserDA().count_employees_with_profile_changes(company_employee_ids)
        return result

    def __company_employee_ids(self):
        """ Active employees of the active company (none if it is unknown). """
        company_user_ids = UserDA().get_user_ids_by_company(get_active_company_id())
        return set(UserDA().get_all_active_users().filter(id__in=company_user_ids).values_list('id', flat=True))

    def __approval_team(self, user_id, module, company_employee_ids):
        """ Whose requests the caller oversees, by capability: <module>.view_all ->
        the whole company, <module>.view_team -> their own team, else nobody. """
        scope = data_scope(user_id, module)
        if scope == SCOPE_ALL:
            team = set(company_employee_ids)
        elif scope == SCOPE_TEAM:
            team = {member.id for member in UserDA().get_current_team_members_by_lead_id(user_id)}
            team &= company_employee_ids
        else:
            team = set()
        team.discard(user_id)
        return team

    def __pending_leave_count(self, employee_ids):
        period = LeaveDA().get_leave_period_by_date(datetime.today().date(), get_active_company_id())
        if not employee_ids or not period:
            return 0
        return LeaveDA().count_leave_requests(period.leave_period_id,
                                              settings.LEAVE_REQUEST_STATUS_V1['Requested'], employee_ids)

    def __pending_wfh_count(self, employee_ids):
        if not employee_ids:
            return 0
        return AttendanceDA().count_wfh_requests(settings.WFH_REQUEST_STATUS_V1['Requested'], employee_ids)

    def get_pending_leave_and_wfh_count(self, user_id):
        """ Pending-approval counts for the active company. team_* follow the
        caller's capabilities (leave.view_all/view_team, attendance.view_all/
        view_team); the rest are their direct reports and profile changes. """
        try:
            company_employee_ids = self.__company_employee_ids()
            response = {
                'team_leave_requests': self.__pending_leave_count(
                    self.__approval_team(user_id, 'leave', company_employee_ids)),
                'team_wfh_requests': self.__pending_wfh_count(
                    self.__approval_team(user_id, 'attendance', company_employee_ids)),
            }
            response.update(self.get_all_direct_reporting_leave_and_wfh_pending_request_count(user_id))
            return response
        except Exception as err:
            response = {}
            response['status'] = 499
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__logs.error(self.__exception.get_exception()))
            return response

    def save_employee_profile_image(self, user_id, request):
        result = {}
        edit_data_list = []
        try:
            image = request.FILES.get("image", None)
            emp_id = request.data['emp_id']

            employee = UserDA().get_user_by_id(emp_id)

            if employee is None:
                result["error"] = "User does not exist ."
                result['status'] = 499
                return result
            is_permitted = self.is_permmitted_to_edit(user_id, emp_id)
            if not is_permitted:
                result["error"] = settings.ERROR_MSG.get('access_denied')
                result['status'] = 403
                return result

            if image:
                is_image_valid = self.is_profile_image_valid(image)

                if is_image_valid:

                    if has_capability(user_id, 'employee.manage'):
                        profile_image_name = self.update_user_profile_image(image, employee.username)
                        user_profile_update_data = {}
                        user_profile_update_data['profile_photo'] = profile_image_name
                        UserDA().update_user_profile(employee.id, user_profile_update_data)
                        result['message'] = "Profile image uploaded successfully"

                    else:
                        pending_image_change = self.pending_profile_image_change(emp_id)

                        if pending_image_change:
                            self.delete_pending_profile_image(pending_image_change[0].value)
                            UserDA().delete_user_profile_provisional_entries(emp_id, "emp_image")

                        value = self.upload_profile_provisional_image(image, employee.username)
                        field = "emp_image"
                        user_profile_provisional_obj = UserDA().create_user_profile_provisional_object(user_id, emp_id, field, value)
                        edit_data_list.append(user_profile_provisional_obj)

                        UserDA().create_emp_profile_changes(edit_data_list)

                        result['message'] = "Profile image uploaded successfully"

                else:
                    result["error"] = "Invalid image ."
                    result['status'] = 499
                    return result
            else:
                result['error'] = "Image not found"
                result['status'] = 499
                return result


        except Exception as err:
            result['status'] = 499
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__logs.error(self.__exception.get_exception()))
        return result


    def is_permmitted_to_edit(self, user_id, emp_id):
        permitted = False
        if int(user_id) == int(emp_id):
            permitted = True
            return permitted
        if has_capability(user_id, 'employee.manage'):
            permitted = True
            return permitted
        return permitted

    def upload_profile_provisional_image(self, image, emp_code):

        try:
            if image.content_type == "image/jpeg":
                name = str(emp_code)+".jpeg"

            if image.content_type == "image/png":
                name = str(emp_code)+".png"

            if image.content_type == "image/jpg":
                name = str(emp_code)+".jpg"
            file_path = f"{settings.MEDIA_ROOT}confidential_docs/profile_image_provisional/{name}"
            self.__logs.debug(file_path)
            self.__file_manager.upload_file(file_path, image.read())

            return name
        except Exception as err:
            settings.ERROR_MSG['application_error']\
                .format(err, self.__logs.error(self.__exception.get_exception()))

    def is_profile_image_valid(self, image):
        is_valid = True

        allowed_image_types = ["image/jpeg", "image/png", "image/jpg"]
        width, height = get_image_dimensions(image)

        if image.content_type not in allowed_image_types:
            is_valid = False

        # if image.size > 10000000 or image.size <40000:
        #     is_valid = False

        return is_valid

    def pending_profile_image_change(self, emp_id):

        profile_image_change = UserDA().get_pending_profile_field_change(emp_id, "emp_image")
        return profile_image_change

    def delete_pending_profile_image(self, image):
        try:
            file_path = f'{settings.MEDIA_ROOT}confidential_docs/profile_image_provisional/{image}'
            self.__file_manager.delete_file(file_path)
        except:
            pass
    def __get_database_field_of_emergency_contact(self, field):
        if field == "contact_person":
            return "name"

        if field == "relationship":
            return "relationship"

        if field == "phone_number":
            return "mobile_no"

    def __get_database_field_of_user_profile(self, field, node):
        if node.upper() == "PERMANENT_ADDRESS":
            if field.upper() == "ADDRESS_1":
                return "permanent_address_1"
            if field.upper() == "ADDRESS_2":
                return "permanent_address_2"
            if field.upper() == "DISTRICTID":
                return "permanent_district_code"
            if field.upper() == "STATEID":
                return "permanent_provin_code"
            if field.upper() == "ZIPCODE":
                return "permanent_zipcode"
            if field.upper() == "CITY":
                return "permanent_city_code"

        if node.upper() == "CURRENT_ADDRESS":
            if field.upper() == "ADDRESS_1":
                return "address_1"
            if field.upper() == "ADDRESS_2":
                return "address_2"
            if field.upper() == "DISTRICTID":
                return "district_code"
            if field.upper() == "STATEID":
                return "provin_code"
            if field.upper() == "ZIPCODE":
                return "zipcode"
            if field.upper() == "CITY":
                return "city_code"


    def update_user_profile_changes(self, profile_changes):
        auth_user_update_data = {}
        user_profile_update_data = {}
        emergency_contact_update_data = {}

        emp_id = profile_changes.get("emp_id", None)

        for each_key in profile_changes.keys():


            if (each_key.upper() == "EMP_ID"):
                continue

            elif (each_key.upper() == "EMERGENCY_CONTACT"):
                emergency_contact = profile_changes.get(each_key, None)

                for edited_emergency_key in emergency_contact.keys():
                    field = self.__get_database_field_of_emergency_contact(edited_emergency_key)
                    if field:
                        emergency_contact_update_data[field] = emergency_contact.get(edited_emergency_key, None)
                        emergency_contact_update_data["emp_id"] = emp_id

            elif (each_key.upper() == "PERMANENT_ADDRESS"):
                permanent_address = profile_changes.get(each_key, None)

                for edited_permanent_address_key in permanent_address.keys():
                    field = self.__get_database_field_of_user_profile(edited_permanent_address_key,each_key)
                    if field:
                        user_profile_update_data[field] =  permanent_address.get(edited_permanent_address_key, None)


            elif (each_key.upper() == "CURRENT_ADDRESS"):
                current_address = profile_changes.get(each_key, None)

                for edited_current_address_key in current_address.keys():
                    field = self.__get_database_field_of_user_profile(edited_current_address_key,each_key)
                    if field:
                        user_profile_update_data[field] =  current_address.get(edited_current_address_key, None)

            elif each_key.upper() in ["FIRST_NAME", "LAST_NAME"]:
                auth_user_update_data[each_key] = profile_changes.get(each_key, None)

            else:
                field = self.get_user_profile_database_field(each_key)
                if field:
                    user_profile_update_data[field] = profile_changes.get(each_key, None)

        with transaction.atomic():
                    if auth_user_update_data:
                        UserDA().update_auth_user(auth_user_update_data, emp_id)
                    if user_profile_update_data:
                        UserDA().update_user_profile(emp_id, user_profile_update_data )
                    if emergency_contact_update_data:
                        UserDA().update_emergency_contact( emergency_contact_update_data ,emp_id)

    def get_user_profile_database_field(self, field):
        field_list = ["company_id", "gender", "dob", "job_status_id", "job_title_id",
                      "marital_status", "home_telephone", "mobile", "personal_email", "blood_group"]

        if field in field_list:
            if field == "job_status_id":
                return  "job_status"
            elif field == "job_title_id":
                return "job_title"
            else:
                return field

    def update_user_profile_image(self,image, emp_code):
        try:
            if image.content_type == "image/jpeg":
                name = str(emp_code)+".jpeg"

            if image.content_type == "image/png":
                name = str(emp_code)+".png"

            if image.content_type == "image/jpg":
                name = str(emp_code)+".jpg"
            
            file_path = f"{settings.MEDIA_ROOT}employee_profile_photo/{name}"
            self.__file_manager.upload_file(file_path, image.read())

            return name
        except Exception as err:
            settings.ERROR_MSG['application_error']\
                .format(err, self.__logs.error(self.__exception.get_exception()))






