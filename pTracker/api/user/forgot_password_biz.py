
import secrets
from types import SimpleNamespace

from django.utils import timezone
from django.conf import settings
from django.template import loader
from django.core.mail import EmailMessage
from django.db import DatabaseError, transaction

from pTracker.common.utility import Utility
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.common.logs import Logs

from pTracker.dataaccess.ptracker_access.user_da import UserDA

from pTracker.cronjobs.email_sender import send_email_notification


def new_dto():
    dto = SimpleNamespace()
    return dto


class ResetpasswordBL():
    def __init__(self):
        self.__exception = ExceptionHandler()
        self.__utility = Utility()
        self.__logs = Logs()

    def send_password_reset_notification(self, message, to_email, subject):
        mail_dto = {}
        mail_dto["subject"] = "DM DESK: {0} ".format(subject)
        mail_dto["from_address"] = settings.EMAIL_ADDRESS['do_not_reply']['name']
        mail_dto["body"] = message
        mail_dto["to_addresses"] = [to_email]
        mail_dto["smtp_username"] = settings.EMAIL_ADDRESS['do_not_reply']['mailID']
        mail_dto["smtp_password"] = settings.EMAIL_ADDRESS['do_not_reply']['password']
        # uncomment to send mail TODO
        send_email_notification.apply_async([mail_dto, 1], queue=settings.CELERY_QUEUE['mail_sender'])

    def generate_reset_link(self, request):
        response = {'error': None, 'message': None}
        try:
            email = request.data.get('email')
            user = UserDA().get_user_by_email(email)

            if user:  # get user
                uidb64 = user.id

                # try: # Generating token
                temp_user = UserDA().get_reset_token(email)
                if temp_user:
                    if temp_user.deleted or temp_user.expiry < timezone.now():
                        token = secrets.token_urlsafe(32)
                        data_obj = {'email': email, 'user_id': uidb64, 'req_code': token,
                            'expiry': timezone.now() + timezone.timedelta(minutes=settings.DEFAULT_EXPIRE_TIME)}
                        obj = UserDA().create_reset_password_token(data_obj)
                        temp_user = obj
                    else:
                        token = temp_user.req_code
                else:
                    token = secrets.token_urlsafe(32)
                    data_obj = {'email': email, 'user_id': uidb64, 'req_code': token,
                        'expiry': timezone.now() + timezone.timedelta(minutes=settings.DEFAULT_EXPIRE_TIME)}
                    obj = UserDA().create_reset_password_token(data_obj)
                    temp_user = obj

                absalute_url = settings.BASE_URL+'auth/reset/'
                user_id = str(uidb64)
                link = absalute_url+user_id+"/"+str(token)
                context ={"username": user.first_name + ' ' + user.last_name,\
                    "link": link, "expire": temp_user.expiry, 'domain':settings.BASE_URL
                    }
                message = loader.render_to_string('reset_mail_v1.html',context)
                subject = "Reset Passsword !!!"
                response['message'] = 'We have sent you a link to reset your password'
                self.send_password_reset_notification(message, to_email=user.email, subject=subject)

        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__logs.error(self.__exception.get_exception()))
        return response
    
    def validate_reset_token(self, request):
        response = {'error': None, 'message': None, 'detail': False}
        try:
            token = request.data.get('token')
            user_id = request.data.get('user_id')
            user = UserDA().get_reset_token_by_user_id(user_id, token)
            if user:
                if user.deleted or user.expiry < timezone.now():
                    response['message'] = settings.ERROR_MSG['no_permission']
                    return response
                else:
                    response['user_id'] = request.data.get('user_id')
                    response['detail'] = True
        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__logs.error(self.__exception.get_exception()))
        return response
    
    def set_new_password(self, request):
        response = {'error': None, 'message': ''}
        try:
            user_id = request.data.get('uidb64')
            token = request.data.get('token')
            password = request.data.get('password')
            obj = UserDA().get_reset_token_by_user_id(user_id, token)
            if obj:
                if obj.deleted or obj.expiry < timezone.now():
                    response['message'] = 'Link is expired.'
                    return response
                else:
                    response['message'] = 'Password reset successful.'
                    user = UserDA().reset_user_password(user_id, password, obj.id)
                    return response
            response['message'] = settings.ERROR_MSG['access_denied']
        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__logs.error(self.__exception.get_exception()))
        return response
