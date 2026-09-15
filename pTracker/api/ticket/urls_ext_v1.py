"""
URL patterns for the pTracker external integration API (v1).

All routes are mounted under /api/v1/ in the root urls.py:

    path('api/v1/', include('pTracker.api.ticket.urls_ext_v1'))

Resulting full paths
--------------------
GET  /api/v1/users/me                              – Verify token & return user profile
GET  /api/v1/projects/                             – List projects the user belongs to
GET  /api/v1/projects/<project_id>/issues/         – List open issues for a project
GET  /api/v1/issues/me/                            – List all issues assigned to the user
POST /api/v1/users/generate-api-token/             – Generate / regenerate the user's API token

Authentication
--------------
All GET endpoints use ApiTokenAuthentication (Authorization: Token <api_token>).
The POST endpoint uses the standard JWT session (Authorization: JWT <token>).
"""

from django.urls import path

from pTracker.api.ticket.views import (
    VerifyConnectionView,
    ExternalProjectsView,
    ExternalProjectIssuesView,
    ExternalMyIssuesView,
    GenerateApiTokenView,
)

urlpatterns = [
    # A. Verify connection — confirms the token is valid and returns user profile.
    path('users/me/', VerifyConnectionView.as_view(), name='ext_v1_verify_connection'),

    # Token provisioning — generates/regenerates the user's API token (JWT auth).
    path('users/generate-api-token/', GenerateApiTokenView.as_view(), name='ext_v1_generate_api_token'),

    # B. Fetch projects — returns all projects the token owner belongs to.
    path('projects/', ExternalProjectsView.as_view(), name='ext_v1_projects'),

    # C. Fetch issues for a project — paginated list of open issues.
    #    Query params: page (default 1), limit (default 50, max 100)
    path('projects/<int:project_id>/issues/', ExternalProjectIssuesView.as_view(), name='ext_v1_project_issues'),

    # D. Fetch "My Tasks" — all open issues assigned to the authenticated user.
    path('issues/me/', ExternalMyIssuesView.as_view(), name='ext_v1_my_issues'),
]
