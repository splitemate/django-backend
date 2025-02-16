from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from user.renderers import UserRenderer
from transaction.models import Transaction
from transaction.serializers import (
    AddTransactionSerializer,
    ModifyTransactionSerializer
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
