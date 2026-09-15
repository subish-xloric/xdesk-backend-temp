from django.urls import re_path as url
from django.contrib import admin
from django.urls import path


from pTracker.api.app.views import GetVersionStatus

urlpatterns = [
                path('get-version-status/', GetVersionStatus.as_view(),name='get_version_status'),
              ]