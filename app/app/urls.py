from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/schema/', SpectacularAPIView.as_view(), name='api-schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='api-schema'), name='api-docs'),
    path('api/user/', include(('user.urls', 'user'), namespace='api_user')),
    path('add_friend/', include(('user.urls', 'user'), namespace='add_friend')),
    path('api/otp/', include(('otp.urls', 'otp'), namespace='otp')),
    path('api/transaction/', include(('transaction.urls', 'transaction'), namespace='transaction')),
]
