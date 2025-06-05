from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin101/", admin.site.urls),
    path("", include("blockhaus101_app.urls")),
    path("captcha/", include("captcha.urls")),
]

# Serve static/media files regardless of DEBUG mode since we don't have Nginx inside the container
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [
        path("__debug__/", include(debug_toolbar.urls)),
    ]
