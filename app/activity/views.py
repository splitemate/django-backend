from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.core.paginator import Paginator
from django.db.models import Q
from user.renderers import UserRenderer
from activity.models import Activity


class ActivitySynciew(APIView):
    """Sync Activity for splitemate"""

    renderer_classes = [UserRenderer]
    permission_classes = [IsAuthenticated]

    def get(self, requests):

        since_id_str = requests.query_params.get('since_id', '0')
        limit_str = requests.query_params.get('limit', '50')

        try:
            since_id = int(since_id_str)
            limit = int(limit_str)
        except Exception:
            return Response(
                {"message": "Please provide since_id and limit as valid parameter"},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = requests.user
        queryset = Activity.objects.filter(
            Q(related_users_ids=user),
            id__gt=since_id,
        ).order_by('id')

        paginator = Paginator(queryset, limit)
        page_object = paginator.get_page(1)

        entries = list(page_object.object_list)

        activities_data = []
        for act in entries:
            activities_data.append(act.get_activity_data())

        has_more = page_object.has_next()

        max_id_in_result = entries[-1].id if entries else since_id

        response_data = {
            "activities": activities_data,
            "has_more": has_more,
            "next_since_id": max_id_in_result
        }

        return Response(response_data, status=status.HTTP_200_OK)
