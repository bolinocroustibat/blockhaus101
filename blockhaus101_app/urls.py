from django.conf.urls import include, url
from . import views
from django.views.generic import TemplateView

urlpatterns = ([
	url(r'^$', views.index, name='index'),
	url(r'^past-exhibitions/$', views.past_exhibitions, name='past_exhibitions'),
    url(r'^manifeste/$', TemplateView.as_view(template_name="manifeste.html"), name='manifesto'),
	url(r'^test_exhibition/$', views.test_exhibition, name='test_exhibition'),
	url(r'^build_json/$',views.build_json, name='build_json'),
	#url(r'^test/$', views.test, name='test'),
	url(r'^(?P<slug>[-\w]+)/$',views.exhibition, name='exhbition'),
])