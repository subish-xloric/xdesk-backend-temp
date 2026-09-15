from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication as JSONWebTokenAuthentication
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from pTracker.api.ticket.ticket_biz import TicketBL
from pTracker.api.ticket.ticket_biz_v1 import TicketBL_V1
from pTracker.api.ticket.ticket_report_biz import TicketReportBL
from pTracker.api.ticket.external_api_biz import ExternalApiBL
from pTracker.common.api_token_auth import ApiTokenAuthentication
# from pTracker.api.tax.notification_biz import NotificationBL


class GetCreateTicketDropdowns(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        response = TicketBL().get_ticket_dropdown_params(request, project_id)
        return Response(response)

class GetProjectDropdowns(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    def get(self, request):
        response = TicketBL().get_all_projects_dropdown(request)
        return Response(response)


class CreateTicket(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def put(self, request):
        response = TicketBL().create_ticket(request)
        return Response(response)


class TicketDetailsView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def get(self, request, ticket_id):
        response = TicketBL().get_ticket_details_by_ticket_id(request, ticket_id)
        return Response(response)

    def put(self, request, ticket_id):
        response = TicketBL().update_ticket(request, ticket_id)
        return Response(response)


class TicketProjectView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def get(self, request, ticket_id):
        response = TicketBL().get_ticket_project_by_ticket_id(request, ticket_id)
        return Response(response)
    

class TicketSummaryView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def get(self, request, ticket_id):
        response = TicketBL_V1().get_ticket_summary_by_ticket_id(request, ticket_id)
        return Response(response)


class GetTicketList(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = TicketBL().list_all_tickets(request)
        return Response(response)


class GetProjectTicketList(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = TicketBL().list_all_project_tickets(request)
        return Response(response)


class GetAllTicketsCSVDetails(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def get(self, request):
        response = TicketReportBL().get_all_ticket_details_in_csv(request)
        return response


class TicketAttachmentView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def get(self, request, attachment_id):
        response = TicketBL().get_attachment_file(request, attachment_id)
        if 'error' in response:
            return Response(response, status=499)
        return response


class GetTicketDashboard(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        response = TicketBL().get_ticket_dashboard(request, project_id)
        return Response(response)

class CreateorUpdatepreferredProject(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def put(self, request):
        response = TicketBL().create_or_update_preferred_project(request)
        return Response(response)




class GetSubTicketDetails(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id, ticket_id):
        response = TicketBL().get_sub_ticket_details(request, project_id, ticket_id)
        return Response(response)


# ---------------------------------------------------------------------------
# External Integration API  (v1)
# All views below use ApiTokenAuthentication instead of JWT.
# Clients must include:  Authorization: Token <api_token>
# ---------------------------------------------------------------------------


class VerifyConnectionView(APIView):
    """
    GET /api/v1/users/me

    Validates the API token and returns the authenticated user's basic profile.

    External tools call this endpoint first to confirm that the supplied token
    is valid and the pTracker API is reachable before making any other requests.

    Authentication : Authorization: Token <api_token>
    Success        : HTTP 200 with { id, name, email, active }
    Invalid token  : HTTP 401 (raised by ApiTokenAuthentication)
    """

    authentication_classes = [ApiTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = ExternalApiBL().verify_connection(request.user)
        return Response(response)


class ExternalProjectsView(APIView):
    """
    GET /api/v1/projects

    Returns all projects the authenticated user is a member of.

    External tools use this to populate a project-selection dropdown, letting
    the connected user choose which project's issues to import or sync.

    Authentication : Authorization: Token <api_token>
    Success        : HTTP 200 with { projects: [ { id, key, name, description } ] }
    Invalid token  : HTTP 401
    """

    authentication_classes = [ApiTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = ExternalApiBL().get_projects(request.user)
        return Response(response)


class ExternalProjectIssuesView(APIView):
    """
    GET /api/v1/projects/<project_id>/issues

    Returns a paginated list of active (non-closed) issues for the given project.

    The user must be a member of the project; otherwise HTTP 403 is returned.
    Pagination is controlled via optional query parameters:
        page  (int, default=1)  – 1-based page number
        limit (int, default=50) – items per page, capped at 100

    Authentication : Authorization: Token <api_token>
    Success        : HTTP 200 with { total, issues: [ { id, summary, description,
                                    status, resolved, assignee } ] }
    Not a member   : HTTP 403
    Invalid token  : HTTP 401
    """

    authentication_classes = [ApiTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        try:
            page = max(1, int(request.query_params.get('page', 1)))
            limit = min(100, max(1, int(request.query_params.get('limit', 50))))
        except (ValueError, TypeError):
            page, limit = 1, 50

        response = ExternalApiBL().get_project_issues(
            request.user, project_id, page, limit
        )
        # pop the internal 'status' hint before serialising the response body
        status_code = response.pop('status', 200) if 'error' in response else 200
        return Response(response, status=status_code)


class ExternalMyIssuesView(APIView):
    """
    GET /api/v1/issues/me

    Returns all active (non-closed) tickets currently assigned to the
    authenticated user, spanning all projects they belong to.

    External tools use this to display a "My Tasks" view for the connected
    user without requiring them to select a project first.

    Authentication : Authorization: Token <api_token>
    Success        : HTTP 200 with { issues: [ { id, summary, description,
                                    dueDate, project, status } ] }
    Invalid token  : HTTP 401
    """

    authentication_classes = [ApiTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = ExternalApiBL().get_my_issues(request.user)
        return Response(response)


class GenerateApiTokenView(APIView):
    """
    POST /api/v1/users/generate-api-token

    Generates (or regenerates) a personal API token for the authenticated user.

    This endpoint uses standard JWT authentication so the user must be logged in
    via the normal web/mobile session. Calling it invalidates any previously
    issued API token, so existing integrations must be updated with the new value.

    The generated token is a 32-character hex UUID and is returned only once —
    the user should copy it immediately as pTracker does not display it again.

    Authentication : Authorization: JWT <jwt_token>   (standard session auth)
    Success        : HTTP 200 with { api_token, message }
    Unauthenticated: HTTP 401
    """

    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        response = ExternalApiBL().generate_api_token(request.user)
        return Response(response)

