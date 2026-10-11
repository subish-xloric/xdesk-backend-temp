from django.urls import path

from pTracker.api.company_documents.views import CompanyDocumentsView
from pTracker.api.company_documents.views import CompanyDocumentDetailView
from pTracker.api.company_documents.views import CompanyDocumentContentView
from pTracker.api.company_documents.views import CompanyLogoView


urlpatterns = [
    path('<uuid:company_uuid>/documents/', CompanyDocumentsView.as_view(), name='company_documents'),
    path('<uuid:company_uuid>/documents/<uuid:document_id>/', CompanyDocumentDetailView.as_view(),
         name='company_document_detail'),
    path('<uuid:company_uuid>/documents/<uuid:document_id>/content/', CompanyDocumentContentView.as_view(),
         name='company_document_content'),
    path('<uuid:company_uuid>/logo/', CompanyLogoView.as_view(), name='company_logo'),
]
