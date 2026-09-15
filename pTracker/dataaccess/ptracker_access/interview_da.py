from datetime import timedelta

from django.db.models import Q
from django.db import models
from django.contrib.auth.models import User

from pTracker.dataaccess.ptracker_access.interview_model import CareerOpening
from pTracker.dataaccess.ptracker_access.interview_model import Candidate
from pTracker.dataaccess.ptracker_access.interview_model import Interview
from pTracker.dataaccess.ptracker_access.interview_model import InterviewScoreCard
from pTracker.dataaccess.ptracker_access.interview_model import SoftSkills
from pTracker.dataaccess.ptracker_access.interview_model import TechnicalSkills
from pTracker.dataaccess.ptracker_access.interview_model import InterviewLogs
from pTracker.dataaccess.ptracker_access.interview_model import CandidateLogs
from pTracker.dataaccess.ptracker_access.interview_model import InterviewComments
from pTracker.dataaccess.ptracker_access.interview_model import CandidateInformationSheet
from pTracker.dataaccess.ptracker_access.interview_model import InterviewRoundMailStatus



class InterviewDA():

    def __init__(self):
        pass

    """ CareerOpening Model """

    def create_career_opening(self, career_data):
        return CareerOpening.objects.create(**career_data)

    def update_career_opening(self, careerID, career_data):
        return CareerOpening.objects.filter(career_opening_id=careerID).update(**career_data)

    def get_career_opening_by_id(self, career_opening_id):
            obj_opening = CareerOpening.objects.filter(career_opening_id=career_opening_id, is_deleted=0)
            if obj_opening:
                return obj_opening [0]
            else:
                return None

    def get_career_opening(self, careerID=0):
        if careerID:
            return CareerOpening.objects.filter(career_opening_id=careerID,is_deleted=0).first()
        else:
            return CareerOpening.objects.filter(is_deleted=0)

    def get_career_opening_by_year(self, year, status=-1):
        if status == 0:
            return CareerOpening.objects.filter(created_date__year=year, status=0, is_deleted=0).order_by("-career_opening_id")
        elif status == 1:
            return CareerOpening.objects.filter(created_date__year=year, status=1, is_deleted=0).order_by("-career_opening_id")
        else:
            return CareerOpening.objects.filter(created_date__year=year,is_deleted=0).order_by("-career_opening_id")


    def get_all_career_opening(self, status=-1):
        if status == 0:
            return CareerOpening.objects.filter(status=0, is_deleted=0).order_by("-career_opening_id")
        elif status == 1:
            return CareerOpening.objects.filter(status=1, is_deleted=0).order_by("-career_opening_id")
        else:
            return CareerOpening.objects.filter(is_deleted=0).order_by("-career_opening_id")


    def get_career_opening_between_time_period(self, start_date, end_date):
        return CareerOpening.objects.filter(Q(created_date__lt=end_date) & Q(deleted_date__gt=start_date), is_deleted=0)


    def get_career_opened(self, careerID=0):
        if careerID:
            return CareerOpening.objects.filter(career_opening_id=careerID, status=1, is_deleted=0).first()
        else:
            return CareerOpening.objects.filter(status=1, is_deleted=0)

    def get_career_openings_by_ids(self, career_opening_ids=[]):
        return CareerOpening.objects.filter(career_opening_id__in=career_opening_ids, is_deleted=0)

    def delete_career_opening(self,careerID):
        return CareerOpening.objects.filter(career_opening_id=careerID).update(is_deleted=1)


    def get_leads_career_opening(self, lead_id):
        return CareerOpening.objects.filter(lead_interviewer = lead_id, is_deleted=0)

    """ Candidate Model """
    def create_candidate(self, candidate_data):
        return Candidate.objects.create(**candidate_data)

    def update_candidate(self, candidate_id, candidate_data):
        return Candidate.objects.filter(candidate_id=candidate_id).update(**candidate_data)

    def get_candidate_by_id(self, candidate_id):
        return Candidate.objects.filter(candidate_id=candidate_id, is_deleted=0).first()


    def get_candidates(self, candidateID=0):
        if candidateID:
            return Candidate.objects.filter(candidate_id=candidateID, is_deleted=0).first()
        else:
            return Candidate.objects.filter(is_deleted=0)


    def get_candidate_by_career_opening_id(self, careerID):
        return Candidate.objects.filter(Q(candidate_status=2), career_opening_id=careerID, is_deleted=0)

    def get_candidates_by_ids(self, candidate_ids):
        return Candidate.objects.filter(candidate_id__in=candidate_ids)

    def delete_candidate(self, candidateID):
        return Candidate.objects.filter(candidateID=candidateID).update(is_deleted=1)

    # def get_candidate_by_name_email_phone(self, filterData):
    #     return Candidate.objects.filter(Q(name__icontains=filterData) | Q(email__icontains=filterData) | Q(mobile__icontains=filterData))

    def check_candidate_time_range(self, first_name, last_name, email, start_date, end_date):
        return Candidate.objects.filter(Q(first_name__icontains=first_name) & Q(last_name__icontains=last_name) |Q(email=email), created_date__date__gte=start_date, created_date__date__lte=end_date, is_deleted=0).exists()

    def get_candidate_by_opening_id(self, careerID):
        if type(careerID) == list:
            return Candidate.objects.filter(career_opening_id__in=careerID, is_deleted=0)
        else :
            return Candidate.objects.filter(career_opening_id=careerID, is_deleted=0)

    def check_candidate_email_or_phone(self, email, mobile, candidate_id=0):
        if not candidate_id:
            return Candidate.objects.filter(Q(email=email) | Q(mobile=mobile), is_deleted=0).exists()
        else:
            return Candidate.objects.filter(Q(email=email) | Q(mobile=mobile), ~Q(candidate_id=candidate_id), is_deleted=0).exists()


    """ Interview Model """
    def create_interview(self, data):
        return Interview.objects.create(**data)

    def update_interview(self, interview_id, data):
        return Interview.objects.filter(interview_id=interview_id).update(**data)

    def update_interview_status(self, interviewID, result, timeTaken):
        return Interview.objects.filter(interviewID=interviewID).update(interviewStatus=0, result=result, timeTaken=timeTaken)
    

    def update_interview_link(self, interview_id, meeting_link):
        return Interview.objects.filter(interview_id=interview_id).update(meeting_link=meeting_link)


    def get_interview(self, interviewID, candidate_id=0):
        if candidate_id:
            return Interview.objects.filter(candidate_id=candidate_id, interview_status=2, is_deleted=0)
        else:
            return Interview.objects.filter(interview_id=interviewID, is_deleted=0).first()


    def get_interviews_of_a_time_period(self, start_date_time, end_date_time):
        return Interview.objects.filter(Q(date_and_time__gt=start_date_time) & Q(date_and_time__lte=end_date_time), is_deleted=0)

    
    def get_all_interviews_by_year(self, year, status=0):
        if status:
            return Interview.objects.filter(date_and_time__year=year, interview_status=status, is_deleted=0).order_by('-interview_id')
        else:
            return Interview.objects.filter(date_and_time__year=year, is_deleted=0).order_by('-interview_id')

    def get_all_interviews_by_date_range(self, start_date, end_date, status=0):
        if status:
            return Interview.objects.filter(date_and_time__gte=start_date, date_and_time__lte=end_date, interview_status=status, is_deleted=0).order_by('-interview_id')
        else:
            return Interview.objects.filter(date_and_time__gte=start_date, date_and_time__lte=end_date, is_deleted=0).order_by('-interview_id')

    def get_all_active_interviews(self):
        return Interview.objects.filter(interview_status=1, is_deleted=0)


    def get_scheduled_interview_by_candidate(self, candidate_ids):
        if type(candidate_ids) == list:
            return Interview.objects.filter(interview_status=1,candidate_id__in=candidate_ids, is_deleted=0)
        else:
            return Interview.objects.filter(interview_status=1,candidate_id=candidate_ids, is_deleted=0)


    """ InterviewScoreCard Model """

    def create_interview_score(self, data):
        return InterviewScoreCard.objects.create(**data)

    # def create_interview_score_card(self, data):
    #     bulkDataLst = []
    #     for eachItem in data:
    #         interviewData = InterviewScoreCard(interview_id=eachItem['interviewID'], skill=eachItem['skill'], score=eachItem['score'],
    #                                             note=eachItem['note'], skill_type=eachItem['skillType']
    #                                             )
    #         bulkDataLst.append(interviewData)
        # return InterviewScoreCard.objects.bulk_create(bulkDataLst)

    def get_interview_score_card_by_interview_id(self, interview_id):
        if type(interview_id)==list:
            return InterviewScoreCard.objects.filter(interview_id__in=interview_id)
        else:
            return InterviewScoreCard.objects.filter(interview_id=interview_id)

    # def update_interview_score_card(self, id, data):
    #     return InterviewScoreCard.objects.filter(id=id).update(**data)


    """ Create SoftSkill Model """

    def create_soft_skills(self, data):
        return SoftSkills.objects.create(**data)

    def update_soft_skills(self, id, data):
        return SoftSkills.objects.filter(id=id).update(**data)

    def get_soft_skills(self):
        return SoftSkills.objects.all()


    """ Create TechnicalSkills Model """

    def create_technical_skills(self, data):
        return TechnicalSkills.objects.create(**data)

    def update_technical_skills(self, id, data):
        return TechnicalSkills.objects.filter(id=id).update(**data)

    def get_technical_skills(self):
        return TechnicalSkills.objects.all()

    """ InterviewLog Model """

    def create_interview_log(self, data):
        return InterviewLogs.objects.create(**data)

    def update_interview_log(self, interviewID, data):
        return InterviewLogs.objects.filter(interviewID=interviewID).update(**data)

    def check_interview_status(self, candidate_id, interview_status):
        return Interview.objects.filter(candidate_id=candidate_id, interview_status=interview_status)


    def get_all_candidates(self, position=0, status=0):
        candidates = Candidate.objects.filter(is_deleted=0).order_by('-candidate_id')
        if position:
            candidates = candidates.filter(career_opening_id=position)
        if status:
            candidates = candidates.filter(candidate_status=status)
        return candidates

    def create_candidate_log(self, data):
        return CandidateLogs.objects.create(**data)

    def get_candidate_logs(self, candidate_id):
        return CandidateLogs.objects.filter(candidate_id=candidate_id).order_by('id')

    def get_interviews_by_candidate(self, candidate_id):
        return Interview.objects.filter(candidate_id=candidate_id, is_deleted=0)


    '''interview comments model'''
    def create_interview_comment(self, data):
        return InterviewComments.objects.create(**data)

    def get_interview_comments_by_interview_id(self, interview_id):
        return InterviewComments.objects.filter(interview_id=interview_id).order_by('-created_date')

    
    '''candidate information sheet model'''

    def create_candidate_information_sheet(self, data):
        return CandidateInformationSheet.objects.create(**data)


    def get_candidate_information_sheet(self, token, status=0):
        result = CandidateInformationSheet.objects.filter(unique_code=token)
        if status:
            result = result.filter(status=status)
        return result.first()

    def update_candidate_information_sheet(self, token, data):
        return CandidateInformationSheet.objects.filter(unique_code=token).update(**data)
    
    def get_candidate_information_sheet_by_candidate_id(self,candidate_id):
        result = CandidateInformationSheet.objects.filter(candidate_id=candidate_id)
        return result.first()
    
    def create_interview_mail_status(self, data):
        return InterviewRoundMailStatus.objects.create(**data)
    
    def get_interview_mail_status(self, interview_id):
        return InterviewRoundMailStatus.objects.filter(interview_id = interview_id).first()
    
    






