"""
URL Mapping for user API.
"""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from user import views


app_name = "user"

urlpatterns = [
    path("register", views.CreateUserView.as_view(), name="register"),
    path("login", views.UserLoginView.as_view(), name="login"),
    path("profile", views.UserProfileView.as_view(), name="profile"),
    path("change-password", views.UserPasswordChange.as_view(), name="change_password"),
    path("forgot-password", views.UserForgotPassword.as_view(), name="forgot_password"),
    path("reset-password", views.UserResetPassword.as_view(), name="reset_password"),
    path("token/refresh", TokenRefreshView.as_view(), name="token_refresh"),
    path("add-friend/<str:token>", views.AddFriend.as_view(), name='add_friend'),
    path("external-auth", views.ContinueWithGoogle.as_view(), name="O_auth")
]
