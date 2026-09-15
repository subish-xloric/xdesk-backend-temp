import os
import uuid
import json
import base64
from datetime import date
from datetime import datetime
from dateutil.relativedelta import relativedelta
from types import SimpleNamespace

from django.conf import settings
from django.db import  transaction
from django.template import loader
from django.http import HttpResponse

from pTracker.common.logs import Logs
from pTracker.common.utility import Utility
from pTracker.common.file_manager import FileManager
from pTracker.dataaccess.ptracker_access.user_da import UserDA
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.api.interview.common_validation import CommonValidation
from pTracker.dataaccess.ptracker_access.interview_da import InterviewDA

from pTracker.cronjobs.email_sender import send_email_notification

def new_dto():
    dto = SimpleNamespace()
    return dto


class CandidateBL():

    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()
        self.__utility = Utility()

    def check_candidate_email_or_phone(self, email, mobile, candidate_id=0):
        obj_da = InterviewDA()
        candidate = obj_da.check_candidate_email_or_phone(email, mobile,candidate_id)
        if candidate:
            return True
        else:
            return False

    def get_active_interview_dict(self):
        active_interview_dict = {}
        interviews = InterviewDA().get_all_active_interviews()
        if interviews:
            for interview in interviews:
                active_interview_dict[interview.candidate_id] = [interview.interview_code, interview.date_and_time]
        return active_interview_dict




    def get_all_candidates(self, user, position=None, status=None):
        objUser = UserDA()
        obj_da = InterviewDA()
        response = {'error' : '', 'success' : '', 'status' : 200, 'action_menu_view_only':0}
        data = []
        position_name_dict = {}
        referel_code_dict = {}
        try:
            userID = user.id
            role_id, role_name = objUser.get_user_role_by_id(userID)
            is_permitted = self.__utility.is_permitted(userID, 'can_view_candidate')
            #Candidate view permission
            if not self.__can_view_candidate(role_id, is_permitted):
                response['error'] = settings.ERROR_MSG['access_denied']
                response['status'] = 403
                return response

            candidates = obj_da.get_all_candidates(position, status)
            if not candidates:
                response['error'] = "No candidate found !!!"
                response['status'] = 499
                return response

            if position:
                positions = obj_da.get_career_openings_by_ids([position])
            else:
                positions = obj_da.get_career_opening()

            for position in positions:
                position_name_dict[position.career_opening_id] = position.position_name
                referel_code_dict[position.career_opening_id] = position.ref_no

            leads_career_openings = None
            career_opening_ids_of_lead = []

            if role_id == 4:
                response['action_menu_view_only'] = 1
                leads_career_openings = InterviewDA().get_leads_career_opening(userID)
                for openings in leads_career_openings:
                    career_opening_ids_of_lead.append(openings.career_opening_id)

            active_interview_dict = self.get_active_interview_dict()
            for candidate in candidates:
                if role_id == 4 and candidate.career_opening_id not in career_opening_ids_of_lead:
                    continue

                candidateStatusText = settings.CANDIDATE_STATUS.get(candidate.candidate_status, '-')
                interview = active_interview_dict.get(candidate.candidate_id, None)
                if interview:
                    if interview[1] < datetime.now():
                        candidateStatusText = "Interview Missed"

                    candidateStatusText =  candidateStatusText + " (" + interview[0] + ")"

                candidate_dict = {}
                log_list = []
                candidate_dict['candidateID'] = candidate.candidate_id
                candidate_dict['firstName'] = candidate.first_name
                candidate_dict['lastName'] = candidate.last_name
                candidate_dict['email'] = candidate.email
                candidate_dict['mobile'] = candidate.mobile
                candidate_dict['careerOpeningID'] = candidate.career_opening_id
                candidate_dict['candidateStatus'] = candidate.candidate_status
                candidate_dict['candidateStatusText'] = candidateStatusText
                candidate_dict['positionName'] = position_name_dict.get(candidate.career_opening_id, '')
                # profile,extension = self.__get_candidate_profile_url(candidate.profile)
                candidate_dict['profile'] = ''
                candidate_dict['profileType'] = ''
                candidate_dict['reference'] = candidate.reference
                candidate_dict['referedEmployee'] = candidate.refered_employee
                candidate_dict['referalCode'] = referel_code_dict.get(candidate.career_opening_id, '')
                candidate_dict['cis'] = self.__get_cis(candidate.candidate_id)

                # candidate_logs = obj_da.get_candidate_logs(candidate.candidate_id)
                # for log in candidate_logs:
                #     log_list.append(log.action)
                candidate_dict['log'] = log_list
                data.append(candidate_dict)
                del candidate_dict, log_list
            response['data'] = data
            return response
        except Exception as error:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(error, self.__log.error(self.__exception.get_exception()))
            response['status'] = 499
            return response

    def __get_cis(self, candidate_id):
        result = {}
        try:
            candidate_obj = InterviewDA().get_candidate_information_sheet_by_candidate_id(candidate_id)
            if candidate_obj:
                result['token'] = candidate_obj.unique_code
        except:
            pass
        return result

    def create_or_update_candidate(self, user, data):
        objUser = UserDA()
        objCandidate = InterviewDA()
        response = {'error' : '', 'success' : '', 'status' : 200, 'validationError' : ''}
        log_data = {}
        errorLst = []
        candidate = None
        validation = CommonValidation()
        try:
            user_id = user.id
            #TODO - Create funtion for permission check , now using the function from interview_biz file
            role_id, role_name = objUser.get_user_role_by_id(user_id)
            is_permitted = self.__utility.is_permitted(user_id, 'can_create_candidate')
            if not self.__can_create_candidate(role_id, is_permitted):
                response['error'] = settings.ERROR_MSG['access_denied']
                response['status'] = 403
                return response

            candidate_id = data.get('candidateID', 0)
            first_name = data.get('firstName', '')
            last_name = data.get('lastName', '')
            email = data.get('email', '')
            mobile = data.get('mobile', '')
            career_opening_id = data.get('careerOpeningID', 0)

            start_date = date.today() + relativedelta(months=-6)
            end_date = date.today()

            if validation.is_empty(first_name):
                errorLst.append({'firstName' : "Please fill the first name."})

            if not validation.validate_string_length(first_name, min=3, max=100):
                errorLst.append({'firstName' : "First name should be minimum 3 and maximum 100 characters in length."})

            if not validation.validate_string_length(last_name, min=1, max=100):
                errorLst.append({'lastName' : "Last name should be minimum 1 and maximum 100 characters in length."})

            if validation.is_empty(last_name):
                errorLst.append({'lastName' : "Please fill the last name."})

            if not validation.is_alpha(first_name.replace(" ", "")):
                errorLst.append({'firstName' : "First name should contain only letters."})

            if not validation.is_alpha(last_name.replace(" ", "")):
                errorLst.append({'lastName' : "Last name should contain only letters."})

            if not validation.is_mobile_number(mobile):
                errorLst.append({'mobile' : "Mobile number is not valid (Enter a 10 digit number)."})

            if not validation.is_email(email):
                errorLst.append({'email' : "Please enter a valid email address."})

            if not validation.clean_integer(career_opening_id):
                errorLst.append({'careerOpeningID' : "Invalid  career opening"})

            if not candidate_id:
                '''Duplicate checking for create candidate '''
                is_valid_candidate = self.check_candidate_email_or_phone(email, mobile)
                if is_valid_candidate:
                    errorLst.append({'DuplicateCandidate' : 'Candidate with same email id or mobile number already exists.'})

            else:
                '''Duplicate checking for update candidate '''
                is_valid_candidate = self.check_candidate_email_or_phone(email, mobile, candidate_id)
                if is_valid_candidate:
                    errorLst.append({'candidate_exists' : 'Email id or mobile number exists for another candidate.'})


                # TODO - Duplicate checking
                # is_valid_candidate = objCandidate.check_candidate_time_range(first_name, last_name, email, start_date, end_date)
                # if is_valid_candidate:
                #     errorLst.append({'createValidation' : 'Candidate have already registred within the six months'})

            if errorLst:
                response['validationError'] = errorLst
                response['status'] = 499
                return response

            temp_data = {}
            temp_data['first_name'] = first_name
            temp_data['last_name'] = last_name
            temp_data['email'] = email
            temp_data['mobile'] = mobile
            temp_data['career_opening_id'] = career_opening_id
            temp_data['reference'] = data.get('reference')
            temp_data['refered_employee'] = data.get('referedEmployee',0)
            temp_data['created_by'] = user.id

            if not candidate_id:
                #'''Resume upload process'''
                profile_doc  = data.get('profile')
                if profile_doc:
                    temp_data['profile'] = self.upload_candidate_profile(profile_doc)
                else:
                    temp_data['profile'] = ""

                with transaction.atomic():
                    candidate = objCandidate.create_candidate(temp_data)
                    self.__create_candidate_log('create', user, candidate)
                success_msg = "Candidate created successfully"

                '''send candidate information sheet email'''
                self.create_candidate_information_sheet(candidate, user)



            else:
                is_candidate = objCandidate.get_candidate_by_id(candidate_id)
                if not is_candidate:
                    response['error'] = "Invalid candidate id"
                    response['status'] = 499
                    return response

                profile_doc  = data.get('profile', None)
                if profile_doc:
                    profileName = is_candidate.profile
                    location = f"{settings.CONFIDENTIAL_DOCS}interview_candidate_profile/"
                    path = os.path.join(location,profileName)
                    file_exists = os.path.exists(path)
                    if file_exists:
                        os.remove(path)
                    temp_data['profile'] = self.upload_candidate_profile(profile_doc)

                with transaction.atomic():
                    candidate = objCandidate.update_candidate(candidate_id, temp_data)
                    new_candidate = objCandidate.get_candidate_by_id(candidate_id)
                    self.__create_candidate_log('update', user, new_candidate)
                success_msg = "Candidate updated successfully"

            if candidate:
                response['success'] = success_msg
            return response
        except Exception as error:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(error, self.__log.error(self.__exception.get_exception()))
            response['status'] = 499
            return response

    def delete_candidate(self, user, data):
        objUser = UserDA()
        objCandidate = InterviewDA()
        response = {'error' : '', 'success' : '', 'status' : 200}
        temp_data = {}
        log_data = {}
        try:
            candidate_id = data.get('candidateID',0)
            comment = data.get('comment', '')

            user_id = user.id
            role_id, role_name = objUser.get_user_role_by_id(user_id)
            is_permitted = self.__utility.is_permitted(user_id, 'can_modify_candidate')
            if not self.__can_create_candidate(role_id, is_permitted):
                response['error'] = settings.ERROR_MSG['access_denied']
                response['status'] = 403
                return response

            if not comment:
                response['error'] = "You should enter a comment before delete a candidate."
                response['status'] = 499
                return response

            candidate = objCandidate.get_candidates(candidate_id)
            if not candidate:
                response['error'] = "No candidate found."
                response['status'] = 499
                return response

            interiews = objCandidate.get_interviews_by_candidate(candidate_id)
            is_interview=False
            for interiew in interiews:
                if interiew.interview_status in (1,2,"1","2"):
                    is_interview = True
                    break

            if is_interview:
                response['error'] = "Not able to delete the candidate {0} since he/she attend or scheduled for an interview.".format(candidate.first_name)
                response['status'] = 499
                return response

            temp_data['is_deleted'] = 1
            temp_data['comment'] = comment
            temp_data['deleted_by'] = user_id
            objCandidate.update_candidate(candidate_id,temp_data)
            self.__create_candidate_log('delete', user, candidate)

            ''' To remove resume from the location '''
            # profileName = is_candidate.profile
            # location = f"{settings.CONFIDENTIAL_DOCS}interview_candidate_profile/"
            # path = os.path.join(location,profileName)
            # file_exists = os.path.exists(path)
            # if file_exists:
            #     os.remove(path)
            response['success'] = "Candidate deleted successfully."
            return response
        except Exception as error:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(error, self.__log.error(self.__exception.get_exception()))
            response['status'] = 499
            return response

    def candidate_offer_released(self, user, data):
        obj_da = InterviewDA()
        response = {'error' : '', 'success' : '', 'status' : 200}
        try:
            user_id = user.id
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            is_permitted = self.__utility.is_permitted(user_id, 'can_modify_candidate')
            if not self.__can_create_candidate(role_id, is_permitted):
                response['error'] = settings.ERROR_MSG['access_denied']
                response['status'] = 403
                return response

            candidate_id = data.get('candidateID', 0)
            comment = data.get('comment', '')

            if not comment:
                response['error'] = "You should enter a comment."
                response['status'] = 499
                return response

            candidate = obj_da.get_candidate_by_id(candidate_id)
            if not candidate:
                response['error'] = "No candidate found."
                response['status'] = 499
                return response

            if candidate.offer_released in (1, "1"):
                response['error'] = "Offer already released for the candidate {0}".format(candidate.first_name)
                response['status'] = 499
                return response

            ''' check interview status is scheduled for candidate whose status is 4 or 5.'''
            if candidate.candidate_status in (4,5,"4","5"):
                interview = obj_da.get_scheduled_interview_by_candidate(candidate_id)
                if interview :
                    response['error'] = "Can not release Offer for the candidate {0} at this point, Since he/she scheduled for an interview.".format(candidate.first_name)
                    response['status'] = 499
                    return response


            if candidate.candidate_status not in (4,5,6,"4","5","6"):
                response['error'] = "Not able to release an Offer to the candidate {0} at this point, Please change the candidate status.".format(candidate.first_name)
                response['status'] = 499
                return response


            temp_data={}
            temp_data['candidate_id'] = candidate_id
            temp_data['offer_released'] = 1
            temp_data['comment'] = comment
            temp_data['candidate_status'] = 6
            obj_da.update_candidate(candidate_id, temp_data)
            self.__create_candidate_log('offer_released', user, candidate)
            response['success'] = "Candidates offer released successfully."
            return response
        except Exception as error:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(error, self.__log.error(self.__exception.get_exception()))
            response['status'] = 499
            return response

    def reject_candidate(self, user, data):
        objUser = UserDA()
        obj_da = InterviewDA()
        response = {'error' : '', 'success' : '', 'status' : 200}
        log_data = {}

        try:
            candidate_id = data.get('candidateID',0)
            comment = data.get('comment', '')

            user_id = user.id
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            is_permitted = self.__utility.is_permitted(user_id, 'can_modify_candidate')
            if not self.__can_create_candidate(role_id, is_permitted):
                response['error'] = settings.ERROR_MSG['access_denied']
                response['status'] = 403
                return response

            if not comment:
                response['error'] = "You should enter a reason before reject a candidate."
                response['status'] = 499
                return response

            candidate = obj_da.get_candidate_by_id(candidate_id)
            if not candidate:
                response['error'] = "Candidate not found for this id."
                response['status'] = 499
                return response

            ''' check interview scheduled for this candidate '''
            interiews = obj_da.get_interviews_by_candidate(candidate_id)
            is_interview=False
            for interiew in interiews:
                if interiew.interview_status in (1,"1"):
                    is_interview = True
                    break

            if is_interview:
                response['error'] = "Not able to reject the candidate {0} since he/she scheduled for an interview.".format(candidate.first_name)
                response['status'] = 499
                return response

            temp_data = {}
            temp_data['candidate_id'] = candidate_id
            temp_data['comment'] = comment
            temp_data['candidate_status'] = 3
            obj_da.update_candidate(candidate_id, temp_data)
            self.__create_candidate_log('rejected', user, candidate)
            response['success'] = "Candidates rejected  successfully."
            return response
        except Exception as error:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(error, self.__log.error(self.__exception.get_exception()))
            response['status'] = 499

            return response

    def __get_action_text(self,action, candidate_name, creator_name):
        action_text = ''
        created_date = datetime.now().strftime("%d/%m/%y %H:%I %p")
        if action=='create':
            action_text = f""" {candidate_name} created by {creator_name}"""
        elif action=='update':
            action_text = f""" {candidate_name} updated by {creator_name}"""
        elif action=='delete':
            action_text = f''' {candidate_name} deleted by {creator_name} '''
        elif action=='offer_released':
            action_text = f''' {candidate_name} offer relesed by {creator_name}'''
        elif action=='rejected':
            action_text = f''' {candidate_name} rejected by {creator_name}'''
        action_text = action_text + " at " + created_date
        return action_text

    def __create_candidate_log(self, action, user, candidate):
        candidate_name = candidate.first_name + " " + " " +candidate.last_name
        creator_name = user.first_name + " " + user.last_name
        action_text = self.__get_action_text(action, candidate_name, creator_name)
        log_data = {}
        log_data['candidate_id'] = candidate.candidate_id
        log_data['action'] = action_text
        log_data['created_by'] = user.id
        InterviewDA().create_candidate_log(log_data)


    def upload_candidate_profile(self, doc):

        filename = doc.name
        extension = filename.split('.')[1]
        name = str(uuid.uuid4()) + '.'+ extension
        file_path = f"{settings.CONFIDENTIAL_DOCS}interview_candidate_profile/{name}"
        FileManager().upload_file(file_path, doc.read())
        return name

    def __get_candidate_profile_url(self, file_name):
        encoded_string = ''
        try:
            extension = file_name.split(".")[1]
        except:
            extension = ''
        if file_name:
            try:
                file_path = os.path.join(settings.CONFIDENTIAL_DOCS, f'interview_candidate_profile/{file_name}')
                file_content = FileManager().read_file(file_path)
                if file_content:
                    encoded_string = base64.b64encode(file_content)
                    # extension = str(file_name).split(".")[1]

            except Exception as e:
                pass
        return encoded_string,extension
    
    
    
    def get_candidate_file(self, request, candidate_id):
        obj_da = InterviewDA()
        response = {'error': '', 'data': {}}
        try:
            user_id = request.user.id
            request_data = request.data
            is_permitted = True #if user_id== emp_id or role==123
            if not is_permitted:
                response["error"] = settings.ERROR_MSG.get("access_denied")
                response["status"] = 403
                return response
            candidate = obj_da.get_candidate_by_id(int(candidate_id))
            file_name = candidate.profile
            pdf_file_path = f"{settings.CONFIDENTIAL_DOCS}interview_candidate_profile/{file_name}"

            file_content = FileManager().read_file(pdf_file_path)
            if file_content:
                response = HttpResponse(file_content , content_type='application/pdf')
                response['Content-Disposition'] = 'inline; filename="your_pdf_file.pdf"'
                return response
            else:
                return HttpResponse(status=404)

        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error'].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response



    # def search_candidate_by_name_email_phone(self, request, search_parameter):
    #     objCandidate = InterviewDA()
    #     objCareer = InterviewDA()
    #     positionNameDict = {}
    #     careerStatusDict = {}
    #     response = {'error' : '', 'success' : '', 'status' : 200}
    #     careerIDLst = []
    #     data = []
    #     try:
    #         filterData = search_parameter
    #         result = objCandidate.get_candidate_by_name_email_phone(filterData)
    #         if not result:
    #             response['error'] = "No candidates Found"
    #             response['status'] = 499
    #             return response
    #         for eachRow in result:
    #             careerIDLst.append(eachRow.careerOpeningID)
    #         positionname = objCareer.get_career_openings_by_ids(careerIDLst)

    #         for each in positionname:
    #             positionNameDict[each.careerOpeningID] = each.positionName
    #             careerStatusDict[each.careerOpeningID] = each.status
    #         for eachRow in result:
    #             temp_result = {}
    #             temp_result['candidateID'] = eachRow.candidateID
    #             temp_result['name'] = eachRow.name
    #             temp_result['email'] = eachRow.email
    #             temp_result['mobile'] = eachRow.mobile
    #             temp_result['careerOpeningID'] = eachRow.careerOpeningID
    #             temp_result['positionName'] = positionNameDict.get(eachRow.careerOpeningID, '')
    #             temp_result['careerStatus'] = careerStatusDict.get(eachRow.careerOpeningID, '')
    #             temp_result['candidateStatus'] = eachRow.candidateStatus
    #             temp_result['profile'] = self.__get_candidate_profile_url(eachRow.profile)
    #             temp_result['createdDate'] = eachRow.createdDate
    #             temp_result['offerReleased'] = eachRow.offerReleased
    #             data.append(temp_result)
    #         response['data'] = data
    #         return response
    #     except Exception as error:
    #         response["error"] = settings.ERROR_MSG['application_error']\
    #             .format(error, self.__log.error(self.__exception.get_exception()))
    #         response['status'] = 499
    #         return response

    #TODO create permission function for candidate
    def __can_view_candidate(self, role_id, is_permitted):
        if role_id in (2,"2",1,"1","3",3, 4, "4"):
            return True
        if is_permitted:
            return True
        return False

    def __can_create_candidate(self, role_id, is_permitted):
        if role_id in (2,"2"):
            return True
        if is_permitted:
            return True
        return False

    def __can_modify_interview(self, role_id, is_permitted):
        if role_id in (2,"2"):
            return True
        if is_permitted:
            return True
        return False

    def candidate_action_validation(self, request, candidate_id, action):
        response = {'error' : '', 'valid': True, 'status' : 200}
        try:
            action = str(action).strip().replace(" ","").lower()
            user_id = request.user.id
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            if action == 'create':
                is_permitted = self.__utility.is_permitted(user_id, 'can_create_candidate')
                if not self.__can_create_candidate(role_id, is_permitted):
                    response['error'] = settings.ERROR_MSG['access_denied']
                    response['status'] = 403
                    response['valid'] = False
                    return response
            else:
                candidate = InterviewDA().get_candidate_by_id(candidate_id)
                if not candidate:
                    response['error'] = 'Invalid candidate.'
                    response['valid'] = False
                    return response

                career_opening_id = candidate.career_opening_id
                candidate_status = int(candidate.candidate_status)
                if action=='schedule':
                    is_permitted = self.__utility.is_permitted(user_id, 'can_create_interview')
                    if not self.__can_modify_interview(role_id, is_permitted):
                        response['error'] = settings.ERROR_MSG['access_denied']
                        response['status'] = 403
                        response['valid'] = False
                        return response

                    if InterviewDA().check_interview_status(candidate_id, interview_status=1):
                        response['error'] = 'An interview has already been arranged for this candidate.'
                        response['valid'] = False
                        return response

                    if candidate_status in (2,3,6):
                        response['error'] = "Regrettably, it's not possible to schedule an interview for this candidate due to their invalid status."
                        response['valid'] = False
                        return response

                    ''' Check opening is closed '''
                    opening = InterviewDA().get_career_opening(candidate.career_opening_id)
                    if opening.status == 0:
                        response['error'] = "Unfortunately, we cannot arrange an interview for this candidate as the career opening is currently closed."
                        response['valid'] = False
                        return response

                elif action=='rejected':
                    if not self.__can_create_candidate(role_id, False):
                        response['error'] = settings.ERROR_MSG['access_denied']
                        response['status'] = 403
                        return response

                    if candidate_status in [3]:
                        response['error'] = "The candidate has already been rejected."
                        response['valid'] = False
                        return response

                elif action=='delete':
                    is_permitted = self.__utility.is_permitted(user_id, 'can_modify_candidate')
                    if not self.__can_create_candidate(role_id, False):
                        response['error'] = settings.ERROR_MSG['access_denied']
                        response['status'] = 403
                        return response

                    if candidate_status != 1:
                        response['error'] = "It is not feasible to delete the candidate at this time, as they might be in line for an interview. However, you do have the option to reject the candidate."
                        response['valid'] = False
                        return response

                elif action=='edit':
                    if not self.__can_modify_interview(role_id, False):
                        response['error'] = settings.ERROR_MSG['access_denied']
                        response['status'] = 403
                        return response

                elif action=='releaseoffer':
                    if not self.__can_create_candidate(role_id, False):
                        response['error'] = settings.ERROR_MSG['access_denied']
                        response['status'] = 403
                        response['valid'] = False
                        return response

                    if candidate_status in (1,2,3):
                        response['error'] = "We are unable to extend an offer to this candidate due to their current invalid status."
                        response['valid'] = False
                        return response

                    if candidate.offer_released in (1, "1"):
                        response['error'] = "The offer for the candidate {0} has already been extended.".format(candidate.first_name)
                        response['valid'] = False
                        return response

                elif action=='viewscorecard':
                    is_permitted = False
                    career_opening = InterviewDA().get_career_opening_by_id(career_opening_id)
                    if role_id in (1,2,3,"1","2","3"):
                        is_permitted = True
                    elif career_opening and career_opening.lead_interviewer == int(user_id):
                        is_permitted = True

                    if not is_permitted:
                        response['error'] = settings.ERROR_MSG['access_denied']
                        response['status'] = 403
                        response['valid'] = False
                        return response

                    interviews = InterviewDA().get_interview(0, candidate_id)
                    if not interviews:
                        response['error'] = "The scorecard is currently unavailable for this candidate."
                        response['valid'] = False
                        return response

            return response
        except Exception as error:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(error, self.__log.error(self.__exception.get_exception()))
            response['status'] = 499
            return response

    def create_candidate_information_sheet(self,candidate, user):

        objCandidate = InterviewDA()
        try:
            postion = objCandidate.get_career_opening(candidate.career_opening_id)
            position_name = postion.position_name
            to_mail = candidate.email
            emp_name = user.first_name + ' ' + user.last_name
            candidate_name = (candidate.first_name).upper()+ ' ' + (candidate.last_name).upper()

            #TODO remove hardcord value
            json_file = open('/var/www/dm_ptracker/backend_app/pTracker/pTracker/json_templates/' + 'candidate_information_sheet.json', 'r', encoding='utf-8')
            template_data = json.load(json_file)

            unique_id = str(uuid.uuid4())
            temp_data = {}
            temp_data['candidate_id'] = candidate.candidate_id
            temp_data['information_sheet'] = json.dumps(template_data)
            temp_data['status'] = 1 # pending
            temp_data['unique_code'] = unique_id
            objCandidate.create_candidate_information_sheet(temp_data)

            bcc_adress = []
            email_dto = new_dto()
            email_dto.candidate_name = candidate_name
            email_dto.position_name = position_name
            email_dto.emp_name = emp_name
            email_dto.emp_designation = self.__get_user_job_title(user.id)
            email_dto.emp_email = user.email
            email_dto.url = f"{settings.BASE_URL}candidate-information-sheet/{unique_id}"
            email_dto.heading = f"Congratulations! You've been shortlisted for an interview at Digital Mesh Softech India P Limited"
            email_msg = self.genarate_candidate_informationsheet_mail(email_dto)
            self.send_candidate_information_sheet_email_notification(email_msg,to_mail,email_dto.heading,bcc_adress)
        except Exception as error:
            print(error)
            self.__log.error(self.__exception.get_exception())

    def update_candidate_information_sheet(self, request):
        response = {'error' : '', 'valid': False, 'status' : 200}
        objCandidate = InterviewDA()
        try:
            token = request.data.get('token')
            json_data = request.data.get('jsonData')
            update_dict = {'information_sheet': json_data, 'status': 2} #2 completed
            result = objCandidate.update_candidate_information_sheet(token, update_dict)
            if result:
                response['valid'] = True
        except Exception as error:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(error, self.__log.error(self.__exception.get_exception()))
            response['status'] = 499
        return response


    def genarate_candidate_informationsheet_mail(self,email_dto):
        email_template = 'candidate_information_sheet_email.html'
        context = {
            "heading": email_dto.heading,
            "position_name": email_dto.position_name,
            "url": email_dto.url,
            "emp_name": email_dto.emp_name,
            "emp_designation": email_dto.emp_designation,
            "emp_email": email_dto.emp_email,
            "candidate_name": email_dto.candidate_name
        }
        html_email = loader.render_to_string(email_template, context)
        return html_email

    def __get_user_job_title(self, user_id):
        user_profile = UserDA().get_user_profile_by_id(user_id)
        job_title = UserDA().get_job_title_by_id(user_profile.job_title)
        job_title = job_title.job_title
        return job_title

    def send_candidate_information_sheet_email_notification(self,email_msg,to_mail,heading,bcc_adress=[]):
        mail_dto = {}
        mail_dto["subject"] = "{0} ".format(heading)
        mail_dto["from_address"] = settings.EMAIL_ADDRESS['do_not_reply']['name']
        mail_dto["body"] = email_msg
        mail_dto["to_addresses"] = [to_mail]
        # mail_dto["cc_addresses"] =  cc_addresses
        mail_dto["bcc_address"] = bcc_adress
        mail_dto["smtp_username"] = settings.EMAIL_ADDRESS['do_not_reply']['mailID']
        mail_dto["smtp_password"] = settings.EMAIL_ADDRESS['do_not_reply']['password']
        send_email_notification.apply_async(
            [mail_dto, 1], queue=settings.CELERY_QUEUE['mail_sender'])

    def get_candidate_information_sheet(self, token, status=1):
        objUser = UserDA()
        objInterview = InterviewDA()
        response = {'error' : '', 'success' : '', 'status' : 200}
        data = []
        position_name = '-'
        candidate_name = '-'
        try:
            cis_sheet = objInterview.get_candidate_information_sheet(token, status) #1 Pending
            if cis_sheet:
                response['data'] = json.loads( cis_sheet.information_sheet)
                candidate_id = cis_sheet.candidate_id
                candidate = objInterview.get_candidate_by_id(candidate_id)
                if candidate:
                    career_id = candidate.career_opening_id
                    candidate_name = candidate.first_name +' ' + candidate.last_name
                    career_opening = objInterview.get_career_opened(career_id)
                    if career_opening:
                        position_name = career_opening.position_name
                response['candidate_name'] = candidate_name
                response['position_applied'] = position_name
            else:
                response['error'] = "Candidate Information Sheet Does Not Exist! ."
        except Exception as error:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(error, self.__log.error(self.__exception.get_exception()))
            response['status'] = 499
        return response
























