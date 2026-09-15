from time import perf_counter
from types import SimpleNamespace

from django.db.models import Q

from pTracker.dataaccess.ptracker_access.appraisal_models import AppraisalBatches, AppraisalCeleryJobLog, AppraisalPeriod
from pTracker.dataaccess.ptracker_access.appraisal_models import AppraisalForm
from pTracker.dataaccess.ptracker_access.appraisal_models import AppraisalLog


def new_dto():
    dto = SimpleNamespace()
    return dto

class AppraisalDA():

    def __init__(self):
        pass

    def get_appraisal_period_by_date(self, year):
        try:
            return AppraisalPeriod.objects.get(year = year)
        except:
            return None

    def create_appraisal_form(self, data):
        return AppraisalForm.objects.create(**data)

    def create_appraisal_log(self, data):
        return AppraisalLog.objects.create(**data)

    def get_appraisal_form_by_token(self, token):
        try:
            return AppraisalForm.objects.get(appraisal_token=token)
        except:
            return None

    def update_appraisal_form(self, appraisal_id, data):
        return AppraisalForm.objects.filter(appraisal_id = appraisal_id).update(**data)

    def get_all_my_appraisal_forms_by_appraisal_period(self, user_id, period_id, role_id):
        if role_id in (1, '1', 2, '2'):
            return AppraisalForm.objects.filter(period_id=period_id)
        return AppraisalForm.objects.filter(Q(employee_id= user_id)|Q(reviewer_id=user_id)|Q(appraiser_id=user_id),period_id=period_id)

    def get_appraisal_entry_by_period(self, period):
        return AppraisalForm.objects.filter( period_id=period)

    def get_all_appraisal_log(self):
        return  AppraisalLog.objects.all()

    def get_appraisal_period_by_id(self, period_id):
        return AppraisalPeriod.objects.get(period_id = period_id)

    def delete_appraisal_form_by_id(self, appraisal_id):
        return  AppraisalForm.objects.filter( appraisal_id=appraisal_id).delete()

    def delete_all_appraisal_celery_job_log(self):
        return AppraisalCeleryJobLog.objects.all().delete()

    def get_all_appraisal_celery_job_log(self):
        return AppraisalCeleryJobLog.objects.all()

    def create_appraisal_celery_job(self, data):
        return AppraisalCeleryJobLog.objects.create(**data)

    def get_all_appraisal_batches(self):
        return AppraisalBatches.objects.filter(is_deleted = 0)

    def get_appraisal_batch_by_id(self, batch_id):
        return AppraisalBatches.objects.filter(batch_id = batch_id)

    def publish_appraisal_normalization_result(self, period_id, batch_id, organization, data, employee_id ):
        print(period_id, batch_id, organization,data )
        return AppraisalForm.objects.filter(period_id = period_id, batch_id = batch_id, \
            organization_id = organization, employee_id=employee_id).update(**data)

    def get_all_appraisal_forms_by_appraisal_period_batch_id_and_organization(self, period_id, batch_id, organization):
        return AppraisalForm.objects.filter\
            (period_id=period_id, batch_id=batch_id, organization_id=organization, is_published=0)

    def get_all_my_appraisal_forms_by_appraisal_period_and_batch_organization(self,period_id, batch_id, organization =0):
        if organization:
            return AppraisalForm.objects.filter(period_id=period_id, organization_id=organization, batch_id=batch_id )
        return AppraisalForm.objects.filter(period_id=period_id, batch_id=batch_id )



