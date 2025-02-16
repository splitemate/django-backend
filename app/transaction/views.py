from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q
from user.renderers import UserRenderer
from transaction.models import Transaction
from transaction.serializers import (
    AddTransactionSerializer,
    ModifyTransactionSerializer,
    BulkTransactionSerializer
)


class AddTransactionView(APIView):
    """Create a new transaction in splitemate"""

    renderer_classes = [UserRenderer]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AddTransactionSerializer(data=request.data, context={'user': request.user})
        if serializer.is_valid():
            transaction = serializer.save()
            return Response({
                'message': 'Transaction created successfully.',
                'transaction_id': transaction.id
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ModifyTransactionView(APIView):
    """ Modify existing transaction of splitemate """

    permission_classes = [IsAuthenticated]
    renderer_classes = [UserRenderer]

    def put(self, request, pk):
        transaction = get_object_or_404(Transaction, pk=pk)
        serializer = ModifyTransactionSerializer(transaction, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GetExistingTransactionView(APIView):
    """Get existing transaction of splitemate"""

    permission_classes = [IsAuthenticated]
    renderer_classes = [UserRenderer]

    def get(self, request, pk):
        transaction = get_object_or_404(Transaction.objects.filter(is_active=True), pk=pk)
        participant_ids = transaction.get_associated_members()
        if request.user.id in participant_ids:
            data = transaction.get_transaction_data()
            return Response(data=data, status=200)
        else:
            return Response(
                {"message": "You are not participant of the transaction"},
                status=403
            )


class DeleteTransactionView(APIView):
    """Delete existing transaction of splitemate"""

    permission_classes = [IsAuthenticated]
    renderer_classes = [UserRenderer]

    def delete(self, request, pk):
        transaction = get_object_or_404(Transaction.objects.filter(is_active=True), pk=pk)
        if request.user.id not in transaction.allowed_to_modify_transaction():
            return Response(
                {"message": "You are not owner of the transaction"},
                status=403
            )
        transaction.delete()
        return Response({"message": "Transaction deleted successfully"}, status=204)


class RestoreTransactionView(APIView):
    """Restore the transaction of splitemate"""

    permission_classes = [IsAuthenticated]
    renderer_classes = [UserRenderer]

    def patch(self, request, pk):
        transaction = get_object_or_404(Transaction.all_objects, pk=pk)

        if transaction.is_active:
            return Response(
                {"message": "Transaction is already active"},
                status=400
            )
        if request.user.id not in transaction.allowed_to_modify_transaction():
            return Response(
                {"message": "You are not owner of the transaction"},
                status=403
            )
        transaction.restore()
        return Response(
            {"message": "Transaction Restored successfully"},
            status=200
        )


class GetBulkTransactionView(APIView):

    permission_classes = [IsAuthenticated]
    renderer_classes = [UserRenderer]

    def post(self, request):
        serializer = BulkTransactionSerializer(data=request.data)
        if serializer.is_valid():
            page_str = request.query_params.get('page', '1')
            limit_str = request.query_params.get('limit', '50')

            try:
                page = int(page_str)
                page = page if page > 0 else 1
                limit = int(limit_str)
            except Exception as e:
                print(e)
                return Response(
                    {"message": "Please provide page and limit as valid parameter"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            transaction_data = []
            transaction_ids = serializer.validated_data['transaction_ids']
            queryset = Transaction.objects.filter(
                id__in=transaction_ids
            ).filter(
                Q(payer_id=request.user.id) | Q(transactionparticipant__user_id=request.user.id)
            ).distinct()

            paginator = Paginator(queryset, limit)
            page_object = paginator.get_page(page)
            entries = list(page_object.object_list)

            for txn in entries:
                transaction_data.append(txn.get_transaction_data())

            has_more = page_object.has_next()

            response_data = {
                "transactions": transaction_data,
                "has_more": has_more,
            }
            return Response(response_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
