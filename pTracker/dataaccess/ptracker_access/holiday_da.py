from datetime import date, timedelta,datetime
from django.conf import settings

from types import SimpleNamespace

from pTracker.dataaccess.db import Connection
# from pTracker.common.utility import Utility
from pTracker.dataaccess.ptracker_access.models import Holidays
from pTracker.dataaccess.ptracker_access.models import AdditionalWorkingDays




def new_dto():
    dto = SimpleNamespace()
    return dto


class HolidayDA():

    def __init__(self):
        pass

    def get_holidays(self, str_date, end_date):
        return Holidays.objects.filter(deleted=0, holiday_date__range=[str_date, end_date])

    def get_additional_working_days(self, str_date, end_date):
        return AdditionalWorkingDays.objects.filter(deleted=0, working_date__range=[str_date, end_date])

    def get_holiday_by_date(self, start_date):
        return Holidays.objects.filter(deleted=0, holiday_date=start_date)
    
    def get_holiday_dates_only(self, str_date, end_date):
        return Holidays.objects.filter(deleted=0, holiday_date__range=[str_date, end_date]).values_list('holiday_date', flat=True)


