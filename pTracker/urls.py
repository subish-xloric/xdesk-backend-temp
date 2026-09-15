"""pTracker URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from pTracker.wiki.sites import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('wiki/',include('pTracker.wiki.sites.urls')),
    path('api/auth/', include('pTracker.api.user.urls')),
    path('api/auth/', include('dj_rest_auth.urls')),
    path('api/project/', include('pTracker.api.projects.urls')),
    path('api/timesheet/', include('pTracker.api.timesheet.urls')),
    path('api/attendance/', include('pTracker.api.attendance.urls')),
    path('api/user/', include('pTracker.api.user.urls1')),
    path('api/leave/', include('pTracker.api.leave.urls')),
    path('api/offboard/', include('pTracker.api.offboard.urls')),
    path('api/appraisal/', include('pTracker.api.appraisal.urls')),
    path('api/onboarding/', include('pTracker.api.onboarding.urls')),
    path('api/asset/',include('pTracker.api.asset_management.urls')),
    path('api/careers/',include('pTracker.api.interview.urls')),
    path('api/finance/',include('pTracker.api.finance.urls')),
    path('api/induction/',include('pTracker.api.induction.urls')),
    path('api/assessment/',include('pTracker.api.assessment.urls')),
    path('api/rewards/',include('pTracker.api.rewards.urls')),

    path('api/resource/',include('pTracker.api.resource.urls')),
    
    path('api/tax/',include('pTracker.api.finance.urls')),
    
    path('api/ticket/',include('pTracker.api.ticket.urls')),
    path('api/v1/', include('pTracker.api.ticket.urls_ext_v1')),



    path('v1/api/attendance/', include('pTracker.api.attendance.urls_v1')),
    path('v1/api/timesheet/', include('pTracker.api.timesheet.urls_v1')),
    path('v1/api/wfh/', include('pTracker.api.attendance.urls_v1')),
    path('v1/api/leave/', include('pTracker.api.leave.urls_v1')),
    path('v1/api/user/', include('pTracker.api.user.urls_v1')),
    path('v1/api/projects/', include('pTracker.api.projects.urls_v1')),
    path('v1/api/auth/', include('pTracker.api.user.urls_v1')),
    path('v1/api/auth/', include('dj_rest_auth.urls')),
    path('v1/api/app/',  include('pTracker.api.app.urls')),


    # path('v2/api/attendance/', include('pTracker.api.attendance.urls_v2_mob')),
    # path('v2/api/timesheet/', include('pTracker.api.timesheet.urls_v2_mob')),
    # path('v2/api/wfh/', include('pTracker.api.attendance.urls_v2_mob')),
    # path('v2/api/leave/', include('pTracker.api.leave.urls_v2_mob')),
    # path('v2/api/user/', include('pTracker.api.user.urls_v2_mob')),
    # path('v2/api/projects/', include('pTracker.api.projects.urls_v2_mob')),
    # path('v2/api/auth/', include('pTracker.api.user.urls_v2_mob')),
    # path('v2/api/auth/', include('dj_rest_auth.urls')),
    # # path('v1/api/app/',  include('pTracker.api.app.urls')),

] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler500 = views.handler500
handler404 = views.handler404
handler403 = views.handler403
