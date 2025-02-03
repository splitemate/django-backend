from rest_framework import serializers
from otp.models import OTPRequestReason

class OTPValidateSerializer(serializers.Serializer):
    user_id = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)
    code = serializers.CharField(max_length=4, required=True)
    reason = serializers.ChoiceField(choices=OTPRequestReason.choices, required=True)

    def validate(self, data):
        if not data.get('user_id') and not data.get('email'):
            raise serializers.ValidationError("Either user id or email must be provided.")
        return data

class OTPRequestSerializer(serializers.Serializer):
    user_id = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)
    reason = serializers.ChoiceField(choices=OTPRequestReason.choices, required=True)

    def validate(self, data):
        if not data.get('user_id') and not data.get('email'):
            raise serializers.ValidationError("Either user id or email must be provided.")
        return data
