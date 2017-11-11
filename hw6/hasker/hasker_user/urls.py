from django.conf.urls import url

from . import views


app_name = 'hasker_user'
urlpatterns = [
    url(r'^settings/$', views.settings, name='settings'),
]