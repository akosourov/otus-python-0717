from django.conf.urls import url

from . import views


app_name = 'hasker_user'
urlpatterns = [
    url(r'^login/$', views.login_view, name='login'),
    url(r'^logout/$', views.logout_view, name='logout'),
    url(r'^settings/$', views.settings, name='settings'),
    url(r'^signup/$', views.signup, name='signup'),
]