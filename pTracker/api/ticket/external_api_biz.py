"""
Business logic for the pTracker external integration API (v1).

These endpoints mirror a Jira-style REST API surface so that third-party
tools (e.g. ClickUp, Linear, custom dashboards) can authenticate with a
per-user API token and pull project/issue data without going through the
normal JWT-based session flow.

Authentication: every request must include the header
    Authorization: Token <api_token>

The api_token value is stored in user_profile.api_token and is managed via
the token-generation endpoint (POST /api/v1/users/generate-api-token).
"""

import uuid

from bs4 import BeautifulSoup
from django.conf import settings
from django.contrib.auth.models import User

from pTracker.common.logs import Logs
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.dataaccess.ptracker_access.user_da import UserDA
from pTracker.dataaccess.ptracker_access.ticket_da import TicketDA
from pTracker.dataaccess.ptracker_access.project_da import ProjectDA
from pTracker.dataaccess.ptracker_access.project_models import Project


def _strip_html(text):
    """
    Removes all HTML tags from a string and returns plain text.

    Uses BeautifulSoup's html.parser to handle malformed markup safely.
    Multiple whitespace characters are collapsed into a single space.
    Returns an empty string when the input is None or empty.

    Args:
        text (str | None): Raw string that may contain HTML markup.

    Returns:
        str: Plain text with all HTML tags removed.
    """
    if not text:
        return ''
    return ' '.join(BeautifulSoup(text, 'html.parser').get_text(separator=' ').split())


def _project_key(name):
    """
    Derives a short, Jira-style project key from a project name.

    Takes the first letter of each word (up to 6 characters), uppercased.
    Examples:
        "Core Authentication API"  -> "CAA"
        "Frontend Dashboard"       -> "FD"
        "pTracker"                 -> "P"

    Args:
        name (str): The full project name.

    Returns:
        str: An uppercase abbreviation used as the project key.
    """
    words = (name or '').split()
    return ''.join(w[0].upper() for w in words if w)[:6] or 'PRJ'


class ExternalApiBL:
    """
    Business logic layer for the four external integration endpoints.

    Each method corresponds to one API endpoint:
      A. verify_connection  -> GET  /api/v1/users/me
      B. get_projects       -> GET  /api/v1/projects
      C. get_project_issues -> GET  /api/v1/projects/<project_id>/issues
      D. get_my_issues      -> GET  /api/v1/issues/me

    A fifth helper (generate_api_token) supports the token provisioning
    endpoint: POST /api/v1/users/generate-api-token
    """

    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()
        self.__user_da = UserDA()
        self.__ticket_da = TicketDA()
        self.__project_da = ProjectDA()

    # ------------------------------------------------------------------
    # A. Verify Connection
    # ------------------------------------------------------------------

    def verify_connection(self, user):
        """
        Returns the basic profile of the authenticated user.

        External tools call this endpoint first to confirm that the supplied
        API token is valid and the pTracker API is reachable. No additional
        DB queries beyond the authentication step itself are needed — the
        Django User object is already loaded by the auth backend.

        Args:
            user (User): The Django User resolved from the API token.

        Returns:
            dict: {
                "id":     "usr-<user_id>",
                "name":   "<first_name> <last_name>",
                "email":  "<email>",
                "active": <bool>
            }
            On unexpected error returns {"error": "<message>"}.
        """
        try:
            return {
                "id": f"usr-{user.id}",
                "name": f"{user.first_name} {user.last_name}".strip(),
                "email": user.email,
                "active": bool(user.is_active),
            }
        except Exception:
            self.__log.error(self.__exception.get_exception())
            return {"error": "Failed to retrieve user profile."}

    # ------------------------------------------------------------------
    # B. Fetch Projects
    # ------------------------------------------------------------------

    def get_projects(self, user):
        """
        Returns all active projects the authenticated user is a member of.

        Looks up project memberships in project_emp_mapping, then fetches
        the full Project rows. The short 'key' field is derived from the
        project name (see _project_key).

        Args:
            user (User): The Django User resolved from the API token.

        Returns:
            dict: {
                "projects": [
                    {
                        "id":          "proj-<project_id>",
                        "key":         "<derived abbreviation>",
                        "name":        "<project name>",
                        "description": "<project description>"
                    },
                    ...
                ]
            }
            On unexpected error the list is empty and an "error" key is added.
        """
        try:
            project_ids = list(
                self.__project_da.get_all_project_ids_of_user(user.id)
            )
            projects = Project.objects.filter(
                project_id__in=project_ids, is_deleted=0
            ).order_by('name')

            project_list = [
                {
                    "id": f"proj-{p.project_id}",
                    "key": _project_key(p.name),
                    "name": p.name,
                    "description": p.description or "",
                }
                for p in projects
            ]
            return {"projects": project_list}
        except Exception:
            self.__log.error(self.__exception.get_exception())
            return {"projects": [], "error": "Failed to retrieve projects."}

    # ------------------------------------------------------------------
    # C. Fetch Issues for a Specific Project
    # ------------------------------------------------------------------

    def get_project_issues(self, user, project_id, page=1, limit=50):
        """
        Returns a paginated list of open/active issues for the specified project.

        Access control: the user must be a member of the project (checked via
        project_emp_mapping). Closed issues (status in TICKET_STATUS_CLOSED)
        are excluded from the results.

        All ticket_details rows are fetched in a single batch query and split
        into two groups per ticket:
          - description : the row where is_header=1 (original description), HTML stripped.
          - comments    : all remaining rows ordered by ticket_details_id (chronological),
                          each message stripped of HTML tags.

        Assignee names are resolved in a separate batch query on auth_user.

        Args:
            user       (User): The Django User resolved from the API token.
            project_id (int):  The numeric project identifier from the URL path.
            page       (int):  1-based page number (default 1).
            limit      (int):  Issues per page, capped at 100 (default 50).

        Returns:
            dict: {
                "total":  <int>,
                "issues": [
                    {
                        "id":          "<KEY>-<ticket_id>",
                        "summary":     "<ticket subject>",
                        "description": "<plain text description>",
                        "status":      "<status string>",
                        "resolved":    <bool>,
                        "assignee":    {"name": "<full name>"} | null,
                        "comments":    ["<plain text comment>", ...]
                    },
                    ...
                ]
            }
            On access denial: {"error": "<message>", "status": 403}
            On unexpected error: {"total": 0, "issues": [], "error": "<message>"}
        """
        try:
            is_member = self.__project_da.is_project_accessible(project_id, user.id)
            if not is_member:
                return {
                    "error": "Access denied. You are not a member of this project.",
                    "status": 403,
                }

            all_tickets = self.__ticket_da.get_all_tickets_filtered(
                {"project_id": project_id}
            )
            if all_tickets is None:
                return {"total": 0, "issues": []}

            open_tickets = all_tickets.exclude(status__in=settings.TICKET_STATUS_CLOSED)
            total = open_tickets.count()

            # Apply pagination.
            offset = (page - 1) * limit
            page_tickets = list(open_tickets[offset: offset + limit])

            if not page_tickets:
                return {"total": total, "issues": []}

            ticket_ids = [t.ticket_id for t in page_tickets]

            # Batch-fetch all ticket_details rows for the current page in one query,
            # ordered chronologically so comments appear oldest-first.
            # is_header=1  → original description entry
            # is_header!=1 → subsequent comment / update entries
            all_details = (
                self.__ticket_da
                .get_all_ticket_messages_by_ticket_ids(ticket_ids)
                .order_by('ticket_details_id')
            )

            desc_map = {}     # {ticket_id: plain_text_description}
            comments_map = {} # {ticket_id: [plain_text_comment, ...]}

            if all_details:
                for d in all_details:
                    if d.is_header == 1:
                        # Keep only the first description row per ticket.
                        if d.ticket_id not in desc_map:
                            desc_map[d.ticket_id] = _strip_html(d.message)
                    else:
                        plain = _strip_html(d.message)
                        if plain:
                            comments_map.setdefault(d.ticket_id, []).append(plain)

            # Batch-fetch assignee display names to avoid N+1 queries.
            assignee_ids = list(
                {t.assigned_to for t in page_tickets if t.assigned_to}
            )
            assignee_map = {}
            if assignee_ids:
                for u in User.objects.filter(id__in=assignee_ids):
                    assignee_map[u.id] = f"{u.first_name} {u.last_name}".strip()

            # Resolve project key once for issue ID formatting.
            project_obj = Project.objects.filter(
                project_id=project_id, is_deleted=0
            ).first()
            proj_key = (
                _project_key(project_obj.name)
                if project_obj
                else f"PRJ{project_id}"
            )

            issues = []
            for ticket in page_tickets:
                assignee_name = (
                    assignee_map.get(ticket.assigned_to) if ticket.assigned_to else None
                )
                issues.append({
                    "id": f"{proj_key}-{ticket.ticket_id}",
                    "summary": ticket.subject,
                    "description": desc_map.get(ticket.ticket_id, ""),
                    "status": ticket.status,
                    "resolved": ticket.status in settings.TICKET_STATUS_CLOSED,
                    "assignee": {"name": assignee_name} if assignee_name else None,
                    "comments": comments_map.get(ticket.ticket_id, []),
                })

            return {"total": total, "issues": issues}

        except Exception:
            self.__log.error(self.__exception.get_exception())
            return {"total": 0, "issues": [], "error": "Failed to retrieve project issues."}

    # ------------------------------------------------------------------
    # D. Fetch "My Tasks" (issues assigned to the current user)
    # ------------------------------------------------------------------

    def get_my_issues(self, user):
        """
        Returns all active tickets currently assigned to the authenticated user.

        Fetches TicketHeader rows where assigned_to matches the user's ID,
        excluding closed statuses. Project names are resolved in a single
        batch query. Descriptions are fetched in a single batch query on
        ticket_details (is_header=1).

        Args:
            user (User): The Django User resolved from the API token.

        Returns:
            dict: {
                "issues": [
                    {
                        "id":          "<KEY>-<ticket_id>",
                        "summary":     "<ticket subject>",
                        "description": "<plain text description>",
                        "dueDate":     "<ISO-8601 datetime string>" | null,
                        "project":     {"name": "<project name>"},
                        "status":      "<status string>",
                        "comments":    ["<plain text comment>", ...]
                    },
                    ...
                ]
            }
            On unexpected error the list is empty and an "error" key is added.
        """
        try:
            all_tickets = self.__ticket_da.get_all_tickets_filtered(
                {"assigned_to": user.id}
            )
            if all_tickets is None:
                return {"issues": []}

            my_tickets = list(
                all_tickets.exclude(status__in=settings.TICKET_STATUS_CLOSED)
            )

            if not my_tickets:
                return {"issues": []}

            # Batch-fetch projects to avoid N+1 queries.
            project_ids = list({t.project_id for t in my_tickets if t.project_id})
            project_map = {}
            if project_ids:
                for p in Project.objects.filter(
                    project_id__in=project_ids, is_deleted=0
                ):
                    project_map[p.project_id] = p

            # Batch-fetch all ticket_details rows in one query, ordered chronologically
            # so comments appear oldest-first.
            # is_header=1  → original description entry
            # is_header!=1 → subsequent comment / update entries
            ticket_ids = [t.ticket_id for t in my_tickets]
            all_details = (
                self.__ticket_da
                .get_all_ticket_messages_by_ticket_ids(ticket_ids)
                .order_by('ticket_details_id')
            )

            desc_map     = {}  # {ticket_id: plain_text_description}
            comments_map = {}  # {ticket_id: [plain_text_comment, ...]}

            if all_details:
                for d in all_details:
                    if d.is_header == 1:
                        if d.ticket_id not in desc_map:
                            desc_map[d.ticket_id] = _strip_html(d.message)
                    else:
                        plain = _strip_html(d.message)
                        if plain:
                            comments_map.setdefault(d.ticket_id, []).append(plain)

            issues = []
            for ticket in my_tickets:
                project_obj = project_map.get(ticket.project_id)
                proj_key = (
                    _project_key(project_obj.name)
                    if project_obj
                    else f"PRJ{ticket.project_id}"
                )
                project_name = project_obj.name if project_obj else ""

                issues.append({
                    "id": f"{proj_key}-{ticket.ticket_id}",
                    "summary": ticket.subject,
                    "description": desc_map.get(ticket.ticket_id, ""),
                    "dueDate": (
                        ticket.deadline.isoformat() if ticket.deadline else None
                    ),
                    "project": {"name": project_name},
                    "status": ticket.status,
                    "comments": comments_map.get(ticket.ticket_id, []),
                })

            return {"issues": issues}

        except Exception:
            self.__log.error(self.__exception.get_exception())
            return {"issues": [], "error": "Failed to retrieve assigned issues."}

    # ------------------------------------------------------------------
    # Token provisioning (used by the generate-api-token endpoint)
    # ------------------------------------------------------------------

    def generate_api_token(self, user):
        """
        Generates a new UUID4 API token for the authenticated user and saves
        it to user_profile.api_token, overwriting any previously issued token.

        Invalidating the old token is intentional — it forces any existing
        integration to be reconfigured with the new token, preventing stale
        credentials from lingering. The caller should display the token once
        and advise the user to copy it immediately.

        Args:
            user (User): The Django User whose token should be (re)generated.
                         Must already be authenticated via JWT (normal session).

        Returns:
            dict: {
                "api_token": "<new UUID4 token>",
                "message":   "API token generated. Copy it now — it will not be shown again."
            }
            On failure: {"error": "<message>"}
        """
        try:
            new_token = uuid.uuid4().hex  # 32-char hex string, URL-safe, no hyphens
            saved = self.__user_da.save_api_token(user.id, new_token)
            if not saved:
                return {"error": "Failed to save the API token. Please try again."}
            return {
                "api_token": new_token,
                "message": "API token generated. Copy it now — it will not be shown again.",
            }
        except Exception:
            self.__log.error(self.__exception.get_exception())
            return {"error": "Unexpected error while generating API token."}
