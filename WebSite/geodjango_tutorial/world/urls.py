from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.testmap, name='index'),
]
