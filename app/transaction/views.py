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
