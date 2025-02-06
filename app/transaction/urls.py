"""
URL Mapping for Transaction API.
"""
from django.urls import path
from transaction import views

app_name = "transaction"


urlpatterns = [
    path("add-transaction", views.AddTransactionView.as_view(), name="add_transaction"),
    path("modify-transaction/<str:pk>", views.ModifyTransactionView.as_view(), name="modify_transaction"),
]
