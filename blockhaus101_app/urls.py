from django.urls import re_path
from django.views.generic import RedirectView, TemplateView

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
    # New URLS with language param
    re_path(r"^(?P<lang>fr|en)/$", views.index, name="index"),
    re_path(
        r"^(?P<lang>fr|en)/past-exhibitions/$",
        views.past_exhibitions,
        name="past_exhibitions",
    ),
    re_path(r"^(?P<lang>fr|en)/contact/$", views.contact, name="contact"),
    # robots.txt
    re_path(r"^robots\.txt$", TemplateView.as_view(template_name="robots.txt")),
    # sitemap.xml
    re_path(r"^sitemap\.xml$", TemplateView.as_view(template_name="sitemap.xml")),
    re_path(r"^(?P<slug>[-\w]+)/$", views.exhibition, name="exhibition"),
]
