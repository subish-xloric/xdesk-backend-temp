import os
import base64
from io import BytesIO
import time
import qrcode
import uuid
import pyotp
import urllib
from PIL import Image
from datetime import timedelta
from datetime import date
from datetime import datetime

from django.conf import settings
from rest_framework import permissions
from cryptography.fernet import Fernet

from pTracker.dataaccess.ptracker_access.user_da import UserDA
from pTracker.dataaccess.ptracker_access.holiday_da import HolidayDA




class Utility():

    def __init__(self):
        pass

    def get_all_devices(self):
        str_sql =  """SELECT * FROM Devices
        WHERE SerialNumber IS NOT NULL AND IpAddress"""

    def log(self, msg):
        print(msg)

    def create_date_time(self, str_date, str_time):
        date_string = str_date + " "  + str_time
        log_time = datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S")
        return log_time

    def convert_string_to_date_time(self, date_string, format="%Y-%m-%d %H:%M:%S"):
        try:
            log_time = datetime.strptime(str(date_string), format)
        except:
            log_time = None
        return log_time

    def time_diff_in_seconds(self, dt1, dt2):
        timedelta = dt2 - dt1
        return timedelta.days * 24 * 3600 + timedelta.seconds

    def split_time_from_date_time(self, str_date):
        str_time = None
        try:
            str_time = str(str_date).strip()
            str_time = str_time.split(" ")[1]
        except Exception as err:
            msg = "Error at split_time_from_date_time, Error: {0}".format(err)
            self.log(msg)
        return str_time

    def seconds_converter(self, seconds, format="%H:%M"):
        return time.strftime(format, time.gmtime(seconds))

    def convert_seconds_to_hour_and_minute(self, seconds, format="%H:%M"):
        return time.strftime(format, time.gmtime(seconds))

    def seconds_to_hour_and_minute(self, seconds):
        hrs = seconds // 3600
        mins = (seconds % 3600) // 60
        if len(str(hrs)) == 1:
            hrs = "0"+ str(hrs)
        if len(str(mins)) == 1:
            mins = "0"+ str(mins)

        return str(hrs) + ":" + str(mins)



    def convert_date_time_to_string(self, obj_date, format="%d/%m/%Y"):
        str_date = obj_date.strftime(format)
        return str_date

    def company_punch_in_time(self, str_date):
        punctual_time = PUNCH_IN_CONFIG['punctual']['end_time']
        return self.create_date_time(str_date, punctual_time)

    def get_all_weekends(self, start_date, end_date):
        week_ends = []
        current_day = start_date
        while True:
            if current_day.weekday() in (5, 6):
                week_ends.append(current_day)
            if current_day >= end_date:
                break
            current_day = current_day + timedelta(days=1)
        return week_ends


    def get_first_day_of_month(self, dt=None, d_years=0, d_months=0):
        # d_years, d_months are "deltas" to apply to dt
        if dt:
            y, m = dt.year + d_years, dt.month + d_months
            a, m = divmod(m-1, 12)
            return date(y + a, m + 1, 1)
        else:
            return date(d_years, d_months, 1)


    def get_last_day_of_month(self, dt):
        return self.get_first_day_of_month(dt, 0, 1) + timedelta(-1)

    def get_audit_logs_dict(self):
        log_data = {}
        log_data['user_id'] = 0
        log_data['organization_id'] = 0
        log_data['event'] = ''
        log_data['event_details'] = ''
        return log_data

    def qrcode_generator(self, secret_key, email, issuer="DM Desk", width=225, height=225):
        totp = pyotp.TOTP(secret_key)
        key="otpauth://totp/{0}:{1}?secret={2}&issuer={0}".format(issuer, email, secret_key)
        key = key.replace(" ", "%20")
        key = key.replace("@", "%40")
        obj_qr=qrcode.make(key)
        resized_im = obj_qr.resize((width,height))
        return resized_im

    def verify_time_based_otp(self, secret_key, token):
        totp = pyotp.TOTP(secret_key)
        return totp.verify(token)

    def is_permitted(self, user_id, permission_code):
        """
        This is a common function don't modify or delete
        """
        permitted = False
        permission = UserDA().get_group_permission(user_id, permission_code)
        if permission:
            permitted = True
        else:
            permission = UserDA().get_user_permission(user_id, permission_code)
            if permission:
                permitted = True
        return permitted

    def get_week_days(self,start,end):
        weekdays=[]
        sunday=start+timedelta(days = 6 - start.weekday())  # First Sunday
        saturday=start+timedelta(days = 5 - start.weekday())#first saturday
        while sunday <= end:
            weekdays.append(sunday.strftime("%Y-%m-%d"))
            sunday += timedelta(days = 7)
        while saturday<= end:
            weekdays.append(saturday.strftime("%Y-%m-%d"))
            saturday +=timedelta(days=7)
        return weekdays

    def get_date_range(self, start, end):
        try:
            date_list = []
            delta = end - start
            for i in range(delta.days + 1):
                current_date = start + timedelta(days=i)
                date_list.append(datetime.strptime(
                    current_date.strftime("%Y-%m-%d"), "%Y-%m-%d"))
        except Exception as err:
            date_list = []
        return date_list

    def get_next_n_working_days(self, num=1):
        start_date = date.today()
        off_days = HolidayDA().get_holidays(start_date, start_date+timedelta(days=366))
        week_ends = self.get_all_weekends(start_date, start_date+timedelta(days=366))
        day_count = 0
        day_list = []
        for days in (start_date + timedelta(n) for n in range(366)):
            res = days
            for each in off_days:
                if days == each.holiday_date:
                    res = None
                    continue
            for each in week_ends:
                if days == each:
                    res = None
                    continue
            if res:
                day_count += 1
                day_list.append(days)
                if day_count == num:
                    break
        return day_list

    def utc2local(self):
        return datetime.now() + timedelta(hours=5, minutes=30)

    def get_organization_logo_as_image(self, organization_id):
        logo_images = BytesIO()
        if organization_id == 2:
            logo = Image.open(os.path.join(settings.MEDIA_ROOT, f'logo/DMlogo.png'))
            logo.save(logo_images, format='png')
        else:
            logo = Image.open(os.path.join(settings.MEDIA_ROOT, f'logo/EMlogo.png'))
            logo.save(logo_images, format='png')
        return logo_images

    def date_after_n_working_days(self,num,request_date):

        start_date = request_date.date()
        off_days = HolidayDA().get_holidays(start_date, start_date+timedelta(days=366))
        week_ends = self.get_all_weekends(start_date, start_date+timedelta(days=366))
        day_count = 0
        day_list = []
        for days in (start_date + timedelta(n) for n in range(366)):
            res = days
            for each in off_days:
                if days == each.holiday_date:
                    res = None
                    continue
            for each in week_ends:
                if days == each:
                    res = None
                    continue
            if res:
                day_count += 1
                day_list.append(days)
                if day_count == num:
                    break
        return day_list

    def cutomPageLimits(self, page=1, entries_per_page=settings.DEFAULT_PAGE_LIMIT):
        min = page*entries_per_page - entries_per_page
        max = page*entries_per_page
        return min, max

    def get_organization_name(self, organization_id):
        company_name = ''
        if organization_id == 2:
            company_name = "Digitalmesh"
        else:
            company_name = "EM Softech"
        return company_name

    def get_designation_of_employee(self, emp_id):
        try:
            profile = UserDA().get_user_profile_by_id(emp_id)
            designation = UserDA().get_job_title_by_id(profile.job_title).job_title
        except:
            designation = ''
        return designation


    def decrypt_ctc_amount(self, amount):
        try:
            cipher_suite = Fernet(settings.FERNET_KEY)
            encrypted_value = base64.b64decode(amount.encode('utf-8'))
            decrypted_amount = cipher_suite.decrypt(encrypted_value)
            decrypted_amount = decrypted_amount.decode('utf-8')
            decrypted_amount = float(decrypted_amount)
        except Exception as err:
            #err_msg = settings.ERROR_MSG['application_error'].format(str(err), self.__log.error(self.__exception.get_exception()))
            decrypted_amount = -1

        return decrypted_amount



















