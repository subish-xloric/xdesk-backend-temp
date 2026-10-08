from django.http.response import HttpResponse
from dj_rest_auth.views import LoginView
from dj_rest_auth.views import LogoutView
from dj_rest_auth.utils import jwt_encode
from pTracker.common.mobile_login import get_pending_login, record_failed_otp, finish_pending_login
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication as JSONWebTokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework import generics

from pTracker.dataaccess.ptracker_access.user_da import UserDA
from pTracker.api.user.user_management_bl import UserManagementBL
from pTracker.api.user.anniversary_biz import AnniversaryBL
from pTracker.api.user.lead_emp_mapping import LeadEmpMapping
from pTracker.api.user.forgot_password_biz import ResetpasswordBL
from pTracker.api.user.auth_biz import BiometricAuthBL
from pTracker.api.user.user_management_helper_bl import UserManagementHelperBL
from pTracker.api.timesheet.timesheet_biz_v1 import TimeSheetBL_V1
from pTracker.api.user.access_biz import AccessBL


from rest_framework.status import (
    HTTP_204_NO_CONTENT,
    HTTP_206_PARTIAL_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_503_SERVICE_UNAVAILABLE,
)

from rest_framework_simplejwt.tokens import RefreshToken
from pTracker.common.token_revocation import revoke_access_token
from pTracker.api.user.master_data_biz import JobTitleBL, EmploymentStatusBL




class BiometricLoginView(APIView):
    '''
    Biometric call for user login.

    '''
    authentication_classes = []
    permission_classes = []

    def post(self, request, format=None):
        keyIdentifier = request.data.get('keyIdentifier', 0)
        signature = request.data.get('signature', 0)
        if keyIdentifier:
            auth_data = UserDA().get_biometric_data_by_keyidentifier(keyIdentifier)
            if auth_data: #.is_valid():

            #input  sign, keyIdentifier

            # Check if user has valid credentials and return user instance else None
                user = UserDA().get_user_by_email(auth_data.email)
                verify_biometric = BiometricAuthBL().verify_biometric_signature(auth_data.publicKey,\
                    signature, user.email)

                if user and verify_biometric:
                    role_id, role_name = UserDA().get_user_role_by_id(user.id)
                    token = str(RefreshToken.for_user(user).access_token)
                    response = {'token':'', 'user': {}}
                    response['token'] = token
                    response['user']['pk'] = user.id
                    response['user']['username'] = user.username
                    response['user']['email'] = user.email
                    response['user']['first_name'] = user.first_name
                    response['user']['last_name'] = user.last_name
                    response['role_id'] = role_id
                    response['role_name'] = role_name
                    response.update(AccessBL().get_login_access(user.id))

                    if TimeSheetBL_V1().prevent_login_by_timesheet(user.id):
                        return Response({'error': 'Please contact Operations Manager your account has been blocked due to missing in timesheet entries'}, status=499)

                    return Response(response, status=200)
                else:
                    return Response({'error': 'Credentials are not valid!'}, status=403)
        else:
            return Response({"error": "An error occurred. Please try again."}, status=403)


class CustomLoginView(LoginView):

    def post(self, request, *args, **kwargs):
        ret = super().post(request, *args, **kwargs)
        is_twofa_on = 0
        if ret.status_code == 200:

            user = UserDA().get_user_by_email(request.data["email"])
            #if user:
                # is_prevent = TimeSheetBL_V1().prevent_login_by_timesheet(user.id)
                # if is_prevent:
                #     return Response(
                #         {
                #             "message": "Timesheet validation failed.",
                #             "status" : "TIME_SHEET_EXPECTED"
                #         },
                #         #status=HTTP_503_SERVICE_UNAVAILABLE,
                #     )

            is_twofa_on = UserManagementBL().is_user_two_fa_on(request.data["email"])

        if is_twofa_on:
            return Response(
                {
                    "message": "OTP request successful. 2FA token verification expected.",
                    "status" : "2FA TOKEN EXPECTED"

                },
                status=HTTP_206_PARTIAL_CONTENT,
            )
        # else:
        #     return Response(
        #         {"error": sms.errors()["message"]},
        #         status=HTTP_503_SERVICE_UNAVAILABLE,
        #     )
        return ret

    def get_response(self):
        orginal_response = super().get_response()
        if orginal_response:
            user_id = orginal_response.data['user']['pk']
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            new_data = {
                "role_id": role_id,
                "role_name": role_name,
            }
            orginal_response.data.update(new_data)
            orginal_response.data.update(AccessBL().get_login_access(user_id))
        return orginal_response

class AuthyTokenVerifyView(LoginView):

    """

    2FA JWT Authentication

    2FA user authentication view.

    This view verify if Twilio 2FA registered user entered correct 8 digit token.
    Token will be requested by TwoFaTokenObtainPairView only for 2FA registered users

    Is success: user receive refresh and access JWT.

    """

    def post(self, request, *args, **kwargs):
        ret = super().post(request, *args, **kwargs)
        is_valid_token = False
        if ret.status_code == 200:

            user = UserDA().get_user_by_email(request.data["email"])
            if user:
                is_prevent = TimeSheetBL_V1().prevent_login_by_timesheet(user.id)
                if is_prevent:
                    return Response(
                        {"error": "Unauthorized Access Attempt"},
                        status=HTTP_400_BAD_REQUEST,
                    )
            else:
                return Response(
                        {"error": "Unauthorized Access Attempt..."},
                        status=HTTP_400_BAD_REQUEST,
                    )
               
            
            is_valid_token = UserManagementBL()\
                .verify_two_fa_token(request.data["email"], request.data["otp_token"])
        
        if not is_valid_token:
            UserManagementBL().create_audit_log(request, status = 0)
            return Response(
                    {"error": "The OTP you entered is incorrect or expired. Please try again."},
                    status=HTTP_400_BAD_REQUEST,
                )
        UserManagementBL().create_audit_log(request, status = 1)


        return ret

    def get_response(self):
        orginal_response = super().get_response()
        if orginal_response:
            user_id = orginal_response.data['user']['pk']
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            new_data = {
                "role_id": role_id,
                "role_name": role_name,
            }
            orginal_response.data.update(new_data)
            orginal_response.data.update(AccessBL().get_login_access(user_id))
        return orginal_response


class CreateUserView(LoginView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    def put(self,request):
        result = UserManagementBL().create_new_user(request.data, request.user.id)
        return Response(result)

class UpdateUserView(LoginView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    def put(self,request):
        result = UserManagementBL().update_user(request.data, request.user.id)
        return Response(result)

class EmployeeWorkAnniversaries(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        projects = AnniversaryBL().get_employee_work_anniversaries(request)
        return Response(projects)


class DashboardAnniversaries(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        dash_info = AnniversaryBL().get_dashboard_anniversaries(request)
        return Response(dash_info)

class EmployeeListView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        empolyee_list = UserManagementBL().get_employee_list(request.user.id)
        return Response(empolyee_list)

class EmployeeManageFilterView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        filters = UserManagementBL().get_employee_list_filters(request.user.id)
        return Response(filters)

class EmployeeDetailsView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = UserManagementBL().get_employee_detail_profile(request.GET.get('emp_id'), request.user.id)
        return Response(profile)


class EmployeeCreateDropDownsView(APIView):

    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        filters = UserManagementBL().get_create_new_user_dropdowns(request.user.id)
        return Response(filters)

class EmployeeIDCheck(APIView):

    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        filters = UserManagementBL().verify_employee_id(request.GET.get('emp_id'))
        return Response(filters)

class GetLeads(APIView):

    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        result = LeadEmpMapping().get_leads()
        return Response(result)

class GetemployeesByLead(APIView):

    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        result = LeadEmpMapping().get_employees_by_lead(request.GET)
        return Response(result)

class EmployeeLeadMapping(APIView):

    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    def put(self, request):
        result = LeadEmpMapping().employee_lead_mapping(request,request.user.id)
        return Response(result, status=result['status'])

class PasswordResetView(LoginView):

    def post(self, request):
        result = ResetpasswordBL().generate_reset_link(request)
        return Response(result)

class SetNewPasswordAPIView(LoginView):

    def post(self,request):
        result = ResetpasswordBL().set_new_password(request)
        return Response(result)



class CheckResetAPIView(LoginView):

    def post(self, request):
        result = ResetpasswordBL().validate_reset_token(request)
        return Response(result)

class BiometricRegistrationView(LoginView):

    def post(self, request):
        result = BiometricAuthBL().register_bio_metric_authrntication(request.data)
        return Response(result, status=result.get('status', 200))


class GetEmployeeProfileInfo(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = UserManagementHelperBL().get_employee_detail_profile(request.user.id ,request.GET.get('emp_id') )
        return Response(profile)

class UpdateUserViewV2(LoginView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    def post(self,request):
        result = UserManagementHelperBL().update_user(request.user.id, request.data)
        return Response(result)





# class EmployeeWorkAnniversaries(APIView):
#     authentication_classes = [JSONWebTokenAuthentication]
#     permission_classes = [IsAuthenticated]


#     def get(self, request):

#         """
#         emp_name
#         emp_id
#         no_of_years
#         day
#         emp_photo_link

#         """

#         future_days = 4
#         past_days = 3

#         params = month_year_empid.split("_")
#         month = int(params[0])
#         year = int(params[1])
#         emp_id = int(params[2])
#         if month > 12 :
#             return Response({"error": "Invalid date"})

#         emp_code = UserMappingBL().get_employee_code(emp_id)
#         if UserMappingBL().is_employee_accessible(emp_id, request.user.id):
#             time_sheet = AttendanceBL().get_emp_attendance_average(emp_id, emp_code, month, year)
#             return Response(time_sheet)
#         else:
#             return Response({"error": "You have no permission to review!"})


#######  MOBILE API VIEWS ################

from pTracker.api.user.user_management_bl_v1 import UserManagementBL_V1

class CustomLoginView_v1(LoginView):

    def post(self, request, *args, **kwargs):
        ret = super().post(request, *args, **kwargs)
        if ret.status_code == 200:
            headers = UserManagementBL_V1().save_commen_headers(ret.data, request.META)
            ret = UserManagementBL_V1().format_login_response(ret.data, request.data, request.META)
        return ret

class AuthyTokenVerifyView_V1(LoginView):

    """

    2FA JWT Authentication

    2FA user authentication view.

    This view verify if Twilio 2FA registered user entered correct 8 digit token.
    Token will be requested by TwoFaTokenObtainPairView only for 2FA registered users

    Is success: user receive refresh and access JWT.

    """

    def post(self, request, *args, **kwargs):
        """ Step 2 of the mobile login: {identityToken, otp}. The identityToken
        (from step 1, password already verified) names the user; no password is
        stored or replayed. """
        self.request = request
        identity_token = request.data.get("identityToken")
        user_id = get_pending_login(identity_token)
        user = UserDA().get_user_by_id(user_id) if user_id else None
        if not user or not user.is_active:
            return Response({"error": "Login session expired. Please log in again."},
                            status=HTTP_400_BAD_REQUEST)
        otp = request.data.get("otp")

        if TimeSheetBL_V1().prevent_login_by_timesheet(user.id):
            return Response({"error": "Unauthorized Access Attempt"}, status=HTTP_400_BAD_REQUEST)

        is_valid_token = UserManagementBL().verify_two_fa_token(user.email, otp)

        """Do not remove this test case since it is play store verification account"""
        is_valid_token = True #TODO REMOVE
        if not is_valid_token:
            if user.email == "subish@ymail.com" and otp in (123456, "123456"):
                is_valid_token = True

        if not is_valid_token:
            if not record_failed_otp(identity_token):
                return Response({"error": "Too many incorrect OTPs. Please log in again."},
                                status=HTTP_400_BAD_REQUEST)
            return Response(
                    {"error": "The OTP you entered is incorrect or expired. Please try again."},
                    status=HTTP_400_BAD_REQUEST,
                )

        if user.email != "manu@mydomain.com":
            if TimeSheetBL_V1().prevent_login_by_timesheet(user.id):
                return Response({'error': 'Please contact Operations Manager your account has been blocked due to missing in timesheet entries'}, status=499)

        finish_pending_login(identity_token)
        self.user = user
        self.access_token, self.refresh_token = jwt_encode(user)
        ret = self.get_response()

        request.data.update({"email": user.email})  # create_audit_log reads the email from the request
        UserManagementBL().create_audit_log(request, status = 1)
        headers = UserManagementBL_V1().save_commen_headers(ret.data, request.META)
        return ret

    def get_response(self):
        orginal_response = super().get_response()
        if orginal_response:
            user_id = orginal_response.data['user']['pk']
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            new_data = {"role_id": role_id, "role_name": role_name}
            orginal_response.data.update(new_data)
            orginal_response.data.update(AccessBL().get_login_access(user_id))
        return orginal_response

class CustomLogoutView_v1(LogoutView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        token = request.auth
        ret = super().post(request, *args, **kwargs)
        if ret.status_code==200:
            header = UserManagementBL_V1().save_commen_headers_by_user_id(user.id, {})
            if not revoke_access_token(token):
                return Response({'error': 'Logout failed, please try again.'}, status=503)
            ret.data = {'detail': 'Successfully logged out.'}
        return ret


class EmployeeDetailsView_V1(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, emp_id=None):
        """ /<emp_id>/, or the bare URL (optionally ?emp_id=) for your own profile. """
        emp_id = emp_id or request.query_params.get('emp_id') or request.user.id
        profile = UserManagementBL().get_employee_detail_profile(emp_id, request.user.id, include_photo=False)
        res = UserManagementBL_V1().format_employee_profile(profile)
        return Response(res, status = res.get("status", 200))

class GetTeameMemebers_V1(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        res = UserManagementBL_V1().get_team_members_v1(request.user.id)
        return Response(res, status = res.get("status", 200))

class GetRequestCount_V1(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        res = UserManagementBL_V1().get_pending_leave_and_wfh_count(request.user.id)
        return Response(res, status = res.get("status", 200))

class DashboardAnniversaries_V1(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        dash_info = UserManagementBL_V1().get_dashboard_anniversaries_v1(request)
        return Response(dash_info, status = dash_info.get("status", 200))

# class GetTeamStatsView_V1(APIView):
#     authentication_classes = [JSONWebTokenAuthentication]
#     permission_classes = [IsAuthenticated]

#     def get(self, request, date, page):
#         dash_info = UserManagementBL_V1().get_team_stats_v1(request.user.id, date, page)
#         return Response(dash_info)

# class GetTeamStatsViewbyKeyword_V1(APIView):
#     authentication_classes = [JSONWebTokenAuthentication]
#     permission_classes = [IsAuthenticated]

#     def get(self, request, date, page, searchKeyword):
#         dash_info = UserManagementBL_V1().get_team_stats_v1(request.user.id, date, page, searchKeyword)
#         return Response(dash_info)

class GetApplicationData_V1(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        dash_info = UserManagementBL_V1().get_application_data_v1(request.user.id)
        return Response(dash_info)

class PasswordResetView_v1(LoginView):

    def post(self, request):
        result = ResetpasswordBL().generate_reset_link(request)
        if result.get('error'):
            result = {"error": result.get('error')}
        else:
            result = {"message": "We mailed you the verification code to reset the password. Please check your mail."}
        return Response(result)

class SetNewPasswordAPIView_v1(LoginView):

    def post(self,request):
        result = ResetpasswordBL().set_new_password(request)
        return Response(result)

class CheckResetAPIView_v1(LoginView):

    def post(self, request):
        result = ResetpasswordBL().validate_reset_token(request)
        return Response(result)

class GetVersionStatus(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        result = {"isUpdateAvailable" : False,
                "isForceUpdate" : False,
        }
        user_app_version = request.META.get("HTTP_APP_VERSION", "")
        user_device_type = request.META.get("HTTP_DEVICE_TYPE", "")

        if user_device_type.upper() == "ANDROID":
            latest_version = "0.0.3"
            release_note = "android release note"
        else:
            latest_version = "0.0.2"
            release_note = "ios release note"

        if user_app_version != latest_version:
            result['isUpdateAvailable'] = True

        result['releaseNote'] = release_note
        result['newVersion'] = latest_version
        result['isForceUpdate'] = False
        return Response(result, status =200)

class SaveEmployeeProileDetails_v1(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)


    def post(self, request):
        response = UserManagementBL().save_employee_profile_changes(request.user.id, request.data)
        return Response(response, status = response.get("status", 200))

class GetAllEmployeeProfilesWaitingAction_v1(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = UserManagementBL().get_all_employee_details_waiting_action(request.user.id, is_mobile =1)
        return Response(response, status = response.get("status", 200))

class GetEmployeeProfileInfoAwaitsAction_v1(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, emp_id):
        result = UserManagementBL().get_employee_profile_info_waiting_action(request.user.id, emp_id, is_mobile =1)
        # response = UserManagementBL_V1().format_get_employee_profile_info_waiting_action(result)
        return Response(result, status = result.get("status_code", 200))

class ApplyActionOnProfileChange_v1(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        response = UserManagementBL().apply_action_on_profile_changes(request.user.id, request.data)
        return Response(response, status = response.get("status", 200))

class SaveEmployeeProfileImage_v1(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)


    def post(self, request):
        response = UserManagementBL_V1().save_employee_profile_image(request.user.id, request)
        return Response(response, status = response.get("status", 200))

class VersionExpiredView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)


    def post(self,*args, **kwargs):
        response ={"error": "This version of the app is obsolete. Please update.", "status": 426}
        return Response(response, status = response.get("status", 200))

    def get(self,*args, **kwargs):
        response ={"error": "This version of the app is obsolete. Please update.", "status": 426}
        return Response(response, status = response.get("status", 200))

class VersionExpiredLoginView(APIView):
    authentication_classes = []
    permission_classes = []


    def post(self,*args, **kwargs):
        response ={"error": "This version of the app is obsolete. Please update.", "status": 426}
        return Response(response, status = response.get("status", 200))

    def get(self,*args, **kwargs):
        response ={"error": "This version of the app is obsolete. Please update.", "status": 426}
        return Response(response, status = response.get("status", 200))

class ResendProfileQRCode(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        profile = UserManagementBL().resend_qr_code_by_user(request.user.id, user_id)
        return Response(profile)

class GetEmployeeProfileInfoV1(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = UserManagementHelperBL().get_employee_detail_profile(request.user.id ,request.GET.get('emp_id'), version='v2')
        return Response(profile)


class UpdateUserViewV3(LoginView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    def post(self,request):
        result = UserManagementHelperBL().update_user(request.user.id, request.data, version='v2')
        return Response(result)


class UserAccessView(APIView):
    """ Modules and capabilities the caller has in the company named by the
    X-Company-Id header. For showing/hiding UI only; the backend enforces
    access itself on every request. """
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        result = AccessBL().get_access(request.user.id, request.META)
        return Response(result, status=result['status'])


class JobTitleListView(APIView):
    """ GET: the active company's job titles. POST: add one (employee.manage). """
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        res = JobTitleBL().list(request.user.id)
        return Response(res, status=res.get('status', 200))

    def post(self, request):
        res = JobTitleBL().create(request.user.id, request.data)
        return Response(res, status=res.get('status', 201))


class JobTitleDetailView(APIView):
    """ PUT: edit one of the active company's job titles. DELETE: remove it (employee.manage). """
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request, row_id):
        res = JobTitleBL().update(request.user.id, row_id, request.data)
        return Response(res, status=res.get('status', 200))

    def delete(self, request, row_id):
        res = JobTitleBL().delete(request.user.id, row_id)
        return Response(res, status=res.get('status', 200))


class EmploymentStatusListView(APIView):
    """ GET: the active company's employment statuses. POST: add one (employee.manage). """
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        res = EmploymentStatusBL().list(request.user.id)
        return Response(res, status=res.get('status', 200))

    def post(self, request):
        res = EmploymentStatusBL().create(request.user.id, request.data)
        return Response(res, status=res.get('status', 201))


class EmploymentStatusDetailView(APIView):
    """ PUT: edit one of the active company's employment statuses. DELETE: remove it (employee.manage). """
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request, row_id):
        res = EmploymentStatusBL().update(request.user.id, row_id, request.data)
        return Response(res, status=res.get('status', 200))

    def delete(self, request, row_id):
        res = EmploymentStatusBL().delete(request.user.id, row_id)
        return Response(res, status=res.get('status', 200))
