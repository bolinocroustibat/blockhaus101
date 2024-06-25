from django.conf import settings
from django.contrib import admin
from django.urls import include, re_path

urlpatterns = [
    re_path(r"^admin101/", admin.site.urls),
    re_path(r"^", include("blockhaus101_app.urls")),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [
        re_path(r"^__debug__/", include(debug_toolbar.urls)),
    ]
