import datetime
import email

from django.conf import settings
from django.db import  transaction
from types import SimpleNamespace
from django.template import loader

from pTracker.common.logs import Logs
from pTracker.common.utility import Utility
from pTracker.common.exception_handler import ExceptionHandler

from pTracker.dataaccess.ptracker_access.interview_da import InterviewDA
from pTracker.dataaccess.ptracker_access.user_da import UserDA
from pTracker.cronjobs.email_sender import send_email_notification
from pTracker.cronjobs.career_opening_updation import career_opening_updataion

def new_dto():
    dto = SimpleNamespace()
    return dto



class InterviewScoreCardBL():

    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()
        self.__utility = Utility()

    def __is_create_scorecard(self, role_id, user_id, interviewers):
        if role_id in (1, 2, "1", "2"):
            return True
        if user_id in interviewers:
            return True
        return False


    def get_all_user_dict(self):
        user_dict = {}
        active_users = UserDA().get_all_active_users()
        for user in active_users:
            user_name = user.first_name + " " + user.last_name
            user_dict[user.id] = user_name
        return user_dict
    
    def get_all_users(self):
        user_dict = {}
        aLL_users = UserDA().get_all_users()
        for user in aLL_users:
            user_name = user.first_name + " " + user.last_name
            user_dict[user.id] = user_name
        return user_dict

    def __get_action_text(self, creator_name, candidate_name, interview_code_name):
        action_text = ''
        created_date = datetime.datetime.now().strftime("%d/%m/%y %H:%I %p")
        action_text = f"""Score card is created for the interview ({interview_code_name}), created by {creator_name}"""
        action_text = action_text + " at " + created_date
        return action_text


    def __create_candidate_log(self, user, candidate, interview):
        obj_da = InterviewDA()
        log_dict = {}
        candidate_name = candidate.first_name + " " + " " + candidate.last_name
        creator_name = user.first_name + " " + user.last_name
        interview_code_name = interview.interview_code
        action_text = self.__get_action_text(creator_name, candidate_name, interview_code_name)
        log_data = {}
        log_data['candidate_id'] = candidate.candidate_id
        log_data['action'] = action_text
        log_data['created_by'] = user.id
        InterviewDA().create_candidate_log(log_data)

        #Create log for interview
        log_dict = {}
        log_dict['interview_id'] = interview.interview_id
        log_dict['action'] = action_text
        obj_da.create_interview_log(log_dict)

    def generate_scorecard_by_interview(self, user, interview_id):
        """
        scorecard {
            candidate :{"candidateID":123, "name":"subsih", "mobile":"9934", "email":"sdsds", "positionName":"343434","interviewRound":"Technical Round 1"}
            skills: [
                {"id":1,"skill":"PHP","skillType":"Soft Skill"},
                {"id":1,"skill":"Python","skillType":"Technical Skill"}
            ]
        }
        """
        obj_da = InterviewDA()
        response = {'error' : '', 'success' : '', 'status' : 200, 'scorecard':{}}
        interviewers = []
        try:
            user_id = user.id
            role_id, role_name = UserDA().get_user_role_by_id(user_id)


            interview = obj_da.get_interview(interview_id)

            if not interview:
                response['error'] = "Invalid interview ID."
                response['status'] = 499
                return response

            temp_interviewers = interview.interviewer.split(',')
            for each in temp_interviewers:
                interviewers.append(int(each))

            is_view = self.__is_create_scorecard(role_id, user_id, interviewers)
            if not is_view:
                response['error'] = settings.ERROR_MSG['access_denied']
                response['status'] = 403
                return response

            candidate = obj_da.get_candidate_by_id(interview.candidate_id)
            if not candidate:
                response['error'] = "No candidate found for this interview."
                response['status'] = 499
                return response

            career_opening = obj_da.get_career_opening(candidate.career_opening_id)
            if not career_opening:
                response['error'] = "No career opening found for this interview."
                response['status'] = 499
                return response



            candidate_dict = {
                "candidateID": candidate.candidate_id,
                "name": candidate.first_name + " " + candidate.last_name,
                "mobile": candidate.mobile,
                "email": candidate.email,
                "positionName":career_opening.position_name,
                "candidateStatus" : settings.CANDIDATE_STATUS.get(candidate.candidate_status, '-'),
                "interviewRound" : interview.interview_code
            }

            skill_id=1
            skills = []
            ''' Listing skills based on interview round '''
            if interview.interview_code=='HR Round':
                hr_round_skills = settings.HR_INTERVIEW_SKILLS
                for skill in hr_round_skills:
                    skills.append({'id':skill_id, "skill":skill[1], "skillType":"Soft Skill"})
                    skill_id+=1

            elif interview.interview_code=='Final Round':
                final_round_skills = settings.FINAL_ROUND_INTERVIEW_SKILLS
                for skill in final_round_skills:
                    skills.append({'id':skill_id, "skill":skill[1], "skillType":"Soft Skill"})
                    skill_id+=1

            elif str(interview.interview_code).upper()=='MACHINE TEST':
                coding_skills = settings.MACHINE_TEST_SKILLS
                for skill in coding_skills:
                    skills.append({'id':skill_id, "skill":skill[1], "skillType":"Technical Skill"})
                    skill_id+=1

            else:
                soft_skills = career_opening.soft_skill.strip('][').replace("'","")
                soft_skills = soft_skills.split(",")
                if soft_skills:
                    for skill in soft_skills:
                        skills.append({"id":skill_id, "skill":skill, "skillType":"Soft Skill"})
                        skill_id+=1

                technical_skills = career_opening.technical_skill.strip('][').replace("'","")
                technical_skills = technical_skills.split(",")
                if technical_skills:
                    for skill in technical_skills:
                        skills.append({"id":skill_id,"skill":skill, "skillType":"Technical Skill"})
                        skill_id+=1

            response['scorecard'] = {
                "candidate": candidate_dict,
                "skills": skills
            }
            return response

        except Exception as error:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(error, self.__log.error(self.__exception.get_exception()))
            response['status'] = 499
            return response


    def create_interview_score_card(self, user, data):
        obj_da = InterviewDA()
        response = {'error' : '', 'success' : '', 'status' : 200}
        interviewers = []
        interview_status = "unknown"
        scores = []
        try:

            user_id = user.id
            role_id, roleName = UserDA().get_user_role_by_id(user_id)

            #Collect input from form
            interview_id = data.get('interviewID',0)
            interview_result = data.get('interviewResult',0)
            time_taken = data.get('timeTaken',0)
            comment = data.get('comment','')
            skill_scores = data.get('score', None)


            interview = obj_da.get_interview(interview_id)
            if interview:
                interview_status = str(interview.interview_status)
                temp_interviewers = interview.interviewer.split(',')
                for each in temp_interviewers:
                    interviewers.append(int(each))

            if not self.__is_create_scorecard(role_id, user_id, interviewers):
                response['error'] = settings.ERROR_MSG['access_denied']
                response['status'] = 403
                return response

            score_card = obj_da.get_interview_score_card_by_interview_id(interview_id)
            if score_card:
                response['error'] = "Scorecard is already created for this interview."
                response['status'] = 403
                return response

            if interview_status not in (1,"1"):
                response['error'] = "Not able to create scorecard this interview. (Invalid interview status)"
                response['status'] = 403
                return response


            if skill_scores:
                email_dto = new_dto
                interview = obj_da.get_interview(interview_id)
                candidate = obj_da.get_candidate_by_id(interview.candidate_id)
                position = obj_da.get_career_opening_by_id(candidate.career_opening_id)
                email_dto.candidate_name = candidate.first_name+ ' '+ candidate.last_name
                email_dto.candidate_email = candidate.email
                email_dto.candidate_mobile = candidate.mobile
                email_dto.candidate_position = position.position_name
                email_dto.interview_round = interview.interview_code
                email_dto.mode = interview.mode_of_interview
                email_dto.candidate_status = settings.CANDIDATE_STATUS.get(int(interview_result))



                user_dict = self.get_all_user_dict()
                temp_interviewers = interview.interviewer.split(',')
                interviewers = ''
                for each in temp_interviewers:
                    obj_interviewer = user_dict.get(int(each),None)
                    if obj_interviewer:
                        interviewers = interviewers+ obj_interviewer+", "
                if interviewers:
                    email_dto.interviewers =interviewers[:-1]
                else:
                    email_dto.interviewers = '-'
                email_dto.date_and_time = datetime.datetime.now().strftime('%d/%m/%Y , %-I.%M %p')
                email_dto.heading = "Interview Score Card"
                email_dto.emp_name = (user.first_name).capitalize() + ' ' + (user.last_name).capitalize()

                with transaction.atomic():
                    for each_skill in skill_scores:
                        temp_data = {}
                        temp_data['interview_id'] = interview_id
                        temp_data['skill'] = each_skill['skill']
                        temp_data['score'] = int(each_skill['score'])
                        temp_data['created_by'] = user.id
                        if each_skill['note']:
                            temp_data['note'] = each_skill['note']
                        else:
                            temp_data['note'] = '-'
                        temp_data['skill_type'] = each_skill['skillType']
                        obj_da.create_interview_score(temp_data)
                        scores.append(temp_data)
                        del temp_data

                    candidate_status = int(interview_result)
                    interview_result = "Pass"
                    if candidate_status == 3:
                        interview_result = "Failed"
                    email_dto.decision = interview_result
                    email_dto.comment = comment
                    email_dto.time_taken = Utility().convert_seconds_to_hour_and_minute(int(time_taken))

                    obj_da.update_interview(
                        interview_id,
                        {
                            'result':interview_result,
                            'time_taken': int(time_taken),
                            'comment':comment,
                            'interview_status':2, #Interview completed
                        })

                    updated_candidate_id = obj_da.update_candidate(
                        candidate.candidate_id,
                        {'candidate_status':candidate_status}
                    )

                    self.__create_candidate_log(user, candidate, interview)
                    emp_designation = self.__get_user_job_title(user_id)

                    subject = position.position_name + " " + interview.interview_code+" Scorecard - "+ candidate.first_name+ ' '+ candidate.last_name
                    email_dto.scores= scores
                    email_dto.heading = subject
                    email_msg = self.generate_interview_score_card_mail(email_dto)
                    ccaddress = [user.email]
                    to_email = settings.INTERVIEW_DEFAULT_MAIL

                    send_email = self.send_interview_scorecard_email_notification(email_msg, to_email, subject, ccaddress)
                    completed_email = new_dto
                    candidate_name = (candidate.first_name).capitalize()+ ' '+ (candidate.last_name).capitalize()
                    completed_email.heading = f"{ position.position_name} {interview.interview_code} completed" #nnn confirm before committ
                    completed_email.candidate = candidate_name
                    completed_email.interviewer = user.first_name+ ' '+ user.last_name
                    completed_email.emp_name = user.first_name+ ' '+ user.last_name
                    completed_email.emp_email = user.email
                    completed_email.designation = emp_designation
                    completed_email.company_name = settings.COMPANY_NAME_FOR_INTERVIEW_MAIL
                    interview_completion_msg = self.generate_interview_completion_mail(completed_email)
                    ccaddress1 = []
                    ccaddress1.append(user.email)
                    ccaddress1.append(settings.INTERVIEW_DEFAULT_MAIL)
                    to_email = candidate.email
                    subject1 = position.position_name + " " + interview.interview_code+" Completed - "+ candidate.first_name+ ' '+ candidate.last_name
                    send_email = self.send_interview_completion_email_notification(interview_completion_msg, to_email, subject1, ccaddress1)
                career_id = candidate.career_opening_id
                career_opening_updataion.apply_async([career_id], queue=settings.CELERY_QUEUE['daily_report'])

            #TODO Send result mail

            # for each in interviewerCC:
            #      ccaddress.append(each.email)
            # to_email = settings.HR_EMAIL
            # text = f"Interview result for the role of {positionName}"
            # mailDict['positionName'] = positionName
            # mailDict['candidateName'] = candidateName
            # mailDict['interviewCode'] = interviewCode
            # mailDict['status'] = status
            # mailDict['heading'] = text
            # subject = text
            # email_msg = self.generate_interview_result_mail(mailDict)
            # send_email = self.send_interview_invitation_email_notification(email_msg, to_email, subject, ccaddress)
            response['success'] = "Scorecard updated successfully"
            return response

        except Exception as error:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(error, self.__log.error(self.__exception.get_exception()))
            response['status'] = 499
            return response

    def get_interview_scorecard_by_candidate(self, user, candidate_id):
        """
        scorecard {
            candidate :{"candidateID":123, "name":"subsih", "mobile":"9934", "email":"sdsds", "positionName":"343434", "status":"Interview scheduled"}
            interviews: [
                {
                    "interview_code":"Round 1",
                    "interviewers":"Subish, Bijith",
                    "date_and_time": "25/08/2022 9.30 AM",
                    "mode_of_interview": "Online",
                    "interview_result" : "pass",
                    "skills": [
                        {"id":1,"skill":"PHP","skillType":"Soft Skill", "score":3, "note":"super"},
                        {"id":1,"skill":"Python","skillType":"Technical Skill", "score":3, "note":"super"}
                    ]
                },
                {
                    "interview_code":"Round 2",
                    "interviewers":"Subish",
                    "date_and_time": "26/08/2022 9.30 AM",
                    "mode_of_interview": "F2F"
                    "skills": [
                        {"id":1,"skill":"PHP","skillType":"Soft Skill", "score":3, "note":"super"},
                        {"id":1,"skill":"Python","skillType":"Technical Skill", "score":3, "note":"super"}
                    ]
                }
            ]
        }
        """
        obj_da = InterviewDA()
        obj_user = UserDA()
        score_cards = {}
        temp_dict = {}
        candidate_dict = {}
        interview_lst = []
        interview_id_lst = []

        response = {'error' : '', 'success' : '', 'status' : 200}
        try:
            candidate = obj_da.get_candidate_by_id(candidate_id)
            if not candidate:
                response['error'] = "No candidate found."
                response['status'] = 499
                return response

            interviews = obj_da.get_interview(0, candidate_id)
            if not interviews:
                response['error'] = "No interviews completed for this candidate id."
                response['status'] = 499
                return response

            for interview in interviews:
                interview_id_lst.append(interview.interview_id)


            position = obj_da.get_career_opening(candidate.career_opening_id)
            if position:
                position_name = position.position_name
            else:
                position_name = " "


            score_card_data = obj_da.get_interview_score_card_by_interview_id(interview_id_lst)
            if not score_card_data:
                response['error'] = "No score card found."
                response['status'] = 499
                return response

            ''' To get skills of each interviews completed by a candidate'''
            score_dict = {}
            user_dict = self.get_all_users()
            interview_taken_by_dict = {}
            for score_card in score_card_data:
                if score_card.created_by:
                    interview_taken_by_dict[score_card.interview_id] = user_dict.get(int(score_card.created_by))
                else:
                    interview_taken_by_dict[score_card.interview_id] = '-'
                temp= {'id' : score_card.id, 'skill' : score_card.skill , 'score' : score_card.score,
                        'note' : score_card.note, 'skillType' : score_card.skill_type }
                if score_card.interview_id in score_dict:
                    score_dict[score_card.interview_id].append(temp)
                else:
                    score_dict[score_card.interview_id] = [temp]


            candidate_dict['candidateID'] = candidate_id
            candidate_dict['name'] = candidate.first_name + " " + candidate.last_name
            candidate_dict['mobile'] = candidate.mobile
            candidate_dict['email'] = candidate.email
            candidate_dict['positionName'] = position_name
            candidate_dict['status'] = settings.CANDIDATE_STATUS.get(candidate.candidate_status, '-')



            for interview in interviews:
                temp_interviewers = interview.interviewer.split(',')
                interviewers = []
                for each in temp_interviewers:
                    interviewers.append(int(each))

                temp_dict = {}
                temp_dict['interviewID'] = interview.interview_id
                temp_dict['interview_code'] = interview.interview_code
                temp_dict['date_and_time'] = interview.date_and_time.strftime('%d/%m/%Y , %-I.%M %p')
                temp_dict['mode_of_interview'] = interview.mode_of_interview
                temp_dict['interview_result'] = interview.result
                temp_dict['time_taken'] = Utility().convert_seconds_to_hour_and_minute(interview.time_taken)

                temp_dict['comment'] = interview.comment
                temp_dict['interviewers'] = ""
                temp_dict['interviewed_by'] = interview_taken_by_dict.get(interview.interview_id)

                if interviewers:
                    name = ""
                    for interviewer in interviewers:
                        temp={}
                        temp['name'] = user_dict.get(int(interviewer))
                        name = name + temp['name'] + ", "
                        temp_dict['interviewers'] = name[:-2]

                temp_dict['skills'] = score_dict.get(interview.interview_id)
                interview_lst.append(temp_dict)

            score_cards['candidate'] = candidate_dict
            score_cards['interviews'] = interview_lst
            response['scorecard'] = score_cards
            return response
        except Exception as error:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(error, self.__log.error(self.__exception.get_exception()))
            response['status'] = 499
            return response


    def generate_interview_score_card_mail(self, emailDict):
        email_template = 'interview_scorecard_email.html'
        context = {
            "heading": emailDict.heading,
            "candidate_name": emailDict.candidate_name,
            "candidate_email": emailDict.candidate_email,
            "candidate_mobile" : emailDict.candidate_mobile,
            "candidate_position" : emailDict.candidate_position,
            "interview_round": emailDict.interview_round,
            "interviewers" : emailDict.interviewers,
            "date_and_time" : emailDict.date_and_time,
            "mode": emailDict.mode,
            "scores":emailDict.scores,
            "decision": emailDict.decision,
            "candidate_status": emailDict.candidate_status,
            "time_taken": emailDict.time_taken,
            "comment": emailDict.comment,
            "emp_name" : emailDict.emp_name
        }
        html_email = loader.render_to_string(email_template, context)
        return html_email

    def send_interview_scorecard_email_notification(self,email_msg, to_email, subject, ccaddress):
        mail_dto = {}
        mail_dto["subject"] = "{0} ".format(subject)
        mail_dto["from_address"] = settings.EMAIL_ADDRESS['do_not_reply']['name']
        mail_dto["body"] = email_msg
        mail_dto["to_addresses"] = [to_email]
        mail_dto["bcc_address"] =  ccaddress

        mail_dto["smtp_username"] = settings.EMAIL_ADDRESS['do_not_reply']['mailID']
        mail_dto["smtp_password"] = settings.EMAIL_ADDRESS['do_not_reply']['password']
        send_email_notification.apply_async(
            [mail_dto, 1], queue=settings.CELERY_QUEUE['mail_sender'])

    def get_interview_scorecard_by_interview(self, user, interview_id):
        """
        scorecard {
            candidate :{"candidateID":123, "name":"subsih", "mobile":"9934", "email":"sdsds", "positionName":"343434", "status":"Interview scheduled"}
            interviews: [
                {
                    "interview_code":"Round 1",
                    "interviewers":"Subish, Bijith",
                    "date_and_time": "25/08/2022 9.30 AM",
                    "mode_of_interview": "Online",
                    "interview_result" : "pass",
                    "skills": [
                        {"id":1,"skill":"PHP","skillType":"Soft Skill", "score":3, "note":"super"},
                        {"id":1,"skill":"Python","skillType":"Technical Skill", "score":3, "note":"super"}
                    ]
                },

            ]
        }
        """
        obj_da = InterviewDA()
        obj_user = UserDA()
        score_cards = {}
        temp_dict = {}
        candidate_dict = {}
        interview_lst = []
        interview_id_lst = []

        response = {'error' : '', 'success' : '', 'status' : 200}
        try:

            interview = obj_da.get_interview(interview_id)
            if not interview:
                response['error'] = "No interview found."
                response['status'] = 499
                return response

            candidate_id = int(interview.candidate_id)
            candidate = obj_da.get_candidate_by_id(candidate_id)
            if not candidate:
                response['error'] = "No candidate found."
                response['status'] = 499
                return response

            # interviews = obj_da.get_interview(0, candidate_id)
            # if not interviews:
            #     response['error'] = "No interviews completed for this candidate id."
            #     response['status'] = 499
            #     return response

            #for interview in interviews:
            interview_id_lst.append(interview_id)
            position = obj_da.get_career_opening(candidate.career_opening_id)
            if position:
                position_name = position.position_name
            else:
                position_name = " "
            user_dict = self.get_all_user_dict()
            score_card_data = obj_da.get_interview_score_card_by_interview_id(interview_id_lst)
            if not score_card_data:
                response['error'] = "No score card found."
                response['status'] = 499
                return response

            ''' To get skills of each interviews completed by a candidate'''
            score_dict = {}
            interview_taken_by_dict = {}
            for score_card in score_card_data:
                if score_card.created_by:
                    interview_taken_by_dict[score_card.interview_id] = user_dict.get(int(score_card.created_by))
                else:
                    interview_taken_by_dict[score_card.interview_id] = '-'
                temp= {
                    'id': score_card.id,
                    'skill': score_card.skill,
                    'score': score_card.score,
                    'note': score_card.note,
                    'skillType': score_card.skill_type
                }
                if score_card.interview_id in score_dict:
                    score_dict[score_card.interview_id].append(temp)
                else:
                    score_dict[score_card.interview_id] = [temp]

            candidate_dict['candidateID'] = candidate_id
            candidate_dict['name'] = candidate.first_name + " " + candidate.last_name
            candidate_dict['mobile'] = candidate.mobile
            candidate_dict['email'] = candidate.email
            candidate_dict['positionName'] = position_name
            candidate_dict['status'] = settings.CANDIDATE_STATUS.get(candidate.candidate_status, '-')

            user_dict = self.get_all_user_dict()

            #for interview in interviews:
            temp_interviewers = interview.interviewer.split(',')
            interviewers = []
            for each in temp_interviewers:
                interviewers.append(int(each))

            temp_dict = {}
            temp_dict['interviewID'] = interview.interview_id
            temp_dict['interview_code'] = interview.interview_code
            temp_dict['date_and_time'] = interview.date_and_time.strftime('%d/%m/%Y , %-I.%M %p')
            temp_dict['mode_of_interview'] = interview.mode_of_interview
            temp_dict['interview_result'] = interview.result
            temp_dict['time_taken'] = Utility().convert_seconds_to_hour_and_minute(interview.time_taken)
            temp_dict['comment'] = interview.comment
            temp_dict['interviewers'] = ""
            temp_dict['interview_taken_by'] = interview_taken_by_dict.get(interview.interview_id)

            if interviewers:
                name = ""
                for interviewer in interviewers:
                    temp={}
                    temp['name'] = user_dict.get(int(interviewer))
                    name = name + temp['name'] + ", "
                    temp_dict['interviewers'] = name[:-2]

            temp_dict['skills'] = score_dict.get(interview.interview_id)
            interview_lst.append(temp_dict)

            score_cards['candidate'] = candidate_dict
            score_cards['interviews'] = interview_lst
            response['scorecard'] = score_cards
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

    def generate_interview_completion_mail(self, emailDict):
        email_template = 'interview_completed_confirmation_mail.html'
        context = {
            "heading": emailDict.heading,
            "candidate": emailDict.candidate,
            "interviewer": emailDict.interviewer,
            "emp_name" : emailDict.emp_name,
            "emp_email": emailDict.emp_email,
            "designation":emailDict.designation,
            "company_name": emailDict.company_name
        }
        html_email = loader.render_to_string(email_template, context)
        return html_email

    def send_interview_completion_email_notification(self,email_msg, to_email, subject, ccaddress):
        mail_dto = {}
        mail_dto["subject"] = "{0} ".format(subject)
        mail_dto["from_address"] = settings.EMAIL_ADDRESS['do_not_reply']['name']
        mail_dto["body"] = email_msg
        mail_dto["to_addresses"] = [to_email]
        # mail_dto["cc_addresses"] =  ccaddress
        mail_dto["bcc_address"] =  ccaddress

        mail_dto["smtp_username"] = settings.EMAIL_ADDRESS['do_not_reply']['mailID']
        mail_dto["smtp_password"] = settings.EMAIL_ADDRESS['do_not_reply']['password']
        send_email_notification.apply_async(
            [mail_dto, 1], queue=settings.CELERY_QUEUE['mail_sender'])


