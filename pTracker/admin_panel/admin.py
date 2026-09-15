from django.contrib import admin

from pTracker.dataaccess.ptracker_access.project_models import ProjectActivity

from pTracker.dataaccess.ptracker_access.project_models import Project
from pTracker.dataaccess.ptracker_access.project_models import ProjectModule
from pTracker.dataaccess.ptracker_access.project_models import ProjectEmployee
from pTracker.dataaccess.ptracker_access.project_models import ProjectEmployeeLog
from pTracker.dataaccess.ptracker_access.project_models import ProjectAccount

admin.site.register(ProjectActivity)
admin.site.register(Project)
admin.site.register(ProjectModule)
admin.site.register(ProjectEmployee)
admin.site.register(ProjectAccount)
