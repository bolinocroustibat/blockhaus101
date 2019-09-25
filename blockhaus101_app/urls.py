from django.urls import re_path
from django.views.generic import TemplateView

from . import views


urlpatterns = ([
	re_path(r'^$', views.index, name='index'),
	re_path(r'^past-exhibitions/$', views.past_exhibitions, name='past_exhibitions'),
	re_path(r'^infos-pratiques/$', views.pratique, name="pratique"),

	# tests (now we use tests and commands)
	# re_path(r'^test-exhibition/$', views.test_exhibition, name='test_exhibition'),
	# re_path(r'^test-tweet/$', views.test_tweet, name='test_tweet'),

	re_path(r'^build_json/$',views.build_json, name='build_json'),

	# robots.txt
	re_path(r'^robots\.txt$', TemplateView.as_view(template_name='robots.txt')),
	# sitemap.xml
	re_path(r'^sitemap\.xml$', TemplateView.as_view(template_name='sitemap.xml')),

	re_path(r'^(?P<slug>[-\w]+)/$',views.exhibition, name='exhibition'),

])