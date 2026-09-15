import datetime
import os
import uuid
import base64

from django.db import  transaction
from django.conf import settings
from django.template import loader

from pTracker.common.utility import Utility
from pTracker.dataaccess.ptracker_access.interview_da import InterviewDA
from pTracker.dataaccess.ptracker_access.user_da import UserDA
from pTracker.api.user.lead_emp_mapping import  LeadEmpMapping
from pTracker.cronjobs.email_sender import send_email_notification
from pTracker.common.logs import Logs
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.common.file_manager import FileManager

class InterviewBL():

    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()
        self.__utility = Utility()

    def get_all_user_dict(self):
        user_dict = {}
        active_users = UserDA().get_all_active_users()
        for user in active_users:
            user_name = user.first_name + " " + user.last_name
            user_dict[user.id] = user_name
        return user_dict

    def check_new_interviewer(self,previous_interviewers, new_interviewers):
        obj_user = UserDA()
        cc_address = []

        result = list(set(new_interviewers).difference(set(previous_interviewers)))
        if result:
            interviewerCC = obj_user.get_user_name_by_id(result)
            # for each in interviewerCC:
            #     cc_address.append(each.email)
            # return cc_address
            return interviewerCC
        else:
            return None


    def __get_action_text(self, action, creator_name, candidate_name=""):
        action_text = ''
        created_date = datetime.datetime.now().strftime("%d/%m/%y %H:%I %p")
        if action=='create':
            action_text = f""" Interview created by {creator_name}"""
        elif action=='update':
            action_text = f""" Interview updated by {creator_name}"""
        elif action=='rescheduled':
            action_text = f''' Interview rescheduled by {creator_name} '''
        elif action=='cancel':
            action_text = f''' Interview cancelled by {creator_name}'''
        elif action=='candidate_scheduled':
            action_text = f'''{candidate_name} Interview scheduled by {creator_name}'''
        elif action=='candidate_rescheduled':
            action_text = f'''{candidate_name} Interview rescheduled by {creator_name}'''
        elif action=='candidate_score_card_create':
             action_text = f'''{candidate_name} Interview score card created by {creator_name}'''
        action_text = action_text + " at " + created_date
        return action_text


    def __create_log(self, action, user, interview, log_name, candidate=[]):
        obj_da = InterviewDA()
        log_dict = {}
        if log_name == 'interview':
            creator_name = user.first_name + " " + user.last_name
            action_text = self.__get_action_text(action, creator_name)
            log_dict['interview_id'] = interview.interview_id
            log_dict['action'] = action_text

            obj_da.create_interview_log(log_dict)

        elif log_name == 'candidate':
            candidate_name = candidate.first_name + " " + " " + candidate.last_name
            creator_name = user.first_name + " " + user.last_name
            action_text = self.__get_action_text(action, creator_name, candidate_name)
            log_data = {}
            log_data['candidate_id'] = candidate.candidate_id
            log_data['action'] = action_text
            log_data['created_by'] = user.id
            InterviewDA().create_candidate_log(log_data)


    def __convert_to_date_time(self, date, hr, minute, sec):
        time = datetime.time(hr,minute,sec)
        date = datetime.datetime.strptime(date, '%Y-%m-%d')
        date_and_time = datetime.datetime.combine(date, time)
        return date_and_time

    def __get_mode_of_interview_description(self, mode):
        if mode=='F2F':
            modeDescription = "at our office"
        elif mode=='Telephonic':
            modeDescription = "telephonically"
        elif mode=='Google Meet':
            modeDescription = "Google Meet"
        elif mode=='skype':
            modeDescription = "Skype"
        elif mode=='Teams':
            modeDescription = "Microsoft Teams"
        elif mode=='Online':
            modeDescription = "online"
        elif mode=='Remote':
            modeDescription = "Remote"
        return modeDescription

    # def __create_interview_score_card(self, interview, skill_card_lst):
    #     obj_da = InterviewDA()
    #     bulk_data = []
    #     for eachItem in skill_card_lst[1]:
    #         temp_result = {}
    #         temp_result['interviewID'] = interview.interview_id
    #         temp_result['score'] = 0
    #         temp_result['skill'] = eachItem
    #         temp_result['skillType'] = skill_card_lst[0]
    #         temp_result['note'] = ""
    #         bulk_data.append(temp_result)
    #     obj_da.create_interview_score_card(bulk_data)


    def __get_user_job_title(self, user_id):
        user_profile = UserDA().get_user_profile_by_id(user_id)
        job_title = UserDA().get_job_title_by_id(user_profile.job_title)
        job_title = job_title.job_title
        return job_title

    def __get_all_candidates(self, candidate_ids):
        candidates_dict = {}
        career_opening_ids = []
        candidates = InterviewDA().get_candidates_by_ids(candidate_ids)
        for candidate in candidates:
            candidates_dict[candidate.candidate_id] = {
                'name': candidate.first_name+ ' '+ candidate.last_name,
                'email':candidate.email,
                'mobile':candidate.mobile,
                'career_opening_id':candidate.career_opening_id,
                'profile': candidate.profile
            }
            career_opening_ids.append(candidate.career_opening_id)
        return candidates_dict, career_opening_ids

    def __get_career_openings(self, career_opening_ids):
        opening_dict = {}
        openings = InterviewDA().get_career_openings_by_ids(career_opening_ids)
        if not openings:
            return opening_dict
        for opening in openings:
            opening_dict[opening.career_opening_id] = {
                'position_name':opening.position_name,
                'ref_no':opening.ref_no
            }
        return opening_dict

    def check_interview_status(self, request, candidate_id, status=1):
        response = {'error' : '', 'valid': True, 'status' : 200}
        try:
            res = InterviewDA().check_interview_status(candidate_id, status)
            if res:
                response['valid'] = False
            return response
        except Exception as error:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(error, self.__log.error(self.__exception.get_exception()))
            response['status'] = 499
            return response


    def create_interview(self, user, data):
        objUser = UserDA()
        obj_da = InterviewDA()
        response = {'error' : '', 'success' : '', 'status' : 200}
        try:
            user_id = user.id
            role_id, roleName = objUser.get_user_role_by_id(user_id)
            is_permitted = self.__utility.is_permitted(user_id, 'can_create_interview')
            #Interview create permission
            if not self.__can_create_interview(role_id, is_permitted):
                response['error'] = settings.ERROR_MSG['access_denied']
                response['status'] = 403
                return response

            job_title = self.__get_user_job_title(user_id)
            date = data.get('date')
            hr = int(data.get('timeHr'))
            min = int(data.get('timeMn'))
            section = data.get('timeSection')
            if section.upper() == "PM":
                if hr!=12:
                    hr = hr + 12
            elif section.upper() == "AM" and hr == 12:
                hr = 0
            date_and_time = self.__convert_to_date_time(date, hr, min, 0)

            candidate_id = data.get('candidateID',0)

            temp_data = {}
            temp_data['interview_code'] = data.get('interviewCode')
            temp_data['candidate_id'] = candidate_id
            temp_data['interviewer'] = data.get('interviewer')
            temp_data['date_and_time'] = date_and_time
            temp_data['mode_of_interview'] = data.get('modeOfInterview')
            temp_data['estimated_time'] = data.get('estimatedTime')
            temp_data['created_by'] = user_id
            temp_data['interview_status'] = 1 #scheduled

            notifyCandidate = data.get('notifyCandidate', None)

            candidate = obj_da.get_candidates(candidate_id)
            if not candidate:
                response['error'] = "No candidate found for this candidate id"
                response['status'] = 499
                return response


            candidate_status = int(candidate.candidate_status)
            if candidate.candidate_status in (2,3,6,"2","3","6"):
                response['error'] = '''Can't schedule interview for the candidate {0},
                This candidate may be rejected or acquired
                or already interview scheduled'''.format(candidate.first_name)
                response['status'] = 499
                return response

            postion = obj_da.get_career_opening(candidate.career_opening_id)
            if not postion:
                response['error'] = "No openings found for this career opening id"
                response['status'] = 499
                return response

            if obj_da.get_scheduled_interview_by_candidate(candidate_id):
                response['error'] = '''Can't schedule interview for the candidate {0},
                An interview is already scheduled for the candidate'''
                response['status'] = 499
                return response

            interview = None
            with transaction.atomic():
                interview = obj_da.create_interview(temp_data)
                #Check the candidate status , if status equal to 1 , change status to 2 when schedule interview
                #if candidate_status == 1:
                obj_da.update_candidate(candidate_id, {'candidate_status':2})
                # else:
                #     obj_da.update_candidate(candidate_id, {'candidate_status':7})


                ''' create candidate log after scheduling the interview '''
                self.__create_log('candidate_scheduled', user, interview, 'candidate', candidate)

                ''' create interview log '''
                self.__create_log('create', user, interview, 'interview')

            if interview:
                ccaddress= []
                interviewerLst = []
                mode_description = self.__get_mode_of_interview_description(interview.mode_of_interview)
                notify = str(interview.interviewer).split(',')
                for eachRow in notify:
                    interviewerLst.append(int(eachRow))
                interviewerCC = objUser.get_user_name_by_id(interviewerLst)
                for each in interviewerCC:
                    ccaddress.append(each.email)

                if notifyCandidate:
                    to_mail = candidate.email
                    ccaddress.append(settings.INTERVIEW_DEFAULT_MAIL)
                else:
                    to_mail = settings.INTERVIEW_DEFAULT_MAIL

                hours = int(interview.estimated_time)//3600
                minutes = (int(interview.estimated_time) % 3600)//60
                candidate_name = candidate.first_name + " " + candidate.last_name

                emailDict = {}
                emailDict['candidateName'] = candidate_name
                emailDict['emp_name'] = user.first_name + " " + user.last_name
                emailDict['designation'] = job_title
                emailDict['emp_email'] = user.email
                emailDict['estimateInterviewTime'] = str(hours)+':'+str(minutes)

                if str(interview.interview_code).upper() == 'MACHINE TEST':
                    if mode_description == "at our office" :
                        location = "Our Office"
                    else:
                        location = "Remote"

                    lead_interviewer = objUser.get_user_by_id(postion.lead_interviewer)
                    contact = '-'
                    if lead_interviewer:
                        contact = lead_interviewer.first_name + " " + lead_interviewer.last_name + " Email: " + lead_interviewer.email

                    subject = "Invitation for Machine Test Interview - " + postion.position_name
                    emailDict['date'] = interview.date_and_time.strftime('%d/%m/%Y')
                    emailDict['time'] = interview.date_and_time.strftime('%I:%M %p')
                    emailDict['location'] = location
                    emailDict['coding_tools'] = postion.coding_tools
                    emailDict['lead_interviwer'] = contact
                    email_msg = self.generate_machine_test_invitation_email(emailDict)
                else:
                    subject = "Interview Call for " + postion.position_name
                    #emailDict = {}
                    emailDict['resultPostion'] = postion.position_name

                    emailDict['candidateEmail'] = candidate.email
                    emailDict['heading'] = subject
                    emailDict['interviewCode'] = interview.interview_code
                    #emailDict['emp_name'] = user.first_name + " " + user.last_name
                    #emailDict['designation'] = job_title
                    emailDict['interviewModeDescription'] = mode_description
                    emailDict['dateTime'] = interview.date_and_time.strftime('at %I:%M %p on %d/%m/%Y')
                    #emailDict['estimateInterviewTime'] = str(hours)+':'+str(minutes)
                    #emailDict['emp_email'] = user.email
                    emailDict['onlineComment'] = ''
                    if mode_description == 'online':
                        emailDict['onlineComment'] = "We will send you a separate mail with the meeting invite."

                    email_msg = self.generate_interview_invitation_email_message(emailDict)
                sent_email = self.send_interview_invitation_email_notification(email_msg, to_mail, subject, ccaddress)
                response['success'] = "Interview details created successfully"
                return response
        except Exception as error:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(error, self.__log.error(self.__exception.get_exception()))
            response['status'] = 499
            return response

    def update_interview(self, user, data):
        '''   Inputs
            "interviewID":0,
            "interviewCode": '',
            "date": '',
            "interviewer": '',
            "timeHr": '',
            "timeMn": '',
            "timeSection": '',
            "candidateID": '',
            "modeOfInterview": '',
            "estimatedTime": '',
            "notifyCandidate": '''''
        obj_da = InterviewDA()

        response = {'error' : '', 'success' : '', 'status' : 200}
        temp_dict = {}
        email_dict = {}
        new_interviwers_lst = []

        try:
            # user_id = user.id
            # user_id = user.id
            # role_id, roleName = UserDA().get_user_role_by_id(user_id)
            # is_permitted = self.__utility.is_permitted(user_id, 'can_modify_interview')
            # #Interview modify permission
            # if not self.__can_modify_interview(role_id, is_permitted):
            #     response['error'] = settings.ERROR_MSG['access_denied']
            #     response['status'] = 403
            #     return response
            interviewers = []
            member_ids = []

            user_id= user.id
            interview_id = data.get('interviewID', 0)
            interview = obj_da.get_interview(interview_id)
            if interview:
                temp_interviewers = interview.interviewer.split(',')
                for each in temp_interviewers:
                    interviewers.append(int(each))


            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            is_permitted = self.__utility.is_permitted(user_id, 'can_modify_interview')
            if role_id in (4,'4'):
                member_ids = self.__get_team_members_ids(user_id)

            if not self.__can_modify_interview(role_id, is_permitted,user_id, interviewers, member_ids):
                response['error'] = settings.ERROR_MSG['access_denied']
                response['status'] = 403
                return response

            #interview_id = data.get('interviewID')
            # date = data.get('date')
            # hr = int(data.get('timeHr'))
            # min = int(data.get('timeMn'))
            # section = data.get('timeSection')
            # if section.upper() == "PM":
            #     if hr!=12:
            #         hr = hr + 12
            # elif section.upper() == "AM" and hr == 12:
            #     hr = 0
            # date_and_time = self.__convert_to_date_time(date, hr, min, 0)

            new_interviewer = data.get('interviewer').split(",")
            for each in new_interviewer:
                new_interviwers_lst.append(int(each))

            temp_dict['interview_id'] = interview_id
            temp_dict['interview_code'] = data.get('interviewCode')
            temp_dict['interviewer'] = data.get('interviewer')
            temp_dict['mode_of_interview'] = data.get('modeOfInterview')
            temp_dict['estimated_time'] = data.get('estimatedTime')
            #temp_dict['date_and_time'] = date_and_time
            #TODO - #notify_candidate
            notify_candidate = data.get('notifyCandidate', None)

            #interview = obj_da.get_interview(interview_id)
            if not interview:
                response['error'] = "Interview not found."
                response['status'] = 499
                return response
            obj_da.update_interview(interview_id, temp_dict)
            self.__create_log('update', user, interview, 'interview')

            ''' Send mail to new interviewer '''
            interviewers = self.check_new_interviewer(interviewers,new_interviwers_lst)
            if interviewers:
                emp_job_title = self.__get_user_job_title(user_id)
                for each_interviewer in interviewers:
                    cc_address =[]
                    to_mail = each_interviewer.email
                    subject = "Interview Notification"
                    email_dict['heading'] = subject
                    email_dict['emp_name'] = user.first_name + " " + user.last_name
                    email_dict['emp_email'] = user.email
                    email_dict['designation'] = emp_job_title
                    email_dict['interviewer'] = each_interviewer.first_name+ ' ' + each_interviewer.last_name
                    email_msg = self.generate_interview_notification_new_interviewer(email_dict)
                    sent_email = self.send_interview_invitation_email_notification(email_msg, to_mail, subject, cc_address)
            # if interviewer:
            #     to_mail = settings.INTERVIEW_DEFAULT_MAIL
            #     cc_address = interviewer
            #     subject = "Interview Notification"
            #     email_dict['heading'] = subject
            #     email_dict['emp_name'] = user.first_name + " " + user.last_name
            #     email_msg = self.generate_interview_notification_new_interviewer(email_dict)
            #     sent_email = self.send_interview_invitation_email_notification(email_msg, to_mail, subject, cc_address)
            response['success'] = "Interview updated successfully"
            return response
        except Exception as error:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(error, self.__log.error(self.__exception.get_exception()))
            response['status'] = 499
            return response

    def get_all_interviews(self, request, user, year, status):
        objUser = UserDA()
        objInterview = InterviewDA()
        response = {'error' : '', 'success' : '', 'status' : 200}
        data = []
        temp = {}
        member_ids = []

        try:
            user_id= user.id
            role_id, role_name = objUser.get_user_role_by_id(user_id)
            is_permitted = self.__utility.is_permitted(user_id, 'can_view_interview')
            if role_id in (4,'4'):
                member_ids = self.__get_team_members_ids(user_id)

            start_date = request.GET.get('start_date')
            end_date = request.GET.get('end_date')

            if start_date not in ['null', None] and end_date not in ['null', None]:
                try:
                    start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d')
                    end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d')
                except Exception as e:
                    response['error'] = "Invalid date provided"
                    response['status'] = 499
                    return response

                start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
                end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
                interviews = objInterview.get_all_interviews_by_date_range(start_date, end_date, status)
            else:
                interviews = objInterview.get_all_interviews_by_year(year, status)
            if not interviews:
                response['error'] = "Sorry, there is no interview to show you."
                response['status'] = 499
                return response

            candidate_ids = []
            for interview in interviews:
                candidate_ids.append(interview.candidate_id)

            candidates, career_opening_ids = self.__get_all_candidates(candidate_ids)
            career_openings = self.__get_career_openings(career_opening_ids)

            user_dict = self.get_all_user_dict()

            for interview in interviews:
                temp_interviewers = interview.interviewer.split(',')
                interviewers = []
                for each in temp_interviewers:
                    interviewers.append(int(each))

                #This is view permission settings
                is_view = self.__is_view_interview(role_id, is_permitted, user_id, interviewers, member_ids)
                if not is_view:
                    continue


                temp_record = {}
                temp_record['interviewExpired'] = 0
                temp_record['interviewID'] = interview.interview_id
                temp_record['interviewCode'] = interview.interview_code
                temp_record['candidateID'] = interview.candidate_id


                #temp_record['interviewer'] = interviewer_name
                #temp_record['interviewerData'] = tempLst
                temp_record['interviewStatus'] = interview.interview_status
                temp_record['interviewStatusText'] = settings.INTERVIEW_STATUS.get(interview.interview_status,'-')
                temp_record['dateAndTime'] = interview.date_and_time.strftime('%m/%d/%Y , %H:%I')
                temp_record['strDate'] = interview.date_and_time.strftime('%d/%m/%Y')
                temp_record['time'] = interview.date_and_time.strftime('%I:%M %p')
                temp_record['modeOfInterview'] = interview.mode_of_interview
                temp_record['meetingLink'] = interview.meeting_link
                temp_record['result'] = interview.result
                temp_record['score'] = interview.score
                temp_record['comment'] = interview.comment
                temp_record['estimatedTime'] = interview.estimated_time
                temp['candidateID'] = interview.candidate_id
                if interview.date_and_time < datetime.datetime.now():
                    temp_record['interviewExpired'] = 1
                if interview.meeting_link:
                    temp_record['meetingLinkSent'] = True
                else:
                    temp_record['meetingLinkSent'] = False
                temp_record['interviewers'] = []
                if interviewers:
                    for interviewer in interviewers:
                        temp={}
                        temp['name'] = user_dict.get(int(interviewer))
                        temp['id'] = interviewer
                        temp_record['interviewers'].append(temp)

                candidate = candidates.get(interview.candidate_id,None)
                temp_record['cis'] = self.__get_cis(interview.candidate_id)
                if candidate:
                    temp_record['candidateName'] = candidates[interview.candidate_id]['name']
                    temp_record['candidateEmail'] = candidates[interview.candidate_id]['email']
                    temp_record['candidateMobile'] = candidates[interview.candidate_id]['mobile']
                    opening_id = candidates[interview.candidate_id]['career_opening_id']
                    temp_record['refNo'] = career_openings.get(opening_id)['ref_no']
                    temp_record['positionName'] = career_openings.get(opening_id)['position_name']
                    profile,extension = self.__get_candidate_profile_url(candidate['profile'])
                    temp_record['resume'] = profile
                    temp_record['resumeExtention'] = extension
                    data.append(temp_record)

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

    def cancel_interview(self, user, data):
        objUser = UserDA()
        obj_da = InterviewDA()
        response = {'error' : '', 'success' : '', 'status' : 200}
        temp_dict = {}
        interviewer_lst = []
        ccaddress = []
        email_dict = {}
        candidate_dict = {}
        try:
            user_id= user.id
            interview_id = data.get('interviewID', 0)
            comment = data.get('comment', '')

            #
            interviewers = []
            member_ids = []

            #user_id= user.id
            #interview_id = data.get('interviewID', 0)
            interview = obj_da.get_interview(interview_id)
            if interview:
                temp_interviewers = interview.interviewer.split(',')
                for each in temp_interviewers:
                    interviewers.append(int(each))

            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            is_permitted = self.__utility.is_permitted(user_id, 'can_modify_interview')
            if role_id in [4,'4']:
                member_ids = self.__get_team_members_ids(user_id)

            if not self.__can_modify_interview(role_id, is_permitted,user_id, interviewers, member_ids):
                response['error'] = settings.ERROR_MSG['access_denied']
                response['status'] = 403
                return response

            if not comment:
                response['error'] = "You should enter the reason for the cancellation."
                response['status'] = 499
                return response

            #interview = obj_da.get_interview(interview_id)
            if not interview:
                response['error'] = "No interview found to cancell"
                response['status'] = 499
                return response


            candidate = obj_da.get_candidates(interview.candidate_id)
            ''' Cancel interview '''
            temp_dict['comment'] = data.get('comment', '')
            temp_dict['interview_status'] = 3 # cancelled
            obj_da.update_interview(interview_id, temp_dict)

            #candidate status change from 2 to 1 when cancel the interview.
            candidate_status = int(candidate.candidate_status)
            if candidate_status==2:
                obj_da.update_candidate(interview.candidate_id,{'candidate_status':1})


            ''' Interview Log for cancel the interview'''
            self.__create_log('cancel', user, interview, 'interview')

            ''' Candidate Log for cancel the interview '''
            career = obj_da.get_career_opening(candidate.career_opening_id)
            self.__create_log('cancel', user, interview, 'candidate', candidate)

            #TODO to send notification
            to_mail = settings.INTERVIEW_DEFAULT_MAIL
            notify = str(interview.interviewer).split(',')
            for eachRow in notify:
                interviewer_lst.append(int(eachRow))

            interviewerCC = objUser.get_user_name_by_id(interviewer_lst)
            for each in interviewerCC:
                ccaddress.append(each.email)

            #TODO - confirmation to add candidate mail to ccaddress
            # ccaddress.append(candidate.email)
            emp_job_title = self.__get_user_job_title(user_id)
            candidate_name = candidate.first_name + " " + candidate.last_name
            postion_name = career.position_name
            email_subject = "Interview has been cancelled - {0}".format(candidate_name)
            email_dict['interview_id'] = interview_id
            email_dict['interview_code'] = interview.interview_code
            email_dict['candidate_name'] = candidate_name
            email_dict['position_name'] = postion_name
            email_dict['heading'] = email_subject
            email_dict['date_and_time'] = interview.date_and_time.strftime("%d/%m/%y %I:%M %p")
            email_dict["comment"] = comment
            email_dict["emp_name"]= user.first_name + ' '+ user.last_name
            email_dict["designation"] = emp_job_title
            email_dict["emp_mail"] = user.email
            subject = email_subject
            email_msg = self.generate_interview_cancel_notification_mail(email_dict)
            sent_email = self.send_interview_invitation_email_notification(email_msg, to_mail, subject, ccaddress)

            response['success'] = "Interview cancelled successfully"
            return response
        except Exception as error:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(error, self.__log.error(self.__exception.get_exception()))
            response['status'] = 499
            return response

    def reschedule_interview(self, user, data):
        obj_da = InterviewDA()
        #objInterview = InterviewDA()
        objUser = UserDA()
        ccaddress = []
        interviewerLst = []
        emailDict = {}
        tempData = {}
        interview_dict = {}
        text = "Interview Rescheduled"
        response = {'error' : '', 'success' : '', 'status' : 200}
        try:
            # user_id = user.id
            # role_id, roleName = objUser.get_user_role_by_id(user_id)
            # is_permitted = self.__utility.is_permitted(user_id, 'can_modify_interview')

            # #Interview reschedule permission
            # if not self.__can_modify_interview(role_id, is_permitted):
            #     response['error'] = settings.ERROR_MSG['access_denied']
            #     response['status'] = 403
            #     return response

            interviewers = []
            member_ids = []

            interview_id = data.get('interviewID', 0)
            user_id= user.id
            interview = obj_da.get_interview(interview_id)
            if interview:
                temp_interviewers = interview.interviewer.split(',')
                for each in temp_interviewers:
                    interviewers.append(int(each))

            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            is_permitted = self.__utility.is_permitted(user_id, 'can_modify_interview')
            if role_id in [4,'4']:
                member_ids = self.__get_team_members_ids(user_id)

            if not self.__can_modify_interview(role_id, is_permitted,user_id, interviewers, member_ids):
                response['error'] = settings.ERROR_MSG['access_denied']
                response['status'] = 403
                return response


            date = data.get('date')
            hr = int(data.get('timeHr'))
            min = int(data.get('timeMn'))
            section = data.get('timeSection')
            if section.upper() == "PM":
                if hr!=12:
                    hr = hr + 12
            elif section.upper() == "AM" and hr == 12:
                hr = 0
            date_and_time = self.__convert_to_date_time(date, hr, min, 0)


            interview = obj_da.get_interview(interview_id)
            if not interview:
                response['error'] = "Interview not found for this ID"
                response['status'] = 499
                return response

            tempData['date_and_time'] = date_and_time
            obj_da.update_interview(interview_id, tempData)
            self.__create_log('rescheduled', user, interview, 'interview')
            candidate = obj_da.get_candidates(interview.candidate_id)
            self.__create_log('candidate_rescheduled', user, interview, 'candidate', candidate)

            interviewer = interview.interviewer
            notify = interviewer.split(',')
            for eachRow in notify:
                interviewerLst.append(int(eachRow))
                interviewerCC = objUser.get_user_name_by_id(interviewerLst)

            for each in interviewerCC:
                ccaddress.append(each.email)

            job_title = self.__get_user_job_title(user_id)
            mode_description = self.__get_mode_of_interview_description(interview.mode_of_interview)

            candidate_name = candidate.first_name + " " + candidate.last_name

            '''To get the re-scheduled date and time '''
            new_schdeule = obj_da.get_interview(interview_id)
            date_and_time = new_schdeule.date_and_time.strftime('to %I:%M %p on %d/%m/%Y')

            to_email = candidate.email
            ccaddress.append(settings.INTERVIEW_DEFAULT_MAIL)
            interview_code = interview.interview_code

            text = text + " - " + candidate_name

            hours = int(interview.estimated_time)//3600
            minutes = (int(interview.estimated_time) % 3600)//60
            emailDict['candidateName'] = candidate_name
            emailDict['dateTime'] = date_and_time
            emailDict['interviewCode'] = interview_code
            emailDict['interviewModeDescription'] = mode_description
            emailDict['emp_name'] = user.first_name + " " + user.last_name
            emailDict['designation'] = job_title
            emailDict['resultPostion'] = ""
            emailDict['estimateInterviewTime'] = str(hours)+':'+str(minutes)
            emailDict['heading'] = text
            emailDict['emp_email'] = user.email
            subject = text
            mail_msg = self.generate_interview_invitation_email_message(emailDict)
            send_email = self.send_interview_invitation_email_notification(mail_msg, to_email, subject, ccaddress)
            response['success'] = "Interview rescheduled successfully"
            return response
        except Exception as error:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(error, self.__log.error(self.__exception.get_exception()))
            response['status'] = 499
            return response

    def generate_interview_invitation_email_message(self, emailDict):
        email_template = 'interview_invitation_mail.html'
        context = {
            "heading": emailDict['heading'],
            "emp_name": emailDict['emp_name'],
            "candidate_name": emailDict['candidateName'],
            "interviewCode" : emailDict['interviewCode'],
            "interviewModeDescription" : emailDict['interviewModeDescription'],
            "designation": emailDict['designation'],
            "dateTime" : emailDict['dateTime'],
            "positionName" : emailDict['resultPostion'],
            "timeTaken" : emailDict['estimateInterviewTime'],
            'empEmail': emailDict.get('emp_email'),
            'onlineComment': emailDict.get('onlineComment', ''),
        }

        html_email = loader.render_to_string(email_template, context)
        return html_email

    def send_interview_invitation_email_notification(self, message, to_email, subject, cc_addresses=[]):
        mail_dto = {}
        mail_dto["subject"] = "{0} ".format(subject)
        mail_dto["from_address"] = settings.EMAIL_ADDRESS['do_not_reply']['name']
        mail_dto["body"] = message
        mail_dto["to_addresses"] = [to_email]
        #mail_dto["reply-to"] =  cc_addresses
        mail_dto["bcc_address"] = cc_addresses
        mail_dto["smtp_username"] = settings.EMAIL_ADDRESS['do_not_reply']['mailID']
        mail_dto["smtp_password"] = settings.EMAIL_ADDRESS['do_not_reply']['password']
        send_email_notification.apply_async(
            [mail_dto, 1], queue=settings.CELERY_QUEUE['mail_sender'])

    def generate_interview_confirmation(self, emailDict):
        email_template = 'interview_confirmation_mail.html'
        context = {
            "candidateName" : emailDict['candidateName'],
            "positionName" : emailDict['positionName'],
            "interviewcode" : emailDict['interviewCode'],
            "dateAndTime" : emailDict['dateAndTime'],
            "modeOfInterview" : emailDict['modeOfInterview'],
            "meetingLink" : emailDict['meetingLink'],
            "hr_name" : emailDict['hr_name'],
            "designation" : emailDict['designation'],
            "heading" : emailDict['text']
        }
        html_email = loader.render_to_string(email_template, context)
        return html_email

    def generate_interview_cancel_notification_mail(self, email_dict):
        email_template = 'interview_cancel_mail.html'
        context = {
            "interview_id" : email_dict['interview_id'],
            "interview_code" : email_dict['interview_code'],
            "candidate_name" : email_dict['candidate_name'],
            "position_name" : email_dict['position_name'],
            "heading" : email_dict['heading'],
            "date_and_time" : email_dict['date_and_time'],
            "comment": email_dict["comment"],
            "emp_name": email_dict["emp_name"],
            "designation": email_dict["designation"],
            "emp_mail": email_dict["emp_mail"],

        }
        html_email = loader.render_to_string(email_template, context)
        return html_email





    #TODO - confirmation mail
    # def create_interview_confirmation_mail(self, user, interviewID):
    #     objUser = UserDA()
    #     objInterview = InterviewDA()
    #     response = {'error' : '', 'success' : '', 'status' : 200}
    #     temp_result = {}
    #     ccaddress = []
    #     interviewerLst = []
    #     try:
    #         userID = user.id
    #         userName = objUser.get_user_name_by_id(userID)
    #         creatorName = userName.first_name + " " + userName.last_name

    #         user_profile = UserDA().get_user_profile_by_id(userID)
    #         job_title = UserDA().get_job_title_by_id(user_profile.job_title)
    #         job_title = job_title.job_title

    #         result = objInterview.get_interview(interviewID)
    #         candidateID = result.candidate_id
    #         modeOfInterview = result.mode_of_interview
    #         dateAndTime = result.date_and_timeime
    #         notify=[]
    #         interviewer = result.interviewer
    #         notify = interviewer.split(',')
    #         for eachRow in notify:
    #             interviewerLst.append(int(eachRow))
    #             interviewerCC = objUser.get_user_name_by_id(interviewerLst)

    #         for each in interviewerCC:
    #             ccaddress.append(each.email)
    #         candidate = objInterview.get_candidates(candidateID)
    #         to_email = candidate.email
    #         careerOpeningID = candidate.career_opening_id
    #         careerOpening = objInterview.get_career_opening(careerOpeningID)
    #         positionName = careerOpening.position_name
    #         text = f"Invitation : {modeOfInterview} Interview Invitation @ {dateAndTime} ({to_email})"
    #         candidate_name = candidate.first_name + " " + candidate.last_name
    #         temp_result['candidateName'] = candidate_name
    #         temp_result['positionName'] = positionName
    #         temp_result['interviewCode'] = result.interview_code
    #         temp_result['dateAndTime'] = result.date_and_time
    #         temp_result['modeOfInterview'] = result.mode_of_interview
    #         temp_result['meetingLink'] = result.meeting_link
    #         temp_result['hr_name'] = creatorName
    #         temp_result['designation'] = job_title
    #         temp_result['text'] = text
    #         subject = text
    #         email_confimation = self.generate_interview_confirmation(temp_result)
    #         send_confirmation = self.send_interview_invitation_email_notification(email_confimation, to_email, subject, ccaddress)
    #         if send_confirmation == None:
    #             response['success'] = "Email Sent Successfully"
    #         return response
    #     except Exception as error:
    #         response["error"] = settings.ERROR_MSG['application_error']\
    #             .format(error, self.__log.error(self.__exception.get_exception()))
    #         response['status'] = 499
    #         return response





    # def generate_interview_result_mail(self, emailDict):
    #     email_template = "interview_result_email.html"
    #     context = {
    #         "positionName" : emailDict['positionName'],
    #         "candidateName" : emailDict['candidateName'],
    #         "interviewCode" : emailDict['interviewCode'],
    #         "status" : emailDict['status'],
    #         "heading" : emailDict['heading']
    #     }
    #     html_email = loader.render_to_string(email_template, context)
    #     return html_email








    def __get_team_members_ids(self, lead_id):
        team_members = UserDA().get_current_team_members_by_lead_id(lead_id)
        member_ids = []
        if team_members:
            for team_member in team_members:
                member_ids.append(int(team_member.id))
        return member_ids

    def __is_view_interview(self, role_id, is_permitted, user_id, interviewers, team_ids=[]):
        if role_id in (1,2,3,"1","2","3"):
            return True
        if is_permitted:
            return True
        if user_id in interviewers:
            return True
        if set(interviewers) & set(team_ids):
            return True
        return False

    def __can_modify_interview(self, role_id, is_permitted, user_id, interviewers, team_ids=[]):
        if role_id in (2,"2"):
            return True
        if is_permitted:
            return True
        if user_id in interviewers:
            return True
        if set(interviewers) & set(team_ids):
            return True
        return False

    def __can_create_interview(self, role_id, is_permitted):
        if role_id in (2,"2"):
            return True
        if is_permitted:
            return True
        return False


    def __get_candidate_profile_url(self, file_name):
        encoded_string = ''
        extension = ''
        try:
            extension = str(file_name).split(".")[1]
        except:
            extension = ''
        if file_name:
            try:
                file_path = os.path.join(settings.CONFIDENTIAL_DOCS, f'interview_candidate_profile/{file_name}')
                file_content = FileManager().read_file(file_path)
                if file_content:
                    encoded_string = base64.b64encode(file_content)

            except Exception as e:
                pass
        return encoded_string,extension

    def interview_action_validation(self, request, interview_id, action):
        response = {'error' : '', 'valid': True, 'status' : 200,'is_interview_mail_send': False,'last_send_date': ''}
        try:
            action = str(action).strip().replace(" ","").lower()
            interview = InterviewDA().get_interview(interview_id)
            user_id = request.user.id
            role_id, role_name = UserDA().get_user_role_by_id(user_id)

            if not interview:
                response['error'] = 'Invalid interview.'
                response['valid'] = False
                return response

            interview_status = int(interview.interview_status)
            if action=='scorecard':
                # is_permitted = self.__utility.is_permitted(user_id, 'can_create_interview')
                # if not self.__can_modify_interview(role_id, is_permitted):
                #     response['error'] = settings.ERROR_MSG['access_denied']
                #     response['status'] = 403
                #     response['valid'] = False
                #     return response

                ''' Check the condition for can't create interview_score_card before the interview scheduled date and time '''
                schedule_date = interview.date_and_time
                current_date = datetime.datetime.now()

                if current_date < schedule_date:
                    response['error'] = "Can't create interview score card for this candidate now , you can create it after the scheduled date and time."
                    response['status'] = 499
                    response['valid'] = False
                    return response

                score_card = InterviewDA().get_interview_score_card_by_interview_id(interview_id)
                if score_card:
                    response['error'] = "Scorecard is already created for this interview."
                    response['status'] = 499
                    return response

            elif action in ('drop', 'reschedule','edit'):

                if interview_status not in [1]:
                    response['error'] = "Either interview is completed or cancelled, not able to do any action on this."
                    response['valid'] = False
                    return response
            elif action == 'sendmail':
                interview_mail_status = InterviewDA().get_interview_mail_status(interview_id)
                if interview_mail_status:
                    response['is_interview_mail_send'] = True
                    response['last_send_date'] = (interview_mail_status.created_date).strftime('%d/%m/%y %I:%M %p')
            return response
        except Exception as error:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(error, self.__log.error(self.__exception.get_exception()))
            response['status'] = 499
            return response

    def generate_interview_notification_new_interviewer(self, email_dict):
        email_template = 'interview_notification.html'
        context = {
            "heading": email_dict['heading'],
            "emp_name" : email_dict['emp_name'],
            "emp_email": email_dict['emp_email'],
            "designation" : email_dict['designation'],
            "interviewer" : email_dict['interviewer'],
        }
        html_email = loader.render_to_string(email_template, context)
        return html_email

    def update_interview_comment(self,user,data):
        obj_da = InterviewDA()
        response = {'error' : '', 'success' : '', 'status' : 200}
        interviewers = []
        scores = []
        try:

            user_id = user.id
            role_id, roleName = UserDA().get_user_role_by_id(user_id)

            #Collect input from form
            interview_id = data.get('interview_id',0)
            comment = data.get('comment','')


            interview = obj_da.get_interview(interview_id)
            if interview:
                interview_status = str(interview.interview_status)
                temp_interviewers = interview.interviewer.split(',')
                for each in temp_interviewers:
                    interviewers.append(int(each))

            if not self.__is_comment_interview(role_id, user_id, interviewers):  #nnn include interviewer
                response['error'] = settings.ERROR_MSG['access_denied']
                response['status'] = 403
                return response
            temp = {}
            temp['interview_id'] = int(interview_id)
            temp['comment'] = comment
            temp['created_by'] = user.id
            obj_da.create_interview_comment(temp)
            response['success'] = "Comment created successfully ."
            return response


        except Exception as error:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(error, self.__log.error(self.__exception.get_exception()))
            response['status'] = 499
            return response


    def get_all_interview_comments(self, user, interview_id):
        objUser = UserDA()
        objInterview = InterviewDA()
        response = {'error' : '', 'success' : '', 'status' : 200}
        data = []
        temp = {}
        member_ids = []

        try:
            user_id= user.id
            role_id, role_name = objUser.get_user_role_by_id(user_id)
            is_permitted = self.__utility.is_permitted(user_id, 'can_view_interview')
            if role_id in (4,'4'):
                member_ids = self.__get_team_members_ids(user_id)


            interview = objInterview.get_interview(interview_id)
            if not interview:
                response['error'] = "Sorry, No interview found."
                response['status'] = 499
                return response

            temp_interviewers = interview.interviewer.split(',')
            interviewers = []
            for each in temp_interviewers:
                interviewers.append(int(each))
            is_view = self.__is_view_interview(role_id, is_permitted, user_id, interviewers, member_ids)

            if not is_view:
                response['error'] = "Sorry, No Permission to comment on this interview."
                response['status'] = 499
                return response

            interview_comments = objInterview.get_interview_comments_by_interview_id(interview_id)

            user_dict = self.get_all_user_dict()

            for interview_comment in interview_comments:
                temp_record = {}
                temp_record['name'] = user_dict.get(int(interview_comment.created_by))
                temp_record['comment'] = interview_comment.comment
                temp_record['created_date'] = interview_comment.created_date.strftime('%m/%d/%Y , %I:%M %p')
                data.append(temp_record)

            response['data'] = data
            return response
        except Exception as error:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(error, self.__log.error(self.__exception.get_exception()))
            response['status'] = 499
            return response


    def generate_machine_test_invitation_email(self, emailDict):
        email_template = 'machine_test_interview_invitation_mail.html'
        context = {
            "candidate_name": emailDict['candidateName'],
            "coding_tools": emailDict['coding_tools'],
            "date" : emailDict['date'],
            "time" : emailDict['time'],
            "estimateInterviewTime" : emailDict['estimateInterviewTime'],
            "location" : emailDict['location'],
            "lead_interviwer" : emailDict['lead_interviwer'],
            "emp_name": emailDict['emp_name'],
            "designation": emailDict['designation'],
            'empEmail': emailDict.get('emp_email')
        }

        html_email = loader.render_to_string(email_template, context)
        return html_email


    def __is_comment_interview(self, role_id, user_id, interviewers):
        if role_id in (1, 2, "1", "2"):
            return True
        if user_id in interviewers:
            return True
        return False

    def get_meeting_link_employees(self, request):
        response = {'employee_list': []}
        try:
            active_users = UserDA().get_all_active_users()
            for each in active_users:
                response["employee_list"].append({'id':each.id, 'label': each.first_name+' '+each.last_name})
        except Exception as error:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(error, self.__log.error(self.__exception.get_exception()))
            response['status'] = 499
        return response


