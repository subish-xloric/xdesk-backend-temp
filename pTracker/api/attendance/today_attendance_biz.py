
import math
import time
from  datetime import datetime, date, timedelta
from django.conf import settings
from types import SimpleNamespace
from pTracker.api import attendance

from pTracker.common.utility import Utility
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.common.logs import Logs
from pTracker.dataaccess.ptracker_access.project_da import  ProjectDA

from pTracker.dataaccess.essl_access.attendance import  AttendanceDA
from pTracker.user_management.holiday_da import HolidayDA
from pTracker.api.attendance.attendance_biz import AttendanceBL
from pTracker.api.attendance.mapping_biz import UserMappingBL
from pTracker.user_management.employee import Employee
from pTracker.dataaccess.ptracker_access.attendance import AttendanceDA as pAttendanceDA


def new_dto():
	dto = SimpleNamespace()
	return dto


class TodayAttendanceBL():

	def __init__(self):
		self.__log = Logs()
		self.__exception = ExceptionHandler()
	
	def get_today_attendance_detail_stats(self):
		pass

	def get_today_attendance_detail_filter_stats(self, date):
		pass

	def get_today_attendance_details(self, data, user_id):
		result = {"error": None, "detail_items": None, 'summary':None}
		dto = new_dto()
		dto.date = data.get('date', None)
		try:
			if date:
				attendance_details = self.get_today_attendance_detail_filter_stats(date)
			else:
				attendance_details = self.get_today_attendance_detailr_stats()
			result['summary'] = AttendanceBL().get_today_attendance_stats(user_id) # Get today attendance stats
			return result
		except Exception as err:
			result['error'] = err
			return result
			
