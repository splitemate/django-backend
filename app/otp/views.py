from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from otp.models import OTP
from app.helper import Helper
from django.contrib.auth import get_user_model
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from otp.serializers import OTPValidateSerializer, OTPRequestSerializer
from otp.exceptions import OTPCreationLimitExceeded
from transaction.models import UserBalance


class OTPRequestView(APIView):
    """ Request a OTP """

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = OTPRequestSerializer(data=request.data)
        if serializer.is_valid():
            user_id = serializer.validated_data.get('user_id')
            email = serializer.validated_data.get('email')
            reason = serializer.validated_data.get('reason')

            try:
                User = get_user_model()
                if email:
                    user = User.objects.get(email=email)
                else:
                    user = User.objects.get(id=user_id)
                OTP.create_or_resend_otp(user, reason)
                return Response({'message': 'OTP sent successfully.'}, status=status.HTTP_200_OK)
            except User.DoesNotExist:
                return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
            except OTPCreationLimitExceeded:
                return Response({'error': 'OTP request limit reached. Please try again later.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)
            except Exception as e:
                return Response({'error': 'Something went wrong.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class OTPValidateView(APIView):
    """ Validate all OTP """

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = OTPValidateSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data.get('email')
            user_id = serializer.validated_data.get('user_id')
            code = serializer.validated_data.get('code')
            reason = serializer.validated_data.get('reason')
            try:
                User = get_user_model()
                if email:
                    user = User.objects.get(email=email)
                else:
                    user = User.objects.get(id=user_id)
                otps = OTP.objects.filter(user=user, code=code, reason=reason, is_used=False)
                for otp in otps:
                    if otp.is_valid():
                        otps.update(is_used=True)
                        responseDict = {'message': 'OTP is valid'}
                        if reason == "PR":
                            uid = urlsafe_base64_encode(force_bytes(user.id))
                            token = PasswordResetTokenGenerator().make_token(user)
                            responseDict.update({'token': token, 'uid': uid})
                        elif reason == "EV":
                            token = Helper.get_tokens_for_user(user=user)
                            responseDict.update({
                                'id': str(user.id),
                                'name': user.name,
                                'email': user.email,
                                'image_url': user.image_url,
                                'tokens': token,
                                'balance': UserBalance.get_user_balance(user.id)
                            })
                            user.is_email_verified = True
                            user.save()
                        return Response(responseDict, status=status.HTTP_200_OK)
                return Response({'error': 'Invalid or expired OTP'}, status=status.HTTP_404_NOT_FOUND)
            except User.DoesNotExist:
                return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
