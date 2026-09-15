from rest_framework.authentication import SessionAuthentication, BasicAuthentication, TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication as JSONWebTokenAuthentication
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from pTracker.api.projects.project_biz import ProjectBL
from pTracker.dataaccess.ptracker_access.user_da import UserDA
from pTracker.api.projects.project_biz_v1 import ProjectBL_V1

from pTracker.api.projects.project_biz_v2 import ProjectCreateBL

class ProjectActivityView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        activities = ProjectBL().get_all_project_activity()
        if not activities:
            activities = [{"error": "No activity found"}]
        return Response(activities)

class ProjectView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        role_id, role_name = UserDA().get_user_role_by_id(request.user.id)
        if role_id in (1, 2, 3):
            projects = ProjectBL().get_all_projects()
        else:
            projects = ProjectBL().get_all_projects_by_user(request.user.id)
        return Response(projects)

class ProjectModuleView(APIView):

    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        projects = ProjectBL().get_all_active_modules_by_project(project_id, request.user.id)
        return Response(projects)

    def put(self, request):
        result  = ProjectBL().create_or_update_project_module(request)
        return Response(result)

class ProjectModuleDeleteView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    def get(self, request, module_id):
        result = ProjectBL().delete_project_module(request, module_id)
        return Response(result)

class EmployeesByProjectId(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    def get(self, request):
        result = ProjectBL().get_members_by_project_id(request.GET)
        return Response(result)

class EmployeesProjectMapping(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    def put(self, request):
        result = ProjectBL().create_emp_project_mapping(request.user.id,request)
        return Response(result, status=result['status'])





# @api_view(['GET'])
# @authentication_classes([SessionAuthentication, BasicAuthentication])
# @permission_classes([IsAuthenticated])
# def example_view(request, format=None):
#     content = {
#         'user': unicode(request.user),  # `django.contrib.auth.User` instance.
#         'auth': unicode(request.auth),  # None
#     }
#     return Response(content)

### MOBILE API

class ProjectActivityView_V1(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        activities = ProjectBL().get_all_project_activity()
        res = ProjectBL_V1().format_activiteis(activities)
        return Response(res, status= res.get("status", 200))

class ProjectModuleView_V1(APIView):

    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        projects = ProjectBL().get_all_active_modules_by_project(project_id, request.user.id)
        res = ProjectBL_V1().format_get_modules(projects)
        return Response(res, status= res.get("status", 200))

    def put(self, request):
        result  = ProjectBL().create_or_update_project_module(request)
        return Response(result)

class ProjectView_V1(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        role_id, role_name = UserDA().get_user_role_by_id(request.user.id)
        if role_id in (1, 2, 3):
            projects = ProjectBL().get_all_projects()
        else:
            projects = ProjectBL().get_all_projects_by_user(request.user.id)
        res = ProjectBL_V1().format_get_projects(projects)
        return Response(res, status = res.get("status", 200))

class VersionExpiredView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)


    def post(self,*args, **kwargs):
        response ={"error": "This version of the app is obsolete. Please update.", "status": 426}
        return Response(response, status = response.get("status", 200))

    def get(self,*args, **kwargs):
        response ={"error": "This version of the app is obsolete. Please update.", "status": 426}
        return Response(response, status = response.get("status", 200))
    
    




#project create biz
class GetAllProjectList(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def get(self, request):
        response = ProjectCreateBL().get_all_projects(request)
        return Response(response)


class CreateProject(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def put(self, request):
        response = ProjectCreateBL().create_project(request)
        return Response(response)


class UpdateProject(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def put(self, request, project_id):
        response = ProjectCreateBL().update_project(request, project_id)
        return Response(response)


class DeleteProject(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def put(self, request, project_id):
        response = ProjectCreateBL().delete_project(request, project_id)
        return Response(response)


class GetProjectDropDownParams(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def get(self, request):
        response = ProjectCreateBL().get_project_drop_down_params(request)
        return Response(response)