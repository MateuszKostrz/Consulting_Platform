from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
# from website.views import robots_txt


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('website.urls')),
    path('ckeditor/', include('ckeditor_uploader.urls')),
    path("accounts/", include("allauth.urls")),
    path("", include("website.urls"))
    # path('robots.txt', robots_txt),
]

# Serve static and media files during development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
