from string import Template
from django.template.loader import get_template
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth import authenticate, login
from django.conf import settings
from django.contrib import messages
from pTracker.wiki.common.forms.authentication_form import LoginForm
from pTracker.wiki.common.forms.authentication_form import TwoFactorVerificationForm
from pTracker.wiki.utils.logs import Logs
from pTracker.wiki.utils.exception import ExceptionHandler
from pTracker.common.utility import Utility
from pTracker.wiki.data_access.master.logs_da import LogsDA
from pTracker.wiki.data_access.replica.master_da import MasterDA

from pTracker.api.user.user_management_bl import UserManagementBL


class AuthBL():
    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()
        self.audit_logs = Utility().get_audit_logs_dict()


    def login(self,request):
        try:
            # to redirect to the next url
            if request.method == 'GET':
                request.session['next_url'] = request.GET.get('next')
            form = LoginForm()
            variables = {'form':form}
            template=get_template('auth/login.html')
            if request.method == 'POST':
                form = LoginForm(request.POST)
                if form.is_valid():
                    email = request.POST.get('email', '')
                    password = request.POST.get('password', '')
                    user_name = MasterDA().get_users_username(email)
                    user = authenticate(username=user_name, password=password)
                    if user:
                        is_twofa_on = UserManagementBL().is_user_two_fa_on(email)
                        if is_twofa_on:
                            request.session['email'] = email
                            request.session['password'] = password
                            request.session['user_name'] = user_name
                            request.session['temp_uid'] = user.id
                            URL = request.session['next_url']
                            if URL:
                                return  HttpResponseRedirect('/wiki/accounts/token-challenge/?next=' + URL)
                            else:
                                return redirect('token_challenge')

                        else:
                            login(request,user)
                            request.session['user_group'] = int(user.groups.values_list('id', flat=True).first())
                            self.audit_logs['user_id'] = user.id
                            self.audit_logs['event'] = 'User Login'
                            self.audit_logs['event_details'] =f'User with username {user.username} has logged in.'
                            LogsDA().create_audit_logs(self.audit_logs)
                            URL = request.session['next_url']
                            if URL:
                                return  HttpResponseRedirect(URL)
                            del request.session['next_url']
                            return redirect('home')
                    else:
                       messages.error(request,'Invalid Username or password')
                else:
                    variables = {'form':form}
        except Exception as error:
            self.__log.error(
                f'Error in the method method login in AuthBL., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
        return HttpResponse(template.render(variables,request))

    def token_challenge(self, request):
        utility = Utility()
        exception = ExceptionHandler()
        try:
            if request.method == 'GET':
                request.session['next_url'] = request.GET.get('next')

            template=get_template('auth/token_challenge.html')
            form = TwoFactorVerificationForm()
            variables = {'form':form}
            if request.POST:
                form = TwoFactorVerificationForm(request.POST)
                if form.is_valid():
                    user_name = request.session['user_name']
                    password = request.session['password']
                    token = request.POST.get('two_fa_token', '')
                    user = authenticate(username=user_name, password=password)
                    if user:
                        if UserManagementBL().verify_two_fa_token(request.session['email'], token):
                            login(request,user)
                            request.session['user_group'] = int(user.groups.values_list('id', flat=True).first())
                            self.audit_logs['user_id'] = user.id
                            self.audit_logs['event'] = 'User Login'
                            self.audit_logs['event_details'] =f'User with username {user.username} has logged in.'
                            LogsDA().create_audit_logs(self.audit_logs)
                            URL = request.session['next_url']
                            if URL:
                                return  HttpResponseRedirect(URL)
                            del request.session['next_url']
                            return redirect('home')
                        else:
                            messages.error(request,'The OTP entered is incorrect.')
                    else:
                        messages.error(request,'The OTP entered is incorrect.')
                else:
                    variables = {'form':form}
        except Exception as error:
            self.__log.error(
                f'Error in the method method token_challenge in AuthBL., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
        return HttpResponse(template.render(variables, request))