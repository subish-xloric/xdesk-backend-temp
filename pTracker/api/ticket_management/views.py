from csv import excel
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication as JSONWebTokenAuthentication
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

# from pTracker.api.appraisal.appraisal_biz import AppraisalBL
# from pTracker.api.appraisal.appraisal_report import AppraisalReportBL

from django.http import HttpResponse


