from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminRole

from .models import ActivityLog

MAX_ENTRIES = 200


class ActivityListView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        entries = ActivityLog.objects.all()
        code = request.query_params.get("booking", "").strip().upper()
        if code:
            entries = entries.filter(booking_code=code)
        data = [
            {
                "at": timezone.localtime(entry.created_at).isoformat(),
                "action": entry.action,
                "booking_code": entry.booking_code,
                "status_after": entry.status_after,
                "actor": entry.actor_email or "patient",
            }
            for entry in entries[:MAX_ENTRIES]
        ]
        return Response({"entries": data})