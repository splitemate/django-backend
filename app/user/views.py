"""
Views for the user API.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from user.serializers import (
    UserRegisterSerializers,
    UserLoginSerializers,
    UserProfileSerializer,
    UserPasswordChangeSerializer,
    UserForgotPasswordSerializer,
    UserResetPasswordSerializer,
    ContinueWithGoogleSerializer
)
from app.helper import Helper
from django.contrib.auth import get_user_model
from user.renderers import UserRenderer
from django.contrib.auth import authenticate
from django.http import Http404
from otp.models import OTP, OTPRequestReason
from transaction.models import UserBalance


class CreateUserView(APIView):
    """Create a new user in system"""

    renderer_classes = [UserRenderer]

    def post(self, request):
        serializer = UserRegisterSerializers(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            try:
                OTP.create_or_resend_otp(user, OTPRequestReason.EMAIL_VERIFICATION)
            except Exception:
                return Response({"message": "Unable to send OTP"}, status=status.HTTP_400_BAD_REQUEST)
            data = {
                "id": str(user.id),
                "name": user.name,
                "email": user.email,
                "image_url": user.image_url,
                "balance": UserBalance.get_user_balance(user.id)
            }
            return Response({"message": "Registration successful", "user_data": data}, status=status.HTTP_201_CREATED)
        else:
            if "email" in serializer.errors:
                return Response(serializer.errors, status=status.HTTP_409_CONFLICT)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserLoginView(APIView):
    """Login for existing users"""

    renderer_classes = [UserRenderer]

    def post(self, requests, format=None):
        serializer = UserLoginSerializers(data=requests.data)
        if serializer.is_valid(raise_exception=True):
            email = serializer.data.get("email")
            password = serializer.data.get("password")
            user = authenticate(email=email, password=password)
            if user is not None:
                data = {
                    "id": str(user.id),
                    "name": user.name,
                    "email": user.email,
                    "image_url": user.image_url,
                    "balance": UserBalance.get_user_balance(user.id)
                }
                message = "Login successful"
                token = Helper.get_tokens_for_user(user=user)
                status_code = status.HTTP_200_OK
                if not user.is_email_verified:
                    try:
                        OTP.create_or_resend_otp(user, OTPRequestReason.EMAIL_VERIFICATION)
                    except Exception:
                        return Response({message: "OTP Limit Exceed"}, status=status.HTTP_400_BAD_REQUEST)
                    status_code = status.HTTP_403_FORBIDDEN
                    message = "Email is not verified yet"
                    token = ""
                return Response(
                    {"message": message, "tokens": token, "user_data": data},
                    status=status_code
                )
            else:
                return Response(
                    {"error": ["Email or Password is not valid"]},
                    status=status.HTTP_401_UNAUTHORIZED,
                )


class ContinueWithGoogle(APIView):
    """ Continue with Google APIs """
    renderer_classes = [UserRenderer]

    def post(self, requests, format=None):
        serializer = ContinueWithGoogleSerializer(data=requests.data)
        if serializer.is_valid():
            validated_data = serializer.validated_data
            email = validated_data.get('email')
            name = validated_data.get('name')
            source = validated_data.get('user_source')

            user, created = get_user_model().objects.get_or_create(
                    email=email,
                    defaults={
                        'name': name,
                        'is_email_verified': True,
                        'user_source': source
                    }
            )

            tokens = Helper.get_tokens_for_user(user)
            message = "User created successfully" if created else "User already exists"

            return Response({
                    "message": message,
                    "user_data": {
                        "id": str(user.id),
                        "name": user.name,
                        "email": user.email,
                        "image_url": user.image_url,
                        "balance": UserBalance.get_user_balance(user.id)
                    },
                    "tokens": tokens
                }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(APIView):
    """Profile"""

    renderer_classes = [UserRenderer]
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserPasswordChange(APIView):
    """Change current user's password"""

    renderer_classes = [UserRenderer]
    permission_classes = [IsAuthenticated]

    def patch(self, requests, format=None):
        serializer = UserPasswordChangeSerializer(
            data=requests.data, context={"user": requests.user}
        )
        if serializer.is_valid(raise_exception=True):
            return Response(
                {"message": "Password changed successfully."}, status=status.HTTP_200_OK
            )
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserForgotPassword(APIView):
    """Forgot Password for user"""

    renderer_classes = [UserRenderer]

    def post(self, requests, format=None):
        serializer = UserForgotPasswordSerializer(data=requests.data)
        try:
            if serializer.is_valid(raise_exception=True):
                serializer.save()
                return Response(
                    {"message": "OTP is send to registered email"},
                    status=status.HTTP_200_OK,
                )
        except Http404:
            return Response({"error": "user not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception:
            return Response({"error": "Something went wrong. Please try again."}, status=status.HTTP_400_BAD_REQUEST)


class UserResetPassword(APIView):
    """Reset Password with tokens"""

    renderer_classes = [UserRenderer]

    def patch(self, requests):
        serializer = UserResetPasswordSerializer(data=requests.data)
        if serializer.is_valid(raise_exception=True):
            return Response(
                {"message": "Password changed successfully."},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)


class AddFriend(APIView):
    """Create connectrion between 2 friends"""

    renderer_classes = [UserRenderer]
    permission_classes = [IsAuthenticated]

    def post(self, request, token):
        try:
            user_model = get_user_model()
            friend = user_model.objects.get(invite_token=token)
        except Exception:
            return Response({'error': 'Invalid or expired token.'}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        if user == friend:
            return Response({'error': 'You cannot add yourself as a friend.'}, status=status.HTTP_400_BAD_REQUEST)
        user.friends.add(friend)

        return Response({'message': 'Friend added successfully.'}, status=status.HTTP_200_OK)
