from django.conf.urls import url

from . import views


app_name = 'askme'
urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^ask/$', views.ask, name='ask'),
    url(r'^question/(.+)/$', views.question_detail, name='question'),
    url(r'^tag/(.+)/$', views.search_tag, name='search_tag'),
    url(r'^search/$', views.search, name='search'),
    url(r'^api_common/answer/setcorrect/([0-9]+)/$', views.set_correct_answer, name='set_correct'),
    url(r'^api_common/answer/voteup/([0-9]+)/$', views.answer_vote_up),
    url(r'^api_common/answer/votedown/([0-9]+)/$', views.answer_vote_down),
    url(r'^api_common/question/voteup/([0-9]+)/$', views.question_vote_up),
    url(r'^api_common/question/votedown/([0-9]+)/$', views.question_vote_down),
]