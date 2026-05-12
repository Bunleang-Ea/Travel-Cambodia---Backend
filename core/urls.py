from django.contrib import admin
from django.urls import path, include
# --- ADD THESE TWO IMPORTS ---
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')), # Link to your api app
]
# --- ADD THIS BLOCK AT THE VERY BOTTOM ---
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)