"""
Serializers for user API View
"""
from django.contrib.auth import get_user_model
from rest_framework import serializers
from django.utils.encoding import smart_str, force_bytes, DjangoUnicodeDecodeError
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.exceptions import ValidationError
from django.http import Http404
from otp.models import OTP
from transaction.models import UserBalance


class UserRegisterSerializers(serializers.ModelSerializer):
    """Serializer for the user object"""

    email = serializers.EmailField()

    class Meta:
        model = get_user_model()
        fields = ["email", "password", "name"]
        extra_kwargs = {"password": {"write_only": True, "min_length": 8}}

    def validate_email(self, value):
        """Check if a user with this email already exists."""
        if get_user_model().objects.filter(email=value).exists():
            raise ValidationError("A user with this email already exists.")
        return value

    def create(self, validated_data):
        user = get_user_model().objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            name=validated_data['name']
        )
        return user


class UserLoginSerializers(serializers.ModelSerializer):
    """Serializers for user login"""

    email = serializers.EmailField(max_length=255)

    class Meta:
        model = get_user_model()
        fields = ["email", "password"]



class ContinueWithGoogleSerializer(serializers.ModelSerializer):
    """ Serializer for Google APIs """

    email = serializers.EmailField(required=True)
    name = serializers.CharField(required=True)
    user_source = serializers.CharField(required=True)
    image_url = serializers.URLField(required=False, allow_blank=True)

    class Meta:
        model = get_user_model()
        fields = ["email", "name", "user_source", "image_url"]
    
    def create(self, validated_data):
        """Create a user without requiring a password, typically used for Google sign-in."""
        user = get_user_model().objects.create(
            email=validated_data['email'],
            name=validated_data['name'],
            image_url=validated_data['image_url'],
        )
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile"""

    id = serializers.SerializerMethodField()
    balance = serializers.SerializerMethodField()

    class Meta:
        model = get_user_model()
        fields = ["id", "email", "name", "image_url", "balance"]

    def get_id(self, obj):
        return str(obj.id)
    
    def get_balance(self, obj):
        """Fetch user balance"""
        return UserBalance.get_user_balance(obj.id)



class UserPasswordChangeSerializer(serializers.ModelSerializer):
    """Serializer for change user password"""

    old_password = serializers.CharField(
        max_length=255, style={"input_type": "password"}, write_only=True
    )
    new_password = serializers.CharField(
        max_length=255, style={"input_type": "password"}, write_only=True
    )

    class Meta:
        model = get_user_model()
        fields = ["old_password", "new_password"]

    def validate(self, attrs):
        old_password = attrs.get("old_password")
        new_password = attrs.get("new_password")
        user = self.context.get("user")

        if not user.check_password(old_password):
            raise serializers.ValidationError("Old password is incorrect.")

        user.set_password(new_password)
        user.save()
        return attrs


class UserForgotPasswordSerializer(serializers.ModelSerializer):
    """Serializer for forgot password"""

    email = serializers.EmailField(max_length=255)

    class Meta:
        model = get_user_model()
        fields = ["email"]

    def validate(self, attrs):
        email = attrs.get("email")
        user = get_user_model().objects.filter(email=email).first()

        if not user:
            raise Http404("User not found.")
        
        attrs['user'] = user
        return attrs
        
    def create(self, validated_data):
        try:
            user = validated_data.get('user')
            OTP.create_or_resend_otp(user, 'PR')
        except Exception as e:
            raise ValidationError({"error": "Failed to send OTP. Please try again."})
        return validated_data


class UserResetPasswordSerializer(serializers.ModelSerializer):
    """Serializer for forgot password view"""

    password = serializers.CharField(
        max_length=255, style={"input_type": "password"}, write_only=True
    )
    uid = serializers.CharField(max_length=255)
    token = serializers.CharField(max_length=255)

    class Meta:
        model = get_user_model()
        fields = ["password", "uid", "token"]

    def validate(self, attrs):
        try:
            password = attrs.get("password")
            uid = attrs.get("uid")
            token = attrs.get("token")
            id = smart_str(urlsafe_base64_decode(uid))
            user = get_user_model().objects.get(id=id)
            if not PasswordResetTokenGenerator().check_token(user=user, token=token):
                raise ValidationError("Token is not valid or expired")
            user.set_password(password)
            user.save()
            return attrs
        except DjangoUnicodeDecodeError as indentifier:
            PasswordResetTokenGenerator().check_token(user=user, token=token)
            raise ValidationError("Token is not valid or expired")
