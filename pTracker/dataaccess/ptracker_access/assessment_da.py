
from  datetime import datetime, date, timedelta
from types import SimpleNamespace

from django.conf import settings
from django.db.models import query
from django.db.models import Q

from pTracker.dataaccess.ptracker_access.assessment_models import Assessee
from pTracker.dataaccess.ptracker_access.assessment_models import Assessment
from pTracker.dataaccess.ptracker_access.assessment_models import AssessmentComment
from pTracker.dataaccess.ptracker_access.assessment_models import AssessmentLog

from pTracker.dataaccess.db import Connection


def new_dto():
    dto = SimpleNamespace()
    return dto

class AssessmentDA():

    def __init__(self):
        pass

    def create_assessee(self, data_dict):
        return Assessee.objects.create(**data_dict)

    def create_assessment(self, data_dict):
        return Assessment.objects.create(**data_dict)

    def create_assessment_comment(self, data_dict):
        return AssessmentComment.objects.create(**data_dict)

    def create_assessment_log(self, data_dict):
        return AssessmentLog.objects.create(**data_dict)

    def update_assessee(self, assessee_id, data_dict):
        assessment = Assessee.objects.filter(emp_id=assessee_id).update(**data_dict)
        return assessment

    def update_assessment(self, assessment_id, data_dict):
        assessment = Assessment.objects.filter(assessment_id=assessment_id).update(**data_dict)
        return assessment

    def get_asessee(self, emp_id=None):
        result = Assessee.objects.all().order_by('-created_date')
        if emp_id and isinstance(emp_id, list):
            result = result.filter(emp_id__in=emp_id)
        elif emp_id:
            result = result.filter(emp_id=emp_id)
        return result

    def get_assessment(self, assessee_id=None):
        result = Assessment.objects.filter(is_deleted=0).order_by('-assessment_id')
        if assessee_id and isinstance(assessee_id, list):
            result = result.filter(emp_id__in=assessee_id)
        elif assessee_id:
            result = result.filter(emp_id=assessee_id)
        return result

    def get_assessment_by_team_ids(self, assessee_ids):
        result = Assessment.objects.filter(is_deleted=0, emp_id__in=assessee_ids).order_by('-assessment_id')
        return result


    def get_assessment_by_id(self, assessment_id=None):
        result = Assessment.objects.filter(is_deleted=0)
        if assessment_id and isinstance(assessment_id, list):result = result.filter(assessment_id__in=assessment_id)
        elif assessment_id:result = result.filter(assessment_id=assessment_id)
        return result

    def get_assessment_logs(self, assessee_id):
        return AssessmentLog.objects.filter(assessee_id=assessee_id)

    def get_assessment_comments(self, assessment_id):
        return AssessmentComment.objects.filter(assessment_id=assessment_id)

    def delete_assessment(self, assessee_id):
        return Assessment.objects.filter(emp_id=assessee_id).delete()

    def delete_assessment_by_id(self, assessment_id):
        return Assessment.objects.filter(assessment_id=assessment_id).delete()

