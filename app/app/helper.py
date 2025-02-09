from rest_framework_simplejwt.tokens import RefreshToken
from app.response_codes import RESPONSE_CODES
from rest_framework.exceptions import ValidationError


class Helper:

    @staticmethod
    def get_tokens_for_user(user) -> dict:
        """Generate Tokens manually"""

        refresh = RefreshToken.for_user(user)

        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }

    @staticmethod
    def raise_validation_error(error_key, extra_data=None):
        """
        Raises a ValidationError with structured error data.
        """
        error_info = RESPONSE_CODES.get(error_key, {})
        error_data = {
            "status": "failure",
            "error_code": error_info.get("code"),
            "response_key": error_key,
            "description": error_info.get("message")
        }
        if extra_data:
            sanitized_extra_data = {key: str(value) for key, value in extra_data.items()}
            error_data.update(sanitized_extra_data)
        raise ValidationError(error_data)

    @staticmethod
    def format_error_response(error_key, extra_data=None):
        """
        Returns a structured error response dictionary.
        """
        error_info = RESPONSE_CODES.get(error_key, {})
        response_code = error_info.get("code")
        error_data = {
            "status": "failure" if response_code.startswith("E") else "success",
            "is_success": False if response_code.startswith("E") else True,
            "response_code": response_code,
            "response_key": error_key,
            "description": error_info.get("message")
        }
        if extra_data:
            sanitized_extra_data = {key: str(value) for key, value in extra_data.items()}
            error_data.update(sanitized_extra_data)
        return error_data
