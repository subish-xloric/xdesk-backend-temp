from django.urls import path
from pTracker.api.ticket.views import GetCreateTicketDropdowns
from pTracker.api.ticket.views import GetProjectDropdowns
from pTracker.api.ticket.views import CreateTicket
from pTracker.api.ticket.views import TicketDetailsView
from pTracker.api.ticket.views import GetTicketList
from pTracker.api.ticket.views import GetProjectTicketList
from pTracker.api.ticket.views import GetAllTicketsCSVDetails
from pTracker.api.ticket.views import TicketAttachmentView
from pTracker.api.ticket.views import GetTicketDashboard
from pTracker.api.ticket.views import CreateorUpdatepreferredProject
from pTracker.api.ticket.views import TicketSummaryView
from pTracker.api.ticket.views import GetSubTicketDetails
from pTracker.api.ticket.views import TicketProjectView


urlpatterns = [

     path('get-project-dropdown/', GetProjectDropdowns.as_view(), name='get_ticket_create_dropdown'),
     path('get-ticket-param-dropdown/<int:project_id>/', GetCreateTicketDropdowns.as_view(), name='get_ticket_create_dropdown'),

     path('list-all-project-tickets/', GetProjectTicketList.as_view(), name='list_all_tickets'),

     path('ticket-details/<int:ticket_id>/', TicketDetailsView.as_view(), name='ticket-details'),
     path('ticket-project-name/<int:ticket_id>/', TicketProjectView.as_view(), name='ticket-project'),
     path('ticket-summary/<int:ticket_id>/', TicketSummaryView.as_view(), name='ticket-summary'),
     path('list-all-tickets/', GetTicketList.as_view(), name='list_all_tickets'),

     path('create-ticket/', CreateTicket.as_view(), name='create_ticket'),
     path('update-ticket/<int:ticket_id>/', TicketDetailsView.as_view(), name='update_ticket'),
     path('ticket-dashboard/<int:project_id>/', GetTicketDashboard.as_view(), name='get_ticket_dashboard'),
     path('create-or-update-preferred-project/', CreateorUpdatepreferredProject.as_view(), name='create_or_update_preferred_project'),
     path('get-sub-ticket-details/<int:project_id>/<int:ticket_id>/', GetSubTicketDetails.as_view(), name='get_sub_ticket_details'),


     path('view-attachment/<int:attachment_id>/', TicketAttachmentView.as_view(), name='ticket_attachment'),
     #generate csv for all tickets
     path('generate-all-tickets-csv-details/', GetAllTicketsCSVDetails.as_view(), name='all_tickets_csv_details'),
]