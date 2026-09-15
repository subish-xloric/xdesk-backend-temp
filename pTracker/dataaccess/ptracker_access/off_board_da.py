import datetime
from types import SimpleNamespace
from django.conf import settings

from django.contrib.auth.models import User
from django.contrib.auth.models import Group

from datetime import datetime, timedelta

from pTracker.dataaccess.db import Connection
from pTracker.common.utility import Utility
from pTracker.dataaccess.ptracker_access.user_models import OffBoardingExitForm, OffBoardingRequest
from pTracker.dataaccess.ptracker_access.user_models import OffBoardingRequestLog
from pTracker.dataaccess.ptracker_access.user_models import OffBoardingDocuments
from pTracker.dataaccess.ptracker_access.user_models import  OffBoardingExitInterviewForm


def new_dto():
    dto = SimpleNamespace()
    return dto


class OffBoardDA():

    def __init__(self):
        pass

    def create_offboard_request(self, off_board_data):
        return OffBoardingRequest.objects.create(**off_board_data)

    def check_eligible(self, user_id):
        result = None
        try:
            result = OffBoardingRequest.objects.filter(user_id=user_id,
                                                       status__in=[settings.OFF_BOARD_REQUEST_STATUS['Pending'],
                                                                   settings.OFF_BOARD_REQUEST_STATUS['Accepted'],
                                                                   settings.OFF_BOARD_REQUEST_STATUS['Initiated'],
                                                                   settings.OFF_BOARD_REQUEST_STATUS['Completed']])
        except:
            pass
        return result

    def create_offboard_request_log(self, off_board_log):
        return OffBoardingRequestLog.objects.create(**off_board_log)

    def update_offboard_request(self, req_id, off_board_data):
        return OffBoardingRequest.objects.filter(id=req_id).update(**off_board_data)

    def get_all_offboarding_requests(self, is_terminated = 0):
        if is_terminated:
            return OffBoardingRequest.objects.filter(is_terminated = is_terminated).order_by('-id')
        else:
            return OffBoardingRequest.objects.all().order_by('-id')

    def get_all_log_list_by_off_board_id(self, off_id):
        return OffBoardingRequestLog.objects.filter(off_boarding_id=off_id)

    def get_offboarding_request_by_id(self, offboard_request_id):
        try:
            return OffBoardingRequest.objects.get(id=offboard_request_id)
        except:
            return None

    def create_off_board_exit_form_data(self, data):
        return OffBoardingExitForm.objects.create(**data)

    def get_off_boarding_exit_form_by_exit_form_id(self, exif_form_id):
        return OffBoardingExitForm.objects.get(off_boarding_code=exif_form_id)

    def update_offboard_exit_form(self, exit_from_code, exit_form):
        obj = OffBoardingExitForm.objects.get(
            off_boarding_code=exit_from_code)
        obj.exit_form_data = exit_form
        obj.save()
        return obj

    def update_off_board_relieve_date(self, off_boarding_id, relieving_date):
        return OffBoardingRequest.objects.filter(id=off_boarding_id).update(relieving_date=relieving_date)

    def upload_relieving_documents(self, data):
        return OffBoardingDocuments.objects.create(**data)

    def is_document_already_uploaded(self, doc_type, off_boarding_id):
        return OffBoardingDocuments.objects.filter(document_name=doc_type, off_boarding_id=off_boarding_id)

    def get_relieving_docs_by_off_boarding_id(self, off_boarding_id):
        return OffBoardingDocuments.objects.filter(off_boarding_id=off_boarding_id)

    def delete_relieving_document(self, document_id):
        return OffBoardingDocuments.objects.filter(id=int(document_id)).delete()

    def get_exit_form_by_user_id_and_off_boarding_id(self, user_id, off_boarding_id):
        return OffBoardingExitForm.objects.filter(off_boarding_id= off_boarding_id, emp_id= user_id )

    def create_exit_interview_form(self,data):
        return OffBoardingExitInterviewForm.objects.create(**data)

    def get_exit_interviewform_by_exit_interview_code(self, exit_intrvw_code):
        return OffBoardingExitInterviewForm.objects.get(exit_interview_code = exit_intrvw_code)

    def update_exit_interview_form_data(self, update_data, exit_interview_form_id ):
        return OffBoardingExitInterviewForm.objects.filter(id = exit_interview_form_id ).update(**update_data)

    def get_exit_interview_form_by_user_id_and_off_boarding_id(self, user_id, off_boarding_id):
        exit_interview_forms =OffBoardingExitInterviewForm.objects.filter(emp_id = user_id, off_boarding_id= off_boarding_id )
        if exit_interview_forms:
            return exit_interview_forms[0]

    def get_filtered_offboarding_requests(self, organization =0, year=0, from_date =0, to_date=0):
        result = OffBoardDA().get_all_offboarding_requests()
        if organization != '0':
            result = result.filter(organization_id=organization)
        if year:
            result = result.filter(request_date__year=year)
        if from_date and to_date:
            obj_from_date = datetime.strptime(from_date, '%Y-%m-%d')
            obj_end_date = datetime.strptime(to_date, '%Y-%m-%d')
            result = result.filter(request_date__gte=obj_from_date)
            result = result.filter(request_date__lte=obj_end_date)
        return result


    def get_all_exit_forms(self):
        return OffBoardingExitForm.objects.all()

    def get_all_exit_interview_forms(self):
        return OffBoardingExitInterviewForm.objects.all()

    def get_all_logs(self):
        return OffBoardingRequestLog.objects.all()

    def get_offboarding_request_by_id(self, offboard_request_id):
        try:
            return OffBoardingRequest.objects.get(id=offboard_request_id)
        except:
            return None

    def validate_termination_process(self, emp_id, status_list=[], is_terminated=0):
        return OffBoardingRequest.objects.filter(user_id=emp_id, status__in=status_list,\
            is_terminated=is_terminated, deleted=0)

    def get_initiated_termination_requests(self):
        return OffBoardingRequest.objects.filter(is_terminated=1,status=settings.OFF_BOARD_REQUEST_STATUS['Initiated']).order_by('-id')

