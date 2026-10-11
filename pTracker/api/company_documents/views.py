""" Company documents and logo (JWT). The company is the caller's verified
active company; every permission check is in CompanyDocumentBL. File
responses are returned as-is, everything else as JSON. """

from django.http import HttpResponseBase
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication as JSONWebTokenAuthentication

from pTracker.api.company_documents.company_document_biz import CompanyDocumentBL


def respond(response):
    if isinstance(response, HttpResponseBase):
        return response
    return Response(response, status=response.get('status', 200))


class CompanyDocumentsView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def get(self, request, company_uuid):
        return respond(CompanyDocumentBL().list_documents(request.user.id, company_uuid, request.query_params))

    def post(self, request, company_uuid):
        return respond(CompanyDocumentBL().upload_document(request.user.id, company_uuid, request.data, request.FILES))


class CompanyDocumentDetailView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, company_uuid, document_id):
        return respond(CompanyDocumentBL().get_document(request.user.id, company_uuid, document_id))

    def delete(self, request, company_uuid, document_id):
        return respond(CompanyDocumentBL().delete_document(request.user.id, company_uuid, document_id))


class CompanyDocumentContentView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, company_uuid, document_id):
        return respond(CompanyDocumentBL().document_content(request.user.id, company_uuid, document_id))


class CompanyLogoView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def get(self, request, company_uuid):
        return respond(CompanyDocumentBL().logo_content(request.user.id, company_uuid))

    def put(self, request, company_uuid):
        return respond(CompanyDocumentBL().replace_logo(request.user.id, company_uuid, request.FILES))

    def delete(self, request, company_uuid):
        return respond(CompanyDocumentBL().delete_logo(request.user.id, company_uuid))
