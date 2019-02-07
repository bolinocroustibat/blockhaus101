from django.conf.urls import include, url
from . import views
from django.views.generic import TemplateView

urlpatterns = ([
	url(r'^$', views.index, name='index'),
	url(r'^past-exhibitions/$', views.past_exhibitions, name='past_exhibitions'),
	url(r'^infos-pratiques/$', views.pratique, name="pratique"),
	url(r'^(?P<slug>[-\w]+)/$',views.exhibition, name='exhibition'),

	# tests (now we use tests and commands)
	# url(r'^build_json/$',views.build_json, name='build_json'),
	# url(r'^test-exhibition/$', views.test_exhibition, name='test_exhibition'),
	# url(r'^test-tweet/$', views.test_tweet, name='test_tweet'),

	# robots.txt
	url(r'^robots\.txt$', TemplateView.as_view(template_name='robots.txt')),
	# sitemap.xml
	url(r'^sitemap\.xml$', TemplateView.as_view(template_name='sitemap.xml')),
])