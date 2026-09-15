from django.urls import re_path as url
from django.contrib import admin
from django.urls import path


from pTracker.api.user.views import  CustomLoginView
from pTracker.api.user.views import AuthyTokenVerifyView

urlpatterns = [
                  url(r'login/', CustomLoginView.as_view(), name='custom_login'),
                  url(r'2fa/token-verify/', AuthyTokenVerifyView.as_view(), name='2fa_token_verify'),
              ]