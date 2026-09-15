import sys
import traceback

from rest_framework.views import exception_handler

def custom_rest_exception_handler(exc, context):
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)
    try:
        if response is not None:
            response.data['status_code'] = response.status_code
        non_field_errors = response.data.get('non_field_errors', None)
        if non_field_errors and non_field_errors[0].code == "invalid" :
            response.data['error'] = 'Unable to log in with provided credentials.'

        password_errors = response.data.get('password', None)
        if password_errors and password_errors[0].code == "required" :
            response.data['error'] = 'Password field is required.'

        old_password_errors = response.data.get('old_password', None)
        if old_password_errors:
            if old_password_errors[0].code == "invalid":
                response.data['error'] = 'Old password is invalid.'
            if old_password_errors[0].code == "required":
                response.data['error'] = 'Old password is required.'
            elif  old_password_errors[0].code == "blank":
                response.data['error'] = 'Old password cannot be blank.'
            return response

        new_password1_errors = response.data.get('new_password1', None)
        if new_password1_errors:
            if new_password1_errors[0].code == "required":
                response.data['error'] = 'New password is required.'
            elif new_password1_errors[0].code == "blank":
                response.data['error'] = 'New password cannot be blank.'
            return response

        new_password2_errors = response.data.get('new_password2', None)
        if new_password2_errors:
            if new_password2_errors[0].code == "invalid":
                response.data['error'] = new_password2_errors[0]
            if new_password2_errors[0].code == "required":
                response.data['error'] = 'Repeat password is required.'
            elif new_password2_errors[0].code == "blank":
                response.data['error'] = 'Repeat password cannot be blank.'
            return response
    except:
        pass
    finally:
        return response

class ExceptionHandler :

    def __init__(self):
        pass

    def get_exception(self):

        """ Method to track the exception """
        cla, exc, trbk = sys.exc_info()
        excName = cla.__name__

        try:
            excArgs = exc.__dict__["args"]
        except KeyError:
            excArgs = "<no args>"

        excTb = traceback.format_tb(trbk, 8)
        message = '%s %s %s' % (excName, excArgs, excTb)

        return message

