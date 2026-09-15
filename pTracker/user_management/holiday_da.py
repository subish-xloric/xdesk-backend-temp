from django.conf import settings

from types import SimpleNamespace

from pTracker.dataaccess.db import Connection
from pTracker.common.utility import Utility
from pTracker.dataaccess.ptracker_access.models import Holidays
from pTracker.dataaccess.ptracker_access.models import AdditionalWorkingDays



def new_dto():
    dto = SimpleNamespace()
    return dto


class HolidayDA():

    def __init__(self):
        pass

    def is_holiday(self, str_date):
        obj = Holidays.objects.filter(deleted=0, holiday_date=str_date)
        if obj:
            return True
        else:
            return False

    def get_all_holidays(self, str_date, end_date):
        objs = Holidays.objects.filter(deleted=0, holiday_date__lte=end_date, holiday_date__gte=str_date)
        return objs

    def get_upcoming_holidays(self, str_date):
        objs = Holidays.objects.filter(deleted=0, holiday_date__gte=str_date, holiday_date__year=str_date.year)
        return objs

    def get_holidays(self, str_date, end_date):
        return Holidays.objects.filter(deleted=0, holiday_date__range=[str_date, end_date])

    def get_additional_working_days(self, str_date, end_date):
        return AdditionalWorkingDays.objects.filter(deleted=0, working_date__range=[str_date, end_date])

    def get_holidays_in_date_list(self, date_list):
        return Holidays.objects.filter(deleted=0, holiday_date__in=date_list)
