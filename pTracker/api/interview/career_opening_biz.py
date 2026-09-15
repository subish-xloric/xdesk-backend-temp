from datetime import datetime
from datetime import date
from types import SimpleNamespace

from django.conf import settings

from pTracker.common.utility import Utility
from pTracker.common.logs import Logs
from pTracker.common.exception_handler import ExceptionHandler

from pTracker.api.interview.common_validation import CommonValidation

from pTracker.dataaccess.ptracker_access.interview_da import InterviewDA
from pTracker.dataaccess.ptracker_access.user_da import UserDA
from pTracker.api.interview.notification_biz import NotificationBL




def new_dto():
    dto = SimpleNamespace()
    return dto

class CareerOpeningBL():

    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()

    def create_or_update_career_opening(self, user, data):
        ''' input as JSON response
        data = {
            'career_opening_id' : 0,
            'position_name' : '',
            'ref_no' : '',
            'required_experience' : '',
            'required_qualification' : '' ,
            'soft_skill' : [],
            'technical_skill' : [],
            'comment' : '',
            'number_of_opening' : 1,
            'lead_interviewer' : 0,
            'notify_team' : True or False }'''

        objCareer = InterviewDA()
        objValid = CommonValidation()
        objUser = UserDA()
        response = {
            'error' : '',
            'success' : '',
            'status' : 200,
            'validationError' : ''
        }

        ccaddress = []
        errorLst = []
        email_dict = {}
        allowed_characters = ['&','(',')',',','.','-','_']
        try:
            userID = user.id
            roleID, roleName = objUser.get_user_role_by_id(userID)


            if roleID not in (2, "2"):
                response['error'] = settings.ERROR_MSG['access_denied']
                response['status'] = 403
                return response

            careerID = data.get('careerOpeningID', 0)

            if not objValid.validate_is_integer(data.get('numberOfOpening')):
                errorLst.append({'number_of_opening' : "Number of opening should be integer"})

            positionName = data.get('positionName', '')

            if objValid.is_empty(positionName):
                errorLst.append({'positionName' : "Please fill the position name"})

            if not objValid.validate_string_length(positionName, min=5, max=300):
                errorLst.append({'positionName' : "The position should be minimum 5 and maximum 300 characters in length."})

            if not objValid.validate_is_alpha_numeric_with_special_characters(positionName, allowed_characters):
                errorLst.append({'positionName' : "Special characters except & . , ( ) - _ not allowed"})

            # if objValid.is_empty(data.get('refNo')):
            #     errorLst.append({'ref_no' : 'Please fill the Refferel Number'})


            # if not objValid.validate_is_alpha_numeric_with_special_characters(data.get('refNo'), allowed_characters):
            #     errorLst.append({'ref_no' : "Special characters except & . , ( ) - _ not allowed"})

            # if not objValid.validate_string_length(data.get('refNo'), min=3, max=50):
            #     errorLst.append({'refNoLength' : "Minimum 3 characters / maximum 50 characters"})

            # checkComment = objValid.validate_is_alpha_numeric_with_special_characters(data.get('comment'), allowed_characters)
            # if not checkComment:
            #     flag = False
            #     errorLst.append({'comment' : "Special characters except & . , ( ) - _ not allowed"})
            # checkcommentLength = objValid.validate_string_length(data.get('comment'), min=5, max=500)
            # if not checkcommentLength:
            #     flag = False
            #     errorLst.append({'commentLength'  : "Minimum 5 characters / maximum 500 characters"})

            if not objValid.validate_is_integer(data.get('reportedTo',0)):
                errorLst.append({'lead_interviewer' : "It should be integer"})

            if not objValid.validate_is_integer(data.get('minExp',0)):
                errorLst.append({'Minimum Experience' : "It should be integer"})

            if not objValid.validate_is_integer(data.get('maxExp',0)):
                errorLst.append({'Maximum Experience' : "It should be integer"})

            req_experience = data.get('requiredExperience')
            min_exp_required = 0
            max_exp_required = 0
            if req_experience == 'Experienced':
                min_exp_required =  data.get('minExp')
                max_exp_required = data.get('maxExp')
                if int(max_exp_required) < int(min_exp_required):
                    errorLst.append({'Maximum Experience' : "It should be greater than Minimum Experience"})

            if errorLst:
                response['validationError'] = errorLst
                response['status'] = 499
                return response

            temp_data = {}
            temp_data['position_name'] = data.get('positionName')
            temp_data['ref_no'] = data.get('refNo')
            temp_data['required_experience'] = data.get('requiredExperience')
            temp_data['required_qualification'] = data.get('requiredQualification')
            temp_data['soft_skill'] = data.get('softSkill')
            temp_data['comment'] = data.get('comment','')
            temp_data['number_of_opening'] = data.get('numberOfOpening')
            temp_data['technical_skill'] = data.get('technicalSkill')
            temp_data['lead_interviewer'] = data.get('reportedTo')
            temp_data['created_by'] = userID
            temp_data['deleted_by'] = 0

            temp_data['min_and_max_experience'] = str(min_exp_required)+ '-' + str(max_exp_required)
            notify_team = data.get('notifyTeam',False)

            if careerID:
                is_careerID = objCareer.get_career_opening(careerID)
                if not is_careerID:
                    response['error'] = 'No career opening found in this ID'
                    response['status'] = 499
                    return response
                created_date = data.get('createdDate', '')
                comment = data.get('comment','')
                if created_date:
                    temp_data['created_date'] = created_date
                if comment:
                    temp_data['comment'] = comment
                career_result = objCareer.update_career_opening(careerID,temp_data)
                response['action'] = 'update'
            else:
                career_result = objCareer.create_career_opening(temp_data)
                opening_id = career_result.career_opening_id
                response['action'] = 'create'

            if career_result:
                emp_job_title = self.__get_user_job_title(userID)
                if response['action'] == 'update':
                    response['success'] = "Career opening updated successfully"
                else:
                    ''' Send email notification to the team for opening a career '''
                    if notify_team :
                        opening = objCareer.get_career_opening(opening_id)
                        soft_skills = opening.soft_skill.strip('][').replace("'", "") if opening.soft_skill else []
                        technical_skills = opening.technical_skill.strip('][').replace("'", "") if opening.technical_skill else []

                        email_subject = "Seeking " + opening.position_name
                        emp_name = user.first_name + " " + user.last_name
                        email_dict['heading'] = email_subject
                        email_dict['emp_name'] = emp_name
                        email_dict['position_name'] = opening.position_name
                        email_dict['number_of_opening'] = opening.number_of_opening
                        email_dict['ref_no'] = opening.ref_no
                        email_dict['required_experience'] = opening.required_experience
                        email_dict['required_qualification'] = opening.required_qualification
                        email_dict['number_of_opening'] = opening.number_of_opening
                        email_dict['soft_skills'] = soft_skills
                        email_dict['technical_skills'] = technical_skills
                        email_dict['emp_designation'] = emp_job_title
                        email_dict['empEmail'] = user.email
                        email_dict['jobDescription'] = opening.comment
                        email_dict['years_of_exp_required'] = str(min_exp_required)+ '-' + str(max_exp_required)
                        email_msg = NotificationBL().generate_career_open_email_message(email_dict)
                        to_email = settings.TEAM_EMAIL
                        ccaddress.append( settings.INTERVIEW_DEFAULT_MAIL)
                        NotificationBL().send_opening_notification(email_msg, emp_name, to_email, email_subject, ccaddress)

                    response['success'] = "Career opening created successfully"
            return response
        except Exception as error:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(error, self.__log.error(self.__exception.get_exception()))
            response['status'] = 499
            return response

    def get_career_opening_all(self, request, year, status):
        ''' inputs year and status parameters pass through the url
        year = 2022
        status = 0 or 1 or -1
        0 for closed openings
        1 for opened openings
        -1 for all openings'''
        objCareer = InterviewDA()
        objUser = UserDA()
        response = {'error' : '', 'success' : '', 'status'  :200}
        data = []
        nameIdLst = []
        temp_name = {}
        dataDict = {}
        try:
            userID = request.user.id
            filteredYear = year
            filterStatus = int(status)
            roleID, roleName = objUser.get_user_role_by_id(userID)
            
            is_dropdown = request.GET.get('is_dropdown')

            if filteredYear == date.today().year:
                career_result = objCareer.get_all_career_opening(filterStatus)
            else:
                career_result = objCareer.get_career_opening_by_year(filteredYear,filterStatus)
                
            if career_result and roleID == 4:
                career_result = career_result.filter(lead_interviewer = userID)

            for eachItems in career_result:
                nameIdLst.append(eachItems.lead_interviewer)

            reportednames = objUser.get_user_name_by_id(nameIdLst)
            for eachRow in reportednames:
                temp_name[eachRow.id] = eachRow.first_name + " " + eachRow.last_name

            if not career_result:
                response['error'] = "No career openings found!!!!"
                response['status'] = 499
                return response

            for eachItem in career_result:
                if int(eachItem.created_date.strftime('%Y')) != date.today().year and eachItem.status != 1 and int(filteredYear) != int(eachItem.created_date.strftime('%Y')) and not is_dropdown:
                    continue
                
                softSkillLst = []
                technicalSkillLst = []
                softSkillLst = eachItem.soft_skill.replace("'", "").strip('][').split(', ') if eachItem.soft_skill else []
                technicalSkillLst = eachItem.technical_skill.replace("'", "").strip('][').split(', ') if eachItem.technical_skill else []
                temp_data={}
                if eachItem.status == 0:
                    temp_data['positionName'] = eachItem.position_name
                    temp_data['positionNameAdd'] = " - " + eachItem.created_date.strftime('%Y') + " " + "(closed)"
                else:
                    temp_data['positionName'] = eachItem.position_name
                    temp_data['positionNameAdd'] = " - " + eachItem.created_date.strftime('%Y')
                temp_data['careerOpeningID'] = eachItem.career_opening_id
                temp_data['refNo'] = eachItem.ref_no if eachItem.ref_no else '-'
                temp_data['requiredExperience'] = eachItem.required_experience
                temp_data['requiredQualification'] = eachItem.required_qualification
                temp_data['softSkill'] = softSkillLst
                temp_data['comment'] = eachItem.comment
                temp_data['status'] = eachItem.status
                temp_data['numberOfOpening'] = eachItem.number_of_opening
                temp_data['technicalSkill'] = technicalSkillLst
                temp_data['createdDate'] = eachItem.created_date.strftime('%d-%m-%Y')
                temp_data['createdYear'] = eachItem.created_date.strftime('%Y')
                temp_data['reportedToID'] = eachItem.lead_interviewer
                temp_data['reportedName'] = temp_name.get(eachItem.lead_interviewer , '-')
                temp_data['total_interviews'] = eachItem.total_interviews
                temp_data['no_of_short_listed'] = eachItem.no_of_short_listed
                temp_data['no_of_hold'] = eachItem.no_of_hold
                temp_data['no_of_acquired'] = eachItem.no_of_acquired
                temp_data['closedDate'] = eachItem.closed_date.strftime('%d-%m-%Y') if eachItem.closed_date else '-'
                min_and_max_exp_required = eachItem.min_and_max_experience
                required_experience = eachItem.required_experience
                if required_experience == "Experienced":
                    try:
                        min_and_max = min_and_max_exp_required.split('-')
                        temp_data['minExp'] = min_and_max[0]
                        temp_data['maxExp'] = min_and_max[1]
                    except:
                        temp_data['minExp'] = 0
                        temp_data['maxExp'] = 1
                else:
                    temp_data['minExp'] = 0
                    temp_data['maxExp'] = 0
                data.append(temp_data)
            response['data'] = data
            return response
        except Exception as error:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(error, self.__log.error(self.__exception.get_exception()))
            response['status'] = 499
            return response

    def delete_career_opening(self, user, data):
        objCareer = InterviewDA()
        objUser = UserDA()
        response = {'error' : '', 'success' : '', 'status' : 200}
        candidateLst = []
        temp_data = {}
        try:
            userID = user.id
            opening_id = data.get('openingID', 0)
            comment = data.get('comment', '')

            roleID, roleName = objUser.get_user_role_by_id(userID)
            if roleID not in (2, "2"):
                response['error'] = settings.ERROR_MSG['access_denied']
                response['status'] = 403
                return response

            if not comment:
                response['error'] = "You should enter a comment before delete a career opening."
                response['status'] = 499
                return response

            is_careerID = objCareer.get_career_opening(opening_id)
            if not is_careerID:
                response['error'] = "No career opening found to delete."
                response['status'] = 499
                return response

            candidate = objCareer.get_candidate_by_opening_id(opening_id)
            if not candidate:
                temp_data['is_deleted'] = 1
                temp_data['comment'] = comment
                temp_data['deleted_by'] = userID
                result_career = objCareer.update_career_opening(opening_id,temp_data)
                if result_career:
                    response['success'] = "Career opening deleted successfully"
                    return response

            # for eachCandidate in candidate:
            #     candidateLst.append(eachCandidate.candidate_id)

            # checK_interview = objCareer.get_scheduled_interview_by_candidate(candidateLst)
            # if not checK_interview:
            #     result_career = objCareer.delete_career_opening(careerID)
            #     if result_career:
            #         response['success'] = "Career opening deleted successfully"
            #         return response

            response['error'] = "This opening can not deleted, since some candidates are created for this position, however you can close this position."
            response['status'] = 499
            return response
        except Exception as error:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(error, self.__log.error(self.__exception.get_exception()))
            response['status'] = 499
            return response

    def close_career_opening(self, data, user):
        obj_da = InterviewDA()
        response = {'error' : '', 'success' : '', 'status' : 200}
        candidate_lst = []
        ccaddress = []
        try:
            userID = user.id
            roleID, roleName = UserDA().get_user_role_by_id(userID)
            if roleID not in (2, "2"):
                response['error'] = settings.ERROR_MSG['access_denied']
                response['status'] = 403
                return response

            opening_id = data.get('openingID', 0)
            comment = data.get('comment', '')
            career_opening = obj_da.get_career_opening_by_id(opening_id)

            if career_opening:

                ''' Interview open for this position validation '''
                candidate = obj_da.get_candidate_by_opening_id (opening_id)
                if candidate:
                    for eachCandidate in candidate:
                        candidate_lst.append(eachCandidate.candidate_id)
                    check_interview = obj_da.get_scheduled_interview_by_candidate(candidate_lst)
                    if check_interview:
                        response['error'] = "Can't close this opening since interviews is scheduled for candidates. Please cancel the interviews first."
                        response['status'] = 499
                        return response

                postion_name = career_opening.position_name
                ref_no = career_opening.ref_no

                temp_data = {'comment':comment, 'status':0, 'closed_date': datetime.now()}
                obj_da.update_career_opening(opening_id, temp_data)
                emp_job_title = self.__get_user_job_title(userID)

                emp_name = user.first_name + " " + user.last_name
                email_content_dto = new_dto()
                email_content_dto.comment = comment
                email_content_dto.heading = 'Career Opening Closed'
                email_content_dto.postion_name = postion_name
                email_content_dto.ref_no = ref_no
                email_content_dto.emp_name = emp_name
                email_content_dto.emp_designation = emp_job_title
                email_content_dto.emp_email = user.email

                email_msg = NotificationBL().generate_email_messages(email_content_dto)
                to_email = settings.INTERVIEW_DEFAULT_MAIL
                ccaddress.append(settings.TEAM_EMAIL)
                NotificationBL().send_opening_notification(email_msg, emp_name, to_email, email_content_dto.heading, ccaddress)

            response['success'] = "Career opening closed successfully."
            return response

        except Exception as error:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(error, self.__log.error(self.__exception.get_exception()))
            response['status'] = 499
            return response

    def get_soft_and_technical_skills(self, request):
        objCareer = InterviewDA()
        data = {}
        response = {'error' : '', 'data': '', 'status'  :200}
        softSkillLst = []
        technicalSkillLst = []
        try:
            soft_skills = objCareer.get_soft_skills()
            technical_skills = objCareer.get_technical_skills()
            if soft_skills:
                for eachItem in soft_skills:
                    temp_data = {}
                    temp_data['name'] = eachItem.soft_skill
                    temp_data['is_mandatory'] = eachItem.is_mandatory
                    softSkillLst.append(temp_data)
                data['soft_skills'] = softSkillLst
            if technical_skills:
                for eachRow in technical_skills:
                    temp_data = {}
                    temp_data['name'] = eachRow.technical_skill
                    temp_data['is_mandatory'] = eachRow.is_mandatory
                    technicalSkillLst.append(temp_data)
                data['technical_skills'] = technicalSkillLst
            response['data'] = data
            return response
        except Exception as error:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(error, self.__log.error(self.__exception.get_exception()))
            response['status'] = 499
            return response

    def get_career_opened(self, request):
        objCareer = InterviewDA()
        response = {'error' : '', 'data' : '', 'status' : 200}
        data = []
        try:
            result = objCareer.get_career_opened()

            if not result:
                response['error'] = "No opened career openings"
                response['status'] = 499

            for eachItem in result:
                temp = {}
                temp['id'] = eachItem.career_opening_id
                temp['positionName'] = eachItem.position_name
                data.append(temp)
            response['data'] = data
            return response
        except Exception as error:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(error, self.__log.error(self.__exception.get_exception()))
            response['status'] = 499
            return response

    def __get_user_job_title(self, user_id):
        user_profile = UserDA().get_user_profile_by_id(user_id)
        job_title = UserDA().get_job_title_by_id(user_profile.job_title)
        job_title = job_title.job_title
        return job_title