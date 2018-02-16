from django.conf.urls import include, url
from . import views

urlpatterns = ([
	url(r'^$', views.index, name='index'),
	url(r'^past_exhibitions$', views.past_exhibitions, name='past_exhibitions'),
	url(r'^generate$', views.generate, name='generate'),
	url(r'^build_json/$',views.build_json, name='build_json'),
	#url(r'^test/$', views.test, name='test'),
	url(r'^(?P<slug>[-\w]+)$',views.exhibition, name='exhbition'),
])