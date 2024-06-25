from django.urls import include, path, re_path
from django.views.generic import RedirectView

from blockhaus101_app import views

urlpatterns = [
    # Old redirects
    re_path(
        r"^$",
        RedirectView.as_view(url="/fr", permanent=True),
    ),
    re_path(
        r"^past-exhibitions/$",
        RedirectView.as_view(url="/fr/past-exhibitions", permanent=True),
    ),
    re_path(
        r"^infos-pratiques/$",
        RedirectView.as_view(url="/fr/contact", permanent=True),
    ),
    # Language-independent URLs
    path("captcha/", include("captcha.urls")),
    # # New URLS with language param
    # re_path(r"^(?P<lang>fr|en)/$", views.index, name="index"),
    # re_path(
    #     r"^(?P<lang>fr|en)/past-exhibitions/$",
    #     views.past_exhibitions,
    #     name="past_exhibitions",
    # ),
    # re_path(r"^(?P<lang>fr|en)/contact/$", views.contact, name="contact"),
    # Only French for now
    re_path(r"^(?P<lang>fr)/$", views.index, name="index"),
    re_path(
        r"^(?P<lang>fr)/past-exhibitions/$",
        views.past_exhibitions,
        name="past_exhibitions",
    ),
    re_path(r"^(?P<lang>fr)/contact/$", views.contact, name="contact"),
    re_path(r"^(?P<slug>[-\w]+)/$", views.exhibition, name="exhibition"),
]
