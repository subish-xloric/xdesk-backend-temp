""" Endpoints called by external attendance collectors (machine-to-machine).
Authenticated with X-Collector-Id / X-Collector-Key, never with an employee
JWT; HTTPS enforced and rate limited per collector. """

from rest_framework.response import Response
from rest_framework.views import APIView

from pTracker.api.attendance_v2.collector_auth import CollectorAuthentication
from pTracker.api.attendance_v2.collector_auth import CollectorRateThrottle
from pTracker.api.attendance_v2.collector_auth import CollectorTransportIsSecure
from pTracker.api.attendance_v2.collector_auth import IsCollector
from pTracker.api.attendance_v2.ingestion_biz import PunchIngestionBL


class CollectorView(APIView):
    authentication_classes = [CollectorAuthentication]
    permission_classes = [CollectorTransportIsSecure, IsCollector]
    throttle_classes = [CollectorRateThrottle]


class CollectorPunchView(CollectorView):
    def post(self, request):
        response = PunchIngestionBL().ingest(request.user.collector, request.data, request.META)
        return Response(response, status=response.get('status', 200))


class CollectorHeartbeatView(CollectorView):
    def post(self, request):
        response = PunchIngestionBL().heartbeat(request.user.collector, request.data, request.META)
        return Response(response, status=response.get('status', 200))
