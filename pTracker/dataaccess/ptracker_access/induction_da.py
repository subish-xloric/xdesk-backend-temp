
from  datetime import datetime, date, timedelta
from types import SimpleNamespace

from django.conf import settings
from django.db.models import query
from django.db.models import Q

from django.contrib.auth.models import User
from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission

from pTracker.dataaccess.ptracker_access.induction_models import Induction
from pTracker.dataaccess.ptracker_access.induction_models import InductionDetail
from pTracker.dataaccess.ptracker_access.induction_models import InductionLog


from pTracker.dataaccess.db import Connection

from io import BytesIO
import os

from PIL import Image

def new_dto():
    dto = SimpleNamespace()
    return dto

class InductionDA():

    def __init__(self):
        pass

    def create_induction(self, dataDict):
        return Induction.objects.create(**dataDict)

    def get_induction(self, status=0, induction_id=0, employee_id=0):
        result = Induction.objects.all().order_by('-induction_id')
        if status:
            if isinstance(status, list):result = result.filter(status__in=status)
            else:result = result.filter(status=status)
        if induction_id:
            result = result.filter(induction_id=induction_id)
        if employee_id:
            result = result.filter(emp_id=employee_id)
        return result

    def get_induction_by_induction_id(self, induction_id):
        return Induction.objects.filter(induction_id=induction_id).first()

    def get_induction_by_emp_id(self, emp_id):
        return Induction.objects.filter(emp_id=emp_id)

    def create_induction_log(self, dataDict):
        return InductionLog.objects.create(**dataDict)

    def create_induction_details(self, data_dict):
        return InductionDetail.objects.create(**data_dict)

    def get_induction_details_by_induction_id(self, induction_id=0, status=0, lead_id=0):
        result = InductionDetail.objects.filter(induction_id=induction_id)
        if status:
            result = result.filter(status=status)
        if lead_id:
            result = result.filter(lead_id=lead_id)
        return result

    def update_induction_details(self, induction_id, data_dict, lead_id=0):
        result = InductionDetail.objects.filter(induction_id=induction_id)
        if lead_id: result= result.filter(lead_id=lead_id)
        return result.update(**data_dict)

    def update_induction(self, induction_id, update_dict):
        return Induction.objects.filter(induction_id=induction_id).update(**update_dict)

    def get_induction_logs(self, induction_id):
        return InductionLog.objects.filter(induction_id=induction_id)

    def delete_induction_details_by_induction_id(self, induction_id):
        result = InductionDetail.objects.filter(induction_id=induction_id).delete()
        return result

    def get_induction_details_by_lead_id(self, lead_id=0):
        result = None
        if lead_id:
            result = InductionDetail.objects.filter(lead_id=lead_id)
        return result