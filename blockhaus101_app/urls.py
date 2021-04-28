from django.urls import re_path
from django.views.generic import RedirectView, TemplateView

from . import views


urlpatterns = [
	re_path(r"^(?P<lang>fr|en)/$", views.index, name="index"),
	re_path(
		r"^(?P<lang>fr|en)/past-exhibitions/$",
		views.past_exhibitions,
		name="past_exhibitions",
	),
	re_path(r"^(?P<lang>fr|en)/infos-pratiques/$", views.pratique, name="pratique"),

	# Old redirects
	re_path(
		r"^$",
		RedirectView.as_view(pattern_name="index", permanent=True),
	),
	re_path(
		r"^past-exhibitions/$",
		RedirectView.as_view(pattern_name="past_exhibitions", permanent=True),
	),
	re_path(
		r"^infos-pratiques/$",
		RedirectView.as_view(pattern_name="pratique", permanent=True),
	),

	re_path(r"^build_json/$", views.build_json, name="build_json"),

	# robots.txt
	re_path(r"^robots\.txt$", TemplateView.as_view(template_name="robots.txt")),

	# sitemap.xml
	re_path(r"^sitemap\.xml$", TemplateView.as_view(template_name="sitemap.xml")),

	re_path(
		r"^(?P<lang>fr|en)/(?P<slug>[-\w]+)/$", views.exhibition, name="exhibition"
	),
]
