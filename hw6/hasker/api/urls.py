# -*- coding: utf-8 -*-
from django.conf.urls import url
from rest_framework_jwt.views import obtain_jwt_token, refresh_jwt_token, verify_jwt_token

from . import views


app_name = 'api'
urlpatterns = [
    url(r'^$', views.api_root),
    url(r'^questions/$', views.QuestionList.as_view(), name='question-list'),
    url(r'^questions/(?P<pk>[0-9]+)$', views.QuestionDetail.as_view(), name='question-detail'),
    url(r'^questions/(?P<pk>[0-9]+)/answers/$', views.AnswerList.as_view(), name='answer-list'),
    url(r'^trending/$', views.TopQuestionList.as_view(), name='trending-list'),
    url(r'^search/$', views.SearchList.as_view(), name='search-list'),
    url(r'^token-auth/$', obtain_jwt_token, name='token-auth'),
    url(r'^token-refresh/$', refresh_jwt_token, name='token-refresh'),
    url(r'^token-verify/$', verify_jwt_token, name='token-verify'),
]
