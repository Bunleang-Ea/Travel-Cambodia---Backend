from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponse, JsonResponse
from django.urls import path, include

from .views import api_schema_view, health_check, swagger_ui_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health/', health_check, name='health-check'),
    path('api/schema/', api_schema_view, name='api-schema'),
    path('api/docs/', swagger_ui_view, name='api-docs'),
    path('api/', include('api.urls')),
]

from django.urls import re_path
from django.conf import settings
from django.views.static import serve

urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]
