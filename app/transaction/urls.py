"""
URL Mapping for Transaction API.
"""
from django.urls import path
from transaction import views

app_name = "transaction"


urlpatterns = [
    path("add-transaction", views.AddTransactionView.as_view(), name="add_transaction"),
    path("modify-transaction/<str:pk>", views.ModifyTransactionView.as_view(), name="modify_transaction"),
    path("get-transaction/<str:pk>", views.GetExistingTransactionView.as_view(), name="get_transaction"),
    path("delete-transaction/<str:pk>", views.DeleteTransactionView.as_view(), name="delete_transaction"),
    path("restore-transaction/<str:pk>", views.RestoreTransactionView.as_view(), name="restore_transaction"),
    path("get-bulk", views.GetBulkTransactionView.as_view(), name="get_bulk_transaction"),
]
