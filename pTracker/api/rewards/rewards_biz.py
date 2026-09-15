import re
import os
import json

from datetime import datetime, date, timedelta
from types import SimpleNamespace

from django.conf import Settings, settings
from django.db import  DatabaseError, transaction
from django.http import response, HttpResponse
from django.template import loader
from django.db.models import Q

# from asgiref.sync import async_to_sync
# from channels.layers import get_channel_layer

from pTracker.common.logs import Logs
from pTracker.common.utility import Utility
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.common.file_manager import FileManager
from pTracker.dataaccess.ptracker_access.user_da import UserDA
from pTracker.dataaccess.ptracker_access.rewards_da import RewardsDA

from pTracker.cronjobs.email_sender import send_email_notification


def new_dto():
    dto = SimpleNamespace()
    return dto


class RewardsBL():
    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()
        self.__utility = Utility()
        self.__file_manager = FileManager()

    def find_reward_approvers(self, emp_id, reward_type_id, role_id):
        result = []
        if int(reward_type_id)==1:#wow card
            result = [int(settings.HR_DEPT['res_emp_id']), int(settings.OPERATIONS_DEPT['res_emp_id'])]
        elif int(reward_type_id)==2:
            # if role_id == 4:
            #     result.append(emp_id)
            # else:
            lead_id = UserDA().get_lead_id_by_user(emp_id)
            if lead_id:
                result.append(lead_id)
        return result

    def __is_valid_reward_type(self, reward_type_id):
        status = False
        reward_type = RewardsDA().get_reward_type_by_id(reward_type_id)
        if reward_type:
            status = True
        return status

    def __is_active_user(self, user_id):
        status = False
        user = UserDA().get_user_by_id(user_id)
        if user:
            if user.is_active:
                status = True
        return status

    def __is_valid_string(self, string):
        status = True
        '''check the string contains only whitespace.'''
        if re.match(r'^\s*$', string):
            status = False
        '''Check if the string contains only special characters'''
        if re.match(r'^[^\w\s]*$', string):
            status = False

        if len(string) == 0:
            status = False
        return status

    def __is_allowed_to_comment_reward(self, user_id, reward_id):
        status = False
        reward_approvers = RewardsDA().get_reward_approvers(reward_id)
        if user_id in reward_approvers.values_list('approver_id', flat=True):
            status = True
            return status

        reward_obj = RewardsDA().get_reward_by_id(reward_id)
        if user_id == reward_obj.nominated_by:
            status = True
            return status
        return status

    def __is_allowed_to_approve_reward(self, user_id, reward_id):
        status = False
        reward_approvers = RewardsDA().get_reward_approvers(reward_id)
        if user_id in reward_approvers.values_list('approver_id', flat=True):
            status = True
        return status

    def __is_allowed_to_cancel(self, user_id, reward_id):
        status = False
        reward_obj = RewardsDA().get_reward_by_id(reward_id)
        if user_id == reward_obj.nominated_by:
            status = True
        return status

    def __is_allowed_to_view_reward(self, user_id, reward_obj):
        status = False
        try:
            #rewarder = reward_obj.receiving_emp_id
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            if user_id==reward_obj.nominated_by:
                status = True
            elif role_id in (1, 2, 3):
                status = True
            elif role_id==4:
                team_member = UserDA().get_current_team_members_by_lead_id(user_id)
                team_member_ids = [x.id for x in team_member]
                if reward_obj.nominated_by in team_member_ids:
                    status = True

            # elif rewarder==user_id:
            #     status = True

        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return status

    def __is_allowed_to_view_report(self, user_id):
        status = False
        try:
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            if role_id in (1, 2, 3):
                status = True

        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return status

    def __is_allowed_to_update_reward(self, reward_id, user_id):
        status = False
        try:
            reward_approvers = RewardsDA().get_reward_approvers(reward_id)
            reward_obj = RewardsDA().get_reward_by_id(reward_id)

            if user_id in reward_approvers.values_list('approver_id', flat=True):
                status = True
            elif user_id == reward_obj.nominated_by:
                status = True

        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return status


    def __generate_email_template(self, email_template, context):
        html_email = loader.render_to_string(email_template, context)
        return html_email

    def create_reward_nomination(self, request, user_id):
        response = {"error": '', "message": "", "status": 200, 'success': False}
        try:
            data = request.data
            reward_type_id = int(data.get("selectRewardType"))
            receiving_emp_id = int(data.get("selectEmployee"))
            nominated_by = user_id
            title = data.get("title")
            short_description = data.get("shortDescription")
            justification_description = data.get("justificationDescription")

            role_id, roleName = UserDA().get_user_role_by_id(user_id)

            if role_id in (1, 2, 3):
                return self.create_reward_nomination_v1(request, user_id)

            if not self.__is_valid_reward_type(reward_type_id):
                response["error"] = 'Invalid Nomination Type.'
                response["status"] = 499
                return response

            if reward_type_id == 1 and role_id > 4: #WOW Card
                response["error"] = 'You do not have permission to submit a nomination for Wow Card.'
                response["status"] = 499
                return response

            if not self.__is_active_user(receiving_emp_id):
                response["error"] = 'You have entered an invalid employee.'
                response["status"] = 499
                return response

            if not self.__is_valid_string(title):
                response["error"] = 'You have entered an invalid title.'
                response["status"] = 499
                return response

            if not self.__is_valid_string(short_description):
                response["error"] = 'Invalid TV Text.'
                response["status"] = 499
                return response

            if not self.__is_valid_string(justification_description):
                response["error"] = 'Invalid Justification.'
                response["status"] = 499
                return response

            criterias = json.loads(data.get('criterias', None))
            if not criterias:
                response["error"] = 'The reward criteria should not be empty under any circumstances.'
                response["status"] = 499
                return response

            approvers_list = self.find_reward_approvers(nominated_by, reward_type_id, role_id)
            if not approvers_list:
                response["error"] = "Unable to proceed since we haven't been able to find an approver for this reward."
                response["status"] = 499
                return response

            reward_dict = {}
            reward_dict['reward_type'] = RewardsDA().get_reward_type_by_id(reward_type_id)
            reward_dict['receiving_emp_id'] = receiving_emp_id
            reward_dict['nominated_by'] = nominated_by
            reward_dict['title'] = title
            reward_dict['short_description'] = short_description
            reward_dict['justification_description'] = justification_description
            reward_dict['published_date'] = None

            with transaction.atomic():
                approvers_name = ''
                cc_addresses = []
                res = RewardsDA().create_reward(reward_dict)
                if res:
                    for each_criteria in criterias:
                        cr_dict = {}
                        cr_dict['reward'] = res
                        cr_dict['criteria_id'] = each_criteria.get('id')
                        RewardsDA().create_reward_criterias(cr_dict)

                    for approver in approvers_list:
                        approver_user = UserDA().get_user_by_id(approver)
                        reward_approver_dict = {}
                        reward_approver_dict['reward_id'] = res.id
                        reward_approver_dict['approver_id'] = approver
                        reward_approver_dict['is_approved'] = 0
                        RewardsDA().create_reward_approver(reward_approver_dict)
                        approvers_name+=approver_user.first_name+' '+approver_user.last_name+', '
                        cc_addresses.append(approver_user.email)

                    user_name = request.user.first_name+' '+request.user.last_name
                    employee = UserDA().get_user_by_id(res.receiving_emp_id)
                    try:
                        user_profile = UserDA().get_user_profile_by_id(user_id)
                        designation = UserDA().get_job_title_by_id(user_profile.job_title).job_title
                    except:
                        designation = ''
                    template_name = 'reward_nominated.html'
                    emp_name = employee.first_name+' '+employee.last_name

                    subject =  f"{res.reward_type.name} Nomination for {emp_name}"
                    mail_context = {}
                    mail_context['heading'] = subject
                    mail_context['type'] = res.reward_type.name
                    mail_context['emp_name'] = emp_name
                    mail_context['managers'] = approvers_name
                    mail_context['title'] = res.title
                    mail_context['short_desc'] = res.short_description
                    mail_context['long_desc'] = res.justification_description
                    mail_context['name'] = user_name
                    mail_context['designantion'] = designation
                    mail_context['contact_info'] = request.user.email
                    email_content = self.__generate_email_template(template_name, mail_context)

                    bcc_address = [request.user.email]
                    if len(cc_addresses) == 1:
                        to_email = cc_addresses[0]
                        cc_addresses = []
                    else:
                        to_email = settings.CONSTANT_EMAIL['reward_email']

                    self.send_reward_email(subject, email_content, to_email,\
                         cc_addresses=cc_addresses, bcc_address=bcc_address)

                    response["status"] = 200
                    response["success"] = True
                    response['message'] = "Nomination Created Successfully ."

        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(str(err), self.__log.error(self.__exception.get_exception()))
            response["status"] = 499
        return response


    def create_reward_nomination_v1(self, request, user_id):
        # v1 created for role 1,2, 3
        response = {"error": '', "message": "", "status": 200, 'success': False}
        try:
            data = request.data
            reward_type_id = int(data.get("selectRewardType"))
            receiving_emp_id = int(data.get("selectEmployee"))
            nominated_by = user_id
            title = data.get("title")
            short_description = data.get("shortDescription")
            justification_description = data.get("justificationDescription")

            role_id, roleName = UserDA().get_user_role_by_id(user_id)

            if not self.__is_valid_reward_type(reward_type_id):
                response["error"] = 'Invalid Nomination Type.'
                response["status"] = 499
                return response

            if reward_type_id == 1 and role_id > 4: #WOW Card
                response["error"] = 'You do not have permission to submit a nomination for Wow Card.'
                response["status"] = 499
                return response

            if not self.__is_active_user(receiving_emp_id):
                response["error"] = 'You have entered an invalid employee.'
                response["status"] = 499
                return response

            if not self.__is_valid_string(title):
                response["error"] = 'You have entered an Invalid Title.'
                response["status"] = 499
                return response

            if not self.__is_valid_string(short_description):
                response["error"] = 'Invalid Short Description.'
                response["status"] = 499
                return response

            if not self.__is_valid_string(justification_description):
                response["error"] = 'Invalid Justification Description.'
                response["status"] = 499
                return response

            criterias = json.loads(data.get('criterias', None))
            if not criterias:
                response["error"] = 'The reward criteria should not be empty under any circumstances.'
                response["status"] = 499
                return response

            approvers_list = [user_id]
            if not approvers_list:
                response["error"] = "Unable to proceed since we haven't been able to find an approver for this reward."
                response["status"] = 499
                return response

            reward_dict = {}
            reward_dict['reward_type'] = RewardsDA().get_reward_type_by_id(reward_type_id)
            reward_dict['receiving_emp_id'] = receiving_emp_id
            reward_dict['nominated_by'] = nominated_by
            reward_dict['title'] = title
            reward_dict['short_description'] = short_description
            reward_dict['justification_description'] = justification_description
            reward_dict['published_date'] = datetime.now()
            reward_dict['status'] = 3
            reward_dict['published_date'] = datetime.now()

            with transaction.atomic():
                if reward_type_id==1:
                    type = 'Wow'
                else:
                    type = 'GaS'
                approvers_name = ''
                cc_addresses = []
                bcc_address = [request.user.email]
                res = RewardsDA().create_reward(reward_dict)
                if res:
                    for each_criteria in criterias:
                        cr_dict = {}
                        cr_dict['reward'] = res
                        cr_dict['criteria_id'] = each_criteria.get('id')
                        RewardsDA().create_reward_criterias(cr_dict)

                    for approver in approvers_list:
                        approver_user = UserDA().get_user_by_id(approver)
                        reward_approver_dict = {}
                        reward_approver_dict['reward_id'] = res.id
                        reward_approver_dict['approver_id'] = approver
                        reward_approver_dict['is_approved'] = 1
                        reward_approver_dict['approval_date'] = datetime.now()
                        RewardsDA().create_reward_approver(reward_approver_dict)
                        approvers_name+=approver_user.first_name+' '+approver_user.last_name+', '
                        cc_addresses.append(approver_user.email)

                    self.send_reward_congrats_email(res.id, request.user)
                    self.create_tv_notification(type, rewarded_by=res.nominated_by,title=title,\
                        long_desc=justification_description, short_desc=short_description, emp_id=res.receiving_emp_id)

                    response["status"] = 200
                    response["success"] = True
                    response['message'] = "Nomination created successfully."

        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(str(err), self.__log.error(self.__exception.get_exception()))
            response["status"] = 499
        return response

    def send_reward_approval_email(self,request, approvers, reward_obj, user_id):
        cc_addresses = []
        for approver in approvers:
            approver_user = UserDA().get_user_by_id(approver.approver_id)
            # approvers_name+=approver_user.first_name+' '+approver_user.last_name+', '
            cc_addresses.append(approver_user.email)
        user_name = request.user.first_name+' '+request.user.last_name
        nominator = UserDA().get_user_by_id(reward_obj.nominated_by)
        employee = UserDA().get_user_by_id(reward_obj.receiving_emp_id)

        emp_name = employee.first_name+' '+employee.last_name
        template_name = 'reward_approved.html'
        subject = f"{reward_obj.reward_type.name} Nomination for {emp_name} Approved"
        mail_context = {}
        mail_context['heading'] = subject
        mail_context['type'] = reward_obj.reward_type.name
        mail_context['approver'] = nominator.first_name+' '+nominator.last_name+', '
        mail_context['emp_name'] = emp_name
        mail_context['hr_name'] = user_name
        mail_context['hr_position'] = self.__utility.get_designation_of_employee(user_id)
        mail_context['hr_contact_info'] = request.user.email
        email_content = self.__generate_email_template(template_name, mail_context)

        self.send_reward_email(subject, email_content, nominator.email, cc_addresses=cc_addresses)



    def approve_reward_status(self, request):
        response = {"error": '', "success": False, "status": 200}
        try:
            user_id = request.user.id
            data = request.data
            reward_id = int(data.get("reward_id"))

            reward_obj = RewardsDA().get_reward_by_id(reward_id)
            if not reward_obj:
                response["error"] = "Nomination does not exist."
                response["status"] = 499
                return response

            if not self.__is_allowed_to_approve_reward(user_id,reward_id):
                response['error'] = settings.ERROR_MSG['no_permission']
                response['status'] = 403
                return response

            reward_dict = {}
            reward_dict['status'] = 2

            if reward_obj.reward_type.id == 2:
                reward_dict['status'] = 3
                reward_dict['published_date'] = datetime.now()

            with transaction.atomic():
                is_success = False
                res = RewardsDA().update_reward(reward_id, reward_dict)
                reward_approver_dict = {}
                reward_approver_dict['is_approved'] = 1
                reward_approver_dict['approval_date'] = datetime.now()
                approvers = RewardsDA().get_reward_approvers(reward_id)
                if res and reward_obj.reward_type.id==2:#GaS
                    type = 'GaS'
                    is_success = RewardsDA().update_reward_approver(user_id, reward_id, reward_approver_dict)
                    if is_success:
                        self.send_reward_approval_email(request, approvers, reward_obj, user_id )
                        self.send_reward_congrats_email(reward_id, request.user)
                        self.__create_tv_notification(type, reward_obj)
                elif res and reward_obj.reward_type.id==1:
                    type = 'Wow'
                    is_success = RewardsDA().update_reward_approver(user_id, reward_id, reward_approver_dict)
                    if not approvers.filter(is_approved=0).exists():
                        reward_dict['status'] = 3
                        reward_dict['published_date'] = datetime.now()
                        res = RewardsDA().update_reward(reward_id, reward_dict)
                        if res:
                            self.send_reward_approval_email(request, approvers, reward_obj, user_id )
                            self.send_reward_congrats_email(reward_id, request.user)
                            self.__create_tv_notification(type, reward_obj)

                if is_success:
                    response['success'] = True

                response["status"] = 200
                response["message"] = "Nomination updated successfully ."

        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(str(err), self.__log.error(self.__exception.get_exception()))
            response["status"] = 499
        return response

    def reject_reward_status(self, request):
        response = {"error": '', "success":False, "status": 200}
        try:
            user_id = request.user.id
            data = request.data
            reward_id = int(data.get("reward_id"))
            reason = data.get('reason')

            reward_obj = RewardsDA().get_reward_by_id(reward_id)
            if not reward_obj:
                response["error"] = "Nomination Does not Exist ."
                response["status"] = 499
                return response

            if not self.__is_allowed_to_approve_reward(user_id,reward_id):
                response['error'] = settings.ERROR_MSG['no_permission']
                response['status'] = 499
                return response

            reward_dict = {}
            reward_dict['status'] = 4

            res = RewardsDA().update_reward(reward_id, reward_dict)
            if res:
                response["status"] = 200
                response['success'] = True
                response["message"] = "Nomination Rejectd Successfully ."
                cc_addresses = []
                approvers = RewardsDA().get_reward_approvers(reward_id)
                for approver in approvers:
                    approver_user = UserDA().get_user_by_id(approver.approver_id)
                    cc_addresses.append(approver_user.email)
                user_name = request.user.first_name+' '+request.user.last_name
                nominator = UserDA().get_user_by_id(reward_obj.nominated_by)
                employee = UserDA().get_user_by_id(reward_obj.receiving_emp_id)

                emp_name = employee.first_name+' '+employee.last_name
                template_name = 'reward_rejection.html'
                subject = f"{reward_obj.reward_type.name} Nomination for {emp_name} Rejected"
                mail_context = {}
                mail_context['type'] = reward_obj.reward_type.name
                mail_context['heading'] = subject
                mail_context['approver'] = nominator.first_name+' '+nominator.last_name+', '
                mail_context['emp_name'] = emp_name
                mail_context['hr_name'] = user_name
                mail_context['hr_position'] = self.__utility.get_designation_of_employee(user_id)
                mail_context['hr_contact_info'] = request.user.email
                email_content = self.__generate_email_template(template_name, mail_context)

                self.send_reward_email(subject, email_content, nominator.email, cc_addresses=cc_addresses)

                response['success'] = True
        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(str(err), self.__log.error(self.__exception.get_exception()))
            response["status"] = 499
        return response

    def cancel_reward(self, request):
        response = {'status':200, 'error':'', 'success':False}
        try:
            user_id = request.user.id
            data = request.data
            reward_id = int(data.get("reward_id"))
            reward_obj = RewardsDA().get_reward_by_id(reward_id)
            if not reward_obj:
                response["error"] = "Nomination does not exist ."
                response["status"] = 499
                return response

            if not self.__is_allowed_to_cancel(user_id,reward_id):
                response['error'] = settings.ERROR_MSG['access_denied']
                response['status'] = 403
                return response

            res = RewardsDA().update_reward(reward_id, {'is_deleted':1})
            if res:
                response["status"] = 200
                response['success'] = True
                response["message"] = "Nomination Cancelled Successfully ."
        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(str(err), self.__log.error(self.__exception.get_exception()))
            response["status"] = 499
        return response

    def create_comments(self, request):
        response = {"error": '', "success": False, "status": 200}
        try:
            user_id = request.user.id
            data = request.data
            reward_id = int(data.get("reward_id"))
            comment = data.get('comment')

            reward_obj = RewardsDA().get_reward_by_id(reward_id)
            if not reward_obj:
                response["error"] = "Nomination does not exist ."
                response["status"] = 499
                return response

            if not self.__is_allowed_to_comment_reward(user_id, reward_id):
                response['error'] = settings.ERROR_MSG['no_permission']
                response['status'] = 403
                return response

            reward_comment_dict = {}
            reward_comment_dict['comment'] = comment
            reward_comment_dict['created_by'] = user_id
            reward_comment_dict['reward'] = RewardsDA().get_reward_by_id(reward_id)
            res = RewardsDA().create_reward_comment(reward_comment_dict)
            if res:
                response['success'] = True
                response["status"] = 200
                response["message"] = "New comment added successfully."

        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(str(err), self.__log.error(self.__exception.get_exception()))
            response["status"] = 499
        return response

    def get_reward_comments(self, request, reward_id):
        response = {'data' :[], 'error': ''}
        user_dict = {}
        try:
            user_id = request.user.id
            active_users = UserDA().get_all_active_users()
            for each in active_users:
                user_dict[each.id] = each.first_name+' '+each.last_name
            reward_comments = RewardsDA().get_reward_comments(reward_id)
            for each in reward_comments:
                temp_dict = {}
                temp_dict['emp_name'] = user_dict[each.created_by]
                temp_dict['comment'] = each.comment
                temp_dict['created_date'] = each.created_date.strftime('%m/%d/%Y , %I:%M %p')
                response['data'].append(temp_dict)
        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(str(err), self.__log.error(self.__exception.get_exception()))
            response["status"] = 499
        return response

    def get_dropdown_prams(self, request):
        response = {"reward_types": [], "employee_list": [], 'status': [], 'titles': []}
        try:
            user_id = request.user.id
            role, name = UserDA().get_user_role_by_id(user_id)
            active_users = UserDA().get_all_active_users()
            for each in active_users:
                if user_id==each.id:
                    continue
                response["employee_list"].append({'id':each.id, 'label': each.first_name+' '+each.last_name})
            reward_type = RewardsDA().get_all_reward_types()
            for each in reward_type:
                if role==5 and each.id==1:
                    continue
                response['reward_types'].append({'id': each.id, 'label': each.name})
            for key, name in settings.REWARD_STATUS.items():
                response['status'].append({'id': key, 'label': name})

            response['titles'] = settings.REWARD_TITLES
        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(str(err), self.__log.error(self.__exception.get_exception()))
        return response

    def list_all_rewards(self, request, status=0, date_range=0, nominated_by=0):
        response = {"rewards": [], 'error': ''}
        user_dict = {}
        all_rewards = []
        try:
            user_id = request.user.id
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            active_users = UserDA().get_all_users()
            for each in active_users:
                user_dict[each.id] = each.first_name+' '+each.last_name

            if role_id in (1, 2, 3):
                all_rewards = RewardsDA().get_all_rewards()
            elif role_id==4:
                #team_members = UserDA().get_current_team_members_by_lead_id(user_id)
                #team_member_ids = [x.id for x in team_members]
                # team_member_ids =[]
                # team_member_ids.append(user_id)
                rewads_by_approver_id = RewardsDA().get_rewards_by_approver_id(user_id)
                reward_ids = [x.reward_id for x in rewads_by_approver_id]
                all_rewards = RewardsDA().get_all_rewards_by_team_member_ids([user_id], reward_ids)
            else:
                all_rewards = RewardsDA().get_all_rewards()
                all_rewards = all_rewards.filter(nominated_by=user_id)

            params = request.GET
            if all_rewards:
                filter_status = params.get('status')
                is_nominated = params.get('isNominated')
                start_date = params.get('startDate')
                end_date = params.get('endDate')
                if filter_status not in ('', 'null', '0', None):
                    all_rewards = all_rewards.filter(status=filter_status)
                if is_nominated not in ('', 'null', '0', None):
                    all_rewards = all_rewards.filter(nominated_by=user_id)
                if start_date not in ('', 'null', '0', None):
                    start_date = datetime.strptime(start_date, '%Y-%m-%d')
                    end_date = datetime.strptime(end_date, '%Y-%m-%d')
                else:
                    start_date = datetime.now() - timedelta(days=183)
                    end_date = datetime.now()
                    # all_rewards = all_rewards.filter(Q(created_date__range=(start_date, end_date)) | Q(created_date=start_date) | Q(created_date=end_date))
                all_rewards = all_rewards.filter(created_date__date__gte=start_date, created_date__date__lte=end_date)

                # if end_date not in ('', 'null', '0', None):
                #     all_rewards = all_rewards.filter(status=filter_status)
            permitted_rewards = RewardsDA().get_reward_approvers_by_approver(user_id)
            permitted_rewards_dict = {}
            for each in permitted_rewards:
                if each.is_approved:
                    permitted_rewards_dict[each.reward.id] = each.is_approved

            for reward in all_rewards:
                is_approved = False
                if permitted_rewards_dict.get(reward.id):
                    is_approved = True
                temp_dic = {}
                temp_dic['reward_id'] = reward.id
                temp_dic['emp_name'] = user_dict[reward.receiving_emp_id]
                temp_dic['nominated_by'] = user_dict[reward.nominated_by]
                temp_dic['nominated_id'] = reward.nominated_by
                temp_dic['reward_type'] = reward.reward_type.name
                temp_dic['status'] = reward.status
                temp_dic['title'] = reward.title
                temp_dic['short_desc'] = reward.short_description
                temp_dic['just_desc'] = reward.justification_description
                temp_dic['is_approved'] = is_approved
                response["rewards"].append(temp_dic)
        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(str(err), self.__log.error(self.__exception.get_exception()))
        return response

    def get_reward_criterias(self, request, type_id):
        response = {"criterias": [], 'error': ''}
        try:
            criterias = RewardsDA().get_master_criterias(type_id)
            for each in criterias:
                response['criterias'].append({'id': each.id, 'label': each.criteria})
        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(str(err), self.__log.error(self.__exception.get_exception()))
        return response

    def view_reward_details(self, request, reward_id):
        response = {'data' :{}, 'error': ''}
        user_dict = {}
        try:
            user_id = request.user.id
            reward = RewardsDA().get_reward_by_id(reward_id)
            if not self.__is_allowed_to_view_reward(user_id, reward):
                response['error'] = settings.ERROR_MSG['access_denied']
                response['status'] = 403
                return response

            active_users = UserDA().get_all_active_users()
            for each in active_users:
                user_dict[each.id] = each.first_name+' '+each.last_name

            if reward:
                temp_dic = {}
                temp_dic['reward_id'] = reward.id
                temp_dic['emp_name'] = user_dict[reward.receiving_emp_id]
                temp_dic['nominated_by'] = user_dict[reward.nominated_by]
                temp_dic['nominated_id'] = reward.nominated_by
                temp_dic['reward_type'] = reward.reward_type.name
                temp_dic['status'] = reward.status
                temp_dic['title'] = reward.title
                temp_dic['short_desc'] = reward.short_description
                temp_dic['just_desc'] = reward.justification_description
                response['data']['reward_data'] = temp_dic

            reward_comments = RewardsDA().get_reward_comments(reward_id)
            reward_comment_list = []
            if reward_comments:
                for each in reward_comments:
                    temp_dict = {}
                    temp_dict['emp_name'] = user_dict[each.created_by]
                    temp_dict['comment'] = each.comment
                    temp_dict['created_date'] = each.created_date.strftime('%m/%d/%Y , %I:%M %p')
                    reward_comment_list.append(temp_dict)
            response['data']['reward_comment_list'] = reward_comment_list

            approver_details = RewardsDA().get_reward_approvers(reward_id)
            approver_data_list = []
            if approver_details:
                for each in approver_details:
                    temp_dict = {}
                    temp_dict['approver_name'] = user_dict[each.approver_id]
                    temp_dict['approved_date'] = each.approval_date.strftime('%m/%d/%Y, %I:%M %p') if each.approval_date else 'Pending'
                    approver_data_list.append(temp_dict)
            response['data']['approver_data'] = approver_data_list

            reward_criterias = RewardsDA().get_reward_criteria(reward_id)
            criteria_list = []
            if reward_criterias:
                for each in reward_criterias:
                    criteria_list.append(each.criteria.criteria)
            response['data']['criteria_list'] = criteria_list

        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(str(err), self.__log.error(self.__exception.get_exception()))
            response["status"] = 499
        return response

    def get_my_rewards(self, request):
        response = {'error': '', 'rewards': []}
        user_dict = {}
        try:
            user_id = request.user.id
            params = request.GET
            start_date = params.get('startDate')
            end_date = params.get('endDate')
            if start_date not in ('', 'null', '0', None):
                start_date = datetime.strptime(start_date, '%Y-%m-%d')
                end_date = datetime.strptime(end_date, '%Y-%m-%d')
            else:
                start_date = datetime.now() - timedelta(days=183)
                end_date = datetime.now()
            all_users = UserDA().get_all_users()
            for each in all_users:
                user_dict[each.id] = each.first_name+' '+each.last_name
            rewards = RewardsDA().get_all_my_rewards(user_id, start_date, end_date, 3)
            for each in rewards:
                temp_dict = {}
                temp_dict['nominated_by'] = user_dict[each.nominated_by]
                temp_dict['published'] = each.published_date.strftime('%m/%d/%Y, %I:%M %p')
                temp_dict['reward_type'] = each.reward_type.name
                temp_dict['title'] = each.title
                response['rewards'].append(temp_dict)
        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(str(err), self.__log.error(self.__exception.get_exception()))
            response["status"] = 499
        return response

    def send_reward_email(self, subject, content, to_email, cc_addresses=[], bcc_address=[]):
        mail_dto = {}
        mail_dto["subject"] = subject
        mail_dto["from_address"] = settings.EMAIL_ADDRESS['do_not_reply']['name']
        mail_dto["body"] = content
        mail_dto["to_addresses"] = [to_email]
        mail_dto["cc_addresses"] = cc_addresses
        mail_dto["bcc_address"] = bcc_address
        mail_dto["smtp_username"] = settings.EMAIL_ADDRESS['do_not_reply']['mailID']
        mail_dto["smtp_password"] = settings.EMAIL_ADDRESS['do_not_reply']['password']
        send_email_notification.apply_async(
            [mail_dto, 1], queue=settings.CELERY_QUEUE['mail_sender'])


    def test_mail(self):
        a= [73,74]#, 73,74]
        for each_item in a:
            self.send_reward_congrats_email(each_item, None)


    def send_reward_congrats_email(self, reward_id, user):
        template_name = 'reward_congrats.html'
        cc_addresses = [settings.TEAM_EMAIL]
        #cc_addresses = ['kssubish999@gmail.com']

        reward_obj = RewardsDA().get_reward_by_id(reward_id)
        nominator = UserDA().get_user_by_id(reward_obj.nominated_by)
        employee = UserDA().get_user_by_id(reward_obj.receiving_emp_id)

        subject = f"Congratulations on Your {reward_obj.reward_type.name}"

        mail_context = {}
        mail_context['heading'] = subject
        mail_context['nominated_by'] = nominator.first_name+' '+nominator.last_name
        mail_context['designation'] = self.__utility.get_designation_of_employee(reward_obj.nominated_by)
        mail_context['title'] = reward_obj.title
        mail_context['short_desc'] = reward_obj.short_description
        mail_context['emp_name'] = employee.first_name+' '+employee.last_name
        email_content = self.__generate_email_template(template_name, mail_context)
        self.send_reward_email(subject, email_content, employee.email, cc_addresses=cc_addresses)

    def show_reward_reports(self, request):
        response = {'error':'', 'status':200, 'reports': []}
        user_dict = {}
        result_dict = {}
        try:
            user_id = request.user.id
            is_permitted = self.__is_allowed_to_view_report(user_id)
            if not is_permitted:
                response['error'] = settings.ERROR_MSG['access_denied']
                response['status'] = 403
                return response

            active_users = UserDA().get_all_active_users()
            for each in active_users:
                user_dict[each.id] = each.first_name+' '+each.last_name

            filter_data = request.data
            filter_type = filter_data.get('type')
            reward_type = filter_data.get('reward_type')
            employees = filter_data.get('employees')
            rewards = RewardsDA().get_all_rewards(status=3, reward_type=int(reward_type), emp_id=employees)
            if int(filter_type)==1:
                try:
                    month = filter_data.get('month').split('_')[0]
                    year = filter_data.get('month').split('_')[1]
                    rewards = rewards.filter(
                        published_date__year=year,
                        published_date__month=month
                    )
                except:
                    pass
            elif int(filter_type)==2:
                try:
                    year = filter_data.get('year')
                    rewards = rewards.filter(
                        published_date__year=year
                    )
                except:
                    pass
            elif int(filter_type)==3:
                try:
                    custom_date = filter_data.get('custom_date')
                    start_date = custom_date.get('startDate')
                    end_date = custom_date.get('endDate')
                    start_date = datetime.strptime(start_date, '%Y-%m-%d')
                    end_date = datetime.strptime(end_date, '%Y-%m-%d')
                    rewards = rewards.filter(
                        published_date__date__gte=start_date,
                        published_date__date__lte=end_date,
                    )
                except:
                    pass
            if rewards:
                type_dict = {}
                reward_types = RewardsDA().get_all_reward_types()
                for each in reward_types:
                    type_dict[each.id] = each.name
            for reward in rewards:
                # temp_dict = {}
                # temp_dict['name'] = user_dict[reward.receiving_emp_id]
                # temp_dict['reward_id'] = reward.id
                if reward.receiving_emp_id in result_dict.keys():
                    if type_dict[reward.reward_type.id] in result_dict[reward.receiving_emp_id].keys():
                        result_dict[reward.receiving_emp_id][type_dict[reward.reward_type.id]] += 1
                    else:
                        result_dict[reward.receiving_emp_id][type_dict[reward.reward_type.id]] = 1
                else:
                    result_dict[reward.receiving_emp_id] = {type_dict[reward.reward_type.id]: 1}

            for emp_id, values in result_dict.items():
                if not user_dict.get(emp_id, None):
                    continue
                temp_dict = {}
                temp_dict['emp_id'] = emp_id
                temp_dict['emp_name'] = user_dict.get(emp_id, 'Former employee')
                temp_dict['rewards'] = []
                for each in reward_types:
                    count = values.get(each.name, 0)
                    temp_dict['rewards'].append({'name': each.name, 'count': count})

                response['reports'].append(temp_dict)
        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(str(err), self.__log.error(self.__exception.get_exception()))
            response["status"] = 499
        return response

    def show_reward_report_details(self, request):
        response = {'error':'', 'status':200, 'data': [], 'emp_name': ''}
        user_dict = {}
        type_dict = {}
        try:
            user_id = request.user.id
            is_permitted = self.__is_allowed_to_view_report(user_id)
            if not is_permitted:
                response['error'] = settings.ERROR_MSG['access_denied']
                response['status'] = 403
                return response

            active_users = UserDA().get_all_active_users()
            for each in active_users:
                user_dict[each.id] = each.first_name+' '+each.last_name

            filter_data = request.data
            filter_type = filter_data.get('stype')
            reward_type = filter_data.get('selected_type')
            emp_id = filter_data.get('emp_id')

            response['emp_name'] = user_dict[int(emp_id)]

            rewards = RewardsDA().get_all_rewards(status=3, reward_type=int(reward_type), emp_id=emp_id)
            if int(filter_type)==1:
                try:
                    month = filter_data.get('selected_month').split('_')[0]
                    year = filter_data.get('selected_month').split('_')[1]
                    rewards = rewards.filter(
                        published_date__year=year,
                        published_date__month=month
                    )
                except:
                    pass
            elif int(filter_type)==2:
                try:
                    year = filter_data.get('selected_year')
                    rewards = rewards.filter(
                        published_date__year=year
                    )
                except:
                    pass
            elif int(filter_type)==3:
                try:
                    start_date = filter_data.get('start_date')
                    end_date = filter_data.get('end_date')
                    start_date = datetime.strptime(start_date, '%Y-%m-%d')
                    end_date = datetime.strptime(end_date, '%Y-%m-%d')
                    rewards = rewards.filter(
                        published_date__date__gte=start_date,
                        published_date__date__lte=end_date,
                    )
                except:
                    pass
            if rewards:
                reward_types = RewardsDA().get_all_reward_types(int(reward_type))
                for each in reward_types:
                    type_dict[each.id] = each.name

                for reward in rewards.order_by('reward_type_id'):
                    temp_dict = {}
                    temp_dict['name'] = user_dict[reward.receiving_emp_id]
                    temp_dict['nominated_by'] = user_dict[reward.nominated_by]
                    temp_dict['awarded_on'] = reward.published_date.strftime('%m/%d/%Y, %I:%M %p')
                    temp_dict['reward_type'] = reward.reward_type.name
                    temp_dict['title'] = reward.title
                    approver_details = RewardsDA().get_reward_approvers(reward.id)
                    approver_data_list = []
                    if approver_details:
                        for each in approver_details:
                            app_dict = {}
                            app_dict['approver_name'] = user_dict[each.approver_id]
                            app_dict['approved_date'] = each.approval_date.strftime('%m/%d/%Y, %I:%M %p')
                            approver_data_list.append(app_dict)
                    temp_dict['approver_data'] = approver_data_list

                    response['data'].append(temp_dict)

        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(str(err), self.__log.error(self.__exception.get_exception()))
            response["status"] = 499
        print(response)
        return response


    def update_reward_content(self, request):
        response = {'error': '', 'success': False}
        try:
            user_id = request.user.id
            request_data = request.data
            reward_id = request_data.get('reward_id', '')

            is_permitted = self.__is_allowed_to_update_reward(reward_id, user_id)
            if not is_permitted:
                response['error'] = settings.ERROR_MSG['access_denied']
                response['status'] = 403
                return response

            update_dict = {}
            update_dict['title'] = request_data.get('title', '')
            update_dict['short_description'] = request_data.get('short_desc', '')
            update_dict['short_description'] = request_data.get('short_desc', '')
            update_dict['justification_description'] = request_data.get('just_desc', '')

            res = RewardsDA().update_reward(reward_id, update_dict)
            if res:
                response['message'] = 'Reward Updated Successfully'
                response['success'] = True
        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(str(err), self.__log.error(self.__exception.get_exception()))
            response["status"] = 499
        return response

    def get_report_parameters(self, request):
        response = {'error': '', 'employees': [], 'reward_types': []}
        try:
            active_users = UserDA().get_all_active_users()
            for each in active_users:
                response['employees'].append({'label': f'{each.first_name} {each.last_name}', 'value': each.id})

            reward_types = RewardsDA().get_all_reward_types()
            for each in reward_types:
                response['reward_types'].append({'label': each.name, 'value': each.id})
        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(str(err), self.__log.error(self.__exception.get_exception()))
            response["status"] = 499
        return response

    def get_tv_notifications(self, request):
        response = {'error': '', 'data': {}}
        gas_result = { "title": "Gift A Smile Winners", 'data': []}
        wow_result = { "title": "Wow Card Winners", 'data': []}
        birthday_result = { "title": "", 'data': []}
        notice_result = { "title": "", 'data': []}
        outing_result = { "title": "", 'data': []}
        new_joinee_result = { "title": "", 'data': []}
        certification_result = { "title": "", 'data': []}
        user_dict = {}
        try:
            start_date = date.today()
            active_users = UserDA().get_all_active_users()
            for each in active_users:
                user_dict[each.id] = f'{each.first_name} {each.last_name}'
            notifications = RewardsDA().get_notifications(start_date)


            for each in notifications:
                details_obj = RewardsDA().get_notification_details(each.id)

                if each.type == 'Event':
                    for detail in details_obj:
                        temp_dict = {'id': each.id, 'title': each.title, 'short_desc': each.short_desc, 'long_desc': each.long_desc}
                        file_path = self.__get_event_url(detail.url)
                        temp_dict['image_url'] = file_path
                        outing_result['data'].append(temp_dict)
                elif each.type == 'New Joinee':
                    for detail in details_obj:
                        temp_dict = {'id': each.id, 'title': each.title, 'short_desc': each.short_desc, 'long_desc': each.long_desc}
                        file_path = self.__get_event_url(detail.url)
                        temp_dict['image_url'] = file_path
                        new_joinee_result['data'].append(temp_dict)
                elif each.type == 'Certification':
                    for detail in details_obj:
                        temp_dict = {'id': each.id, 'title': each.title, 'short_desc': each.short_desc, 'long_desc': each.long_desc}
                        file_path = self.__get_event_url(detail.url)
                        temp_dict['image_url'] = file_path
                        certification_result['data'].append(temp_dict)
                elif each.type=='Birthday':
                    temp_dict = {'id': each.id, 'title': each.title, 'short_desc': each.short_desc, 'long_desc': each.long_desc}
                    temp_dict['emp_name'] = user_dict[int(each.emp_id)]
                    temp_dict['image_url'] = self.__get_image_url(each.emp_id)
                    birthday_result['data'].append(temp_dict)
                elif each.type=='Notice':
                    temp_dict = {'id': each.id, 'title': each.title, 'short_desc': each.short_desc, 'long_desc': each.long_desc}
                    notice_result['data'].append(temp_dict)
                else:
                    # Handle other event types
                    temp_dict = {'id': each.id, 'title': each.title, 'short_desc': each.short_desc, 'long_desc': each.long_desc}
                    temp_dict['emp_name'] = user_dict[int(each.emp_id)]
                    temp_dict['image_url'] = self.__get_image_url(each.emp_id)

                    if each.type == 'GaS':
                        gas_result['data'].append(temp_dict)
                    elif each.type == 'Wow':
                        wow_result['data'].append(temp_dict)
                    elif each.type == 'Birthday':
                        birthday_result['data'].append(temp_dict)
                    elif each.type == 'Notice':
                        notice_result['data'].append(temp_dict)


            response['data']['gas_result']=gas_result
            response['data']['wow_result']=wow_result
            response['data']['birthday_result']=birthday_result
            response['data']['notice_result']=notice_result
            response['data']['outing_result']=outing_result
            response['data']['new_joinee_result']=new_joinee_result
            response['data']['certification_result']=certification_result

        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(str(err), self.__log.error(self.__exception.get_exception()))
            response["status"] = 499
        return response


    def get_tv_notifications_v1(self):
        response = {'data': {}}
        gas_result = { "title": "Gift A Smile Winners", 'data': []}
        wow_result = { "title": "Wow Card Winners", 'data': []}
        birthday_result = { "title": "", 'data': []}
        notice_result = { "title": "", 'data': []}
        outing_result = { "title": "", 'data': []}
        user_dict = {}
        try:
            start_date = date.today()
            active_users = UserDA().get_all_active_users()
            for each in active_users:
                user_dict[each.id] = f'{each.first_name} {each.last_name}'
            notifications = RewardsDA().get_notifications(start_date)

            for each in notifications:
                details_obj = RewardsDA().get_notification_details(each.id)
                temp_dict = {}

                temp_dict['title'] = each.title
                temp_dict['short_desc'] = each.short_desc
                temp_dict['long_desc'] = each.long_desc

                if each.type=='GaS':
                    temp_dict['emp_name'] = user_dict[each.emp_id]
                    temp_dict['image_url'] = details_obj[0].url
                    gas_result['data'].append(temp_dict)
                elif each.type=='Wow':
                    temp_dict['emp_name'] = user_dict[each.emp_id]
                    temp_dict['image_url'] = details_obj[0].url
                    wow_result['data'].append(temp_dict)
                elif each.type=='Birthday':
                    temp_dict['image_url'] = details_obj[0].url
                    birthday_result['data'].append(temp_dict)
                elif each.type=='Notice':
                    notice_result['data'].append(temp_dict)
                elif each.type=='Event':
                    temp_dict['image_urls'] = []
                    for detail in details_obj:
                        file_path = detail.url
                        temp_dict['image_urls'].append(file_path)
                    outing_result['data'].append(temp_dict)


            response['data']['gas_result']=gas_result
            response['data']['wow_result']=wow_result
            response['data']['birthday_result']=birthday_result
            response['data']['notice_result']=notice_result
            response['data']['outing_result']=outing_result

        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return response


    def create_tv_notification(self, type, **args):
        DM_VIBES_EXPIRY = 5
        DM_REWARD_EXPIRY = 7
        with transaction.atomic():
            notify_dict = { 'type': type}
            details_dict = {}
            rewarded_by = args.get('rewarded_by', 0)
            title = args.get('title', '')
            short_desc = args.get('short_desc', '')
            long_desc = args.get('long_desc', '')
            emp_id = args.get('emp_id', 0)

            user = UserDA().get_user_by_id(emp_id)

            if type in ('GaS', 'Wow'):

                details_dict['url'] = self.__get_image_url(emp_id)
                notify_dict['start_date'] = date.today()
                notify_dict['end_date'] = date.today()+timedelta(days=DM_REWARD_EXPIRY)

            elif type=='Birthday':
                notify_dict['start_date']  = args.get('date', '')
                notify_dict['end_date']  = args.get('date', '')
                details_dict['url'] = self.__get_image_url(emp_id)
            elif type=='Notice':
                notify_dict['start_date']  = args.get('start_date', '')
                notify_dict['end_date']  = args.get('end_date', '')
            elif type in ('Event', 'New Joinee', 'Certification') :
                details_dict = args.get('image_list', [])
                notify_dict['start_date'] =  args.get('start_date', '')
                notify_dict['end_date'] = args.get('end_date', '')

            notify_dict['emp_id'] = emp_id
            notify_dict['rewarded_by'] = rewarded_by
            notify_dict['title'] = title
            notify_dict['short_desc'] = short_desc
            notify_dict['long_desc'] = long_desc
            res = RewardsDA().create_tv_notifications(notify_dict)
            if res:
                if type not in ('Event', 'New Joinee', 'Certification', 'Notice'):
                    details_dict['notification'] = res
                    RewardsDA().create_tv_notification_details(details_dict)
                else:
                    for each in details_dict:
                        file_name = self.__save_file(each)
                        data = {'notification': res, 'url': file_name}
                        RewardsDA().create_tv_notification_details(data)
            # self.send_live_data()
            return res

    def __get_image_url(self, user_id):
        img_url = UserDA().get_user_profile_by_id(user_id)
        if img_url:
            return f"{settings.DEFAULT_SITE_MEDIA_URL}{img_url.profile_photo}"
        else:
            return None

    def __get_event_url(self, filename):
        file_name = os.path.join(f"{settings.DM_DESK_MEDIA_URL}event_images/{filename}")
        return file_name

    # def send_live_data(self):

    #     channel_layer = get_channel_layer()
    #     # Data to send as the live update
    #     live_update_data = self.get_tv_notifications_v1()

    #     # Send the live update to the WebSocket consumers
    #     async_to_sync(channel_layer.group_send)(
    #         'tv_group',  # Replace with the name of the group your consumer is listening to
    #         {
    #             'type': 'send_live_update',
    #             'data': live_update_data,
    #         }
    #     )

    def manage_notices(self, request):
        response = {'error': '', 'data': []}
        try:
            user_id = request.user.id
            is_permitted = self.__utility.is_permitted(user_id, 'can_manage_tv_notice')
            if not is_permitted:
                response['error'] = settings.ERROR_MSG['access_denied']
                response['status'] = 403
                return response
            start_date = date.today() - timedelta(days=183) #last 6 month
            notices = RewardsDA().get_notifications_by_start_date(start_date, 'Notice')
            for each in notices:
                temp_dict = {}
                temp_dict['notice_id'] = each.id
                temp_dict['title'] = each.title
                temp_dict['description'] = each.long_desc
                temp_dict['start_date'] = each.start_date.strftime('%d/%m/%Y')
                temp_dict['end_date'] = each.end_date.strftime('%d/%m/%Y')
                response['data'].append(temp_dict)
        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(str(err), self.__log.error(self.__exception.get_exception()))
            response["status"] = 499
        return response

    def create_notices(self, request):
        response = {'error': '', 'status': 200, 'success':False}
        try:
            user_id = request.user.id
            is_permitted = self.__utility.is_permitted(user_id, 'can_manage_tv_notice')
            if not is_permitted:
                response['error'] = settings.ERROR_MSG['access_denied']
                response['status'] = 403
                return response
            request_data = request.data

            title = request_data.get('title', '')
            long_desc = request_data.get('long_desc', '')
            start_date = request_data.get('start_date', '')
            end_date = request_data.get('end_date', '')

            res = self.create_tv_notification('Notice', title=title, long_desc=long_desc,\
                start_date=start_date, end_date=end_date)
            if res:
                response['message'] = 'Notice Created Successfully.'
                response['success'] = True
        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(str(err), self.__log.error(self.__exception.get_exception()))
            response["status"] = 499
        return response

    def cancel_notices(self, request):
        response = {'error': '', 'success': False, 'status': 200}
        try:
            user_id = request.user.id
            is_permitted = self.__utility.is_permitted(user_id, 'can_manage_tv_notice')
            if not is_permitted:
                response['error'] = settings.ERROR_MSG['access_denied']
                response['status'] = 403
                return response
            request_data = request.data
            notice_id = request_data.get('notice_id', 0)
            notice_obj = RewardsDA().get_notice_by_id(notice_id)
            if notice_obj.type in ('Event', 'New Joinee', 'Certification'):
                res = RewardsDA().delete_details_by_notification_id(notice_id)
            res = RewardsDA().update_notices(notice_id, {'is_deleted':1})
            if res:
                # self.send_live_data()
                response['message'] = 'Notice Cancelled Successfully'
                response['success'] = True
        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(str(err), self.__log.error(self.__exception.get_exception()))
            response["status"] = 499
        return response

    def update_notice(self, request):
        response = {'error': '', 'success': False, 'status': 200}
        try:
            user_id = request.user.id
            request_data = request.data
            is_permitted = self.__utility.is_permitted(user_id, 'can_manage_tv_notice')
            if not is_permitted:
                response['error'] = settings.ERROR_MSG['access_denied']
                response['status'] = 403
                return response
            notice_id = request_data.get('notice_id', '')
            is_valid_date = self.__validate_notice_date(request_data.get('start_date', ''),request_data.get('end_date', '') )
            if not is_valid_date:
                response['error'] = 'Invalid Date Range.'
                response['status'] = 499
                return response

            update_dict = {}
            update_dict['title'] = request_data.get('title', '')
            update_dict['long_desc'] = request_data.get('long_desc', '')
            update_dict['start_date'] = request_data.get('start_date', '')
            update_dict['end_date'] = request_data.get('end_date', '')

            res = RewardsDA().update_notices(notice_id, update_dict)
            if res:
                # self.send_live_data()
                response['message'] = 'Notice Updated Successfully'
                response['success'] = True
        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(str(err), self.__log.error(self.__exception.get_exception()))
            response["status"] = 499
        return response

    def create_events(self, request):
        response = {'error': '', 'success': False}
        try:
            user_id = request.user.id
            #is_permitted = self.__is_allowed_to_view_report(user_id)
            is_permitted = self.__utility.is_permitted(user_id, 'can_manage_tv_dm_vibes')
            if not is_permitted:
                response['error'] = settings.ERROR_MSG['access_denied']
                response['status'] = 403
                return response

            request_data = request.data
            image_list = request_data.getlist('images')
            title = request_data.get('title', '')
            start_date = request_data.get('startDate', '')
            end_date = request_data.get('endDate', '')
            type = request_data.get('type', '')

            if image_list and len(image_list)>6:
                response['error'] = "Maximum of 6 images allowed."
                response['status'] = 403
                return response

            if len(self.__check_file_size(image_list)):
                response['error'] = "Maximum file size allowed is 5 MB."
                response['status'] = 403
                return response

            if not self.__is_allowed_formats(image_list):
                response['error'] = "Warning: Image set has an unsupported image format."
                response['status'] = 403
                return response

            res = self.create_tv_notification(type=type, title=title, image_list=image_list, \
                start_date=start_date, end_date=end_date)
            if res:
                response['message'] = 'Event Created Successfully'
                response['success'] = True
        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(str(err), self.__log.error(self.__exception.get_exception()))
            response["status"] = 499
        return response

    def list_events(self, request):
        response = {'error': '', 'success': False, 'data': []}
        try:
            user_id = request.user.id
            is_permitted = self.__utility.is_permitted(user_id, 'can_manage_tv_dm_vibes')
            if not is_permitted:
                response['error'] = settings.ERROR_MSG['access_denied']
                response['status'] = 403
                return response
            year = date.today().year
            events = RewardsDA().get_notifications_by_type_list(year, ['Event', 'New Joinee', 'Certification'])
            for each in events:
                temp_dic = {
                    'title': each.title,
                    'images':[],
                    'notice_id':each.id,
                    'start_date': each.start_date.strftime('%d/%m/%Y'),
                    'end_date': each.end_date.strftime('%d/%m/%Y'),
                    'type': each.type
                    }
                details = RewardsDA().get_notification_details(each.id)
                for data in details:
                    file_name =settings.DM_DESK_MEDIA_URL + "event_images/" + data.url
                    temp_dic['images'].append(file_name)
                response['data'].append(temp_dic)
        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(str(err), self.__log.error(self.__exception.get_exception()))
            response["status"] = 499
        return response

    def delete_events(self, request):
        response = {'error': '', 'success': False}
        try:
            user_id = request.user.id
            is_permitted = self.__utility.is_permitted(user_id, 'can_manage_tv_dm_vibes')
            if not is_permitted:
                response['error'] = settings.ERROR_MSG['access_denied']
                response['status'] = 403
                return response
            request_data = request.data
            event_id = request_data.get('event_id', '')
            event_obj = RewardsDA().get_notice_by_id(event_id)
            res = RewardsDA().update_notices(event_id, {'is_deleted':1})
            if event_obj.type in ('Event', 'New Joinee', 'Certification'):
                if res:
                    image_details = RewardsDA().get_notification_details(event_id)
                    for each in image_details:
                        self.__delete_file(each.url)
                    res = RewardsDA().delete_details_by_notification_id(event_id)
                    response['message'] = 'Event Deleted Successfully'
                    response['success'] = True
        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(str(err), self.__log.error(self.__exception.get_exception()))
            response["status"] = 499
        return response

    def __save_file(self, file):
        import uuid #TODO
        file_extension = os.path.splitext(file.name)[1]
        new_file_name = str(uuid.uuid4())+file_extension

        file_path = os.path.join(f"{settings.MEDIA_ROOT}event_images/{new_file_name}") #TODO Change

        self.__file_manager.upload_file(file_path, file.read())
        return new_file_name

    def __delete_file(self, file_name):
        try:
            file_path = os.path.join(f"{settings.MEDIA_ROOT}event_images/{file_name}")
            self.__file_manager.delete_file(file_path)
            return True
        except Exception as e:
            return False

    def __validate_notice_date(self, start_date, end_date):
        status = True
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            if start_date>end_date:
                status = False

        except Exception as error:
            pass
        return status

    def __check_file_size(self, file_list, max_file_size_in_bytes = 5120):
        oversized_files = []
        for file in file_list:
            filesize = file.size/1024.0
            if filesize > max_file_size_in_bytes:
                oversized_files.append(file)

        return oversized_files

    def __is_allowed_formats(self, file_list, allowed_formats = ['.jpeg', '.jpg', '.png', '.webp']):

        for uploaded_file in file_list:
            filename, ext = os.path.splitext(uploaded_file.name)
            ext = ext.lower()

            if ext not in allowed_formats:
                return False

        return True

    def __create_tv_notification(self,type, reward_obj):
        try:
            employee = UserDA().get_user_by_id(reward_obj.receiving_emp_id)
            emp_name = employee.first_name+' '+employee.last_name
            self.create_tv_notification(type, rewarded_by=reward_obj.nominated_by, title=reward_obj.title,\
                long_desc=reward_obj.justification_description, short_desc=reward_obj.short_description, \
                    emp_id=reward_obj.receiving_emp_id)
        except:
            pass


