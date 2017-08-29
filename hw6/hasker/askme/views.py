# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseBadRequest
from django.urls import reverse
from django.views.decorators.http import require_POST, require_safe, require_http_methods
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User

from .forms import QuestionForm, UserProfileForm, LoginForm
from .models import Question, Tag, AnswerUserVote, Answer


def index(request):
    # todo Сортировка, пагинация
    top_questions = Question.objects.all()
    return render(request, 'askme/index.html', {
        'questions': top_questions,
        'user': request.user
    })


def ask(request):
    if request.method == 'POST':
        form = QuestionForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            quest_params = {
                'title': cd['title'],
                'text': cd['text'],
                'user_id': 1
            }
            question = Question.objects.create(**quest_params)

            if cd.get('tags'):
                tags = cd['tags'].split(',')
                new_tags = []
                for tag in tags:
                    tag = tag.strip()
                    if not Tag.objects.filter(name=tag).exists():
                        new_tag = Tag.objects.create(name=tag)
                        new_tags.append(new_tag)
                question.tags.add(*new_tags)
            return HttpResponseRedirect('/')
    else:
        # Создаем пустую форму Question и отдаем ее в шаблон
        form = QuestionForm()
    return render(request, 'askme/ask.html', {
        'form': form,
        'hide_ask_btn': True
    })


@require_http_methods('POST, GET')
def question_detail(request, slug):
    question = get_object_or_404(Question, slug=slug)
    if request.method == 'POST':
        # Добавим ответ к этому вопросу
        answer_text = request.POST.get('text')
        if answer_text:
            if request.user.is_authenticated:
                question.answer_set.create(text=answer_text, user=request.user)
                # todo send email to author of question
                return HttpResponseRedirect(reverse('askme:question', args=(slug,)))

    return render(request, 'askme/question.html', {
        'question': question,
        'answers': question.answer_set.all()  # todo пагинация
    })


def signup(request):
    if request.method == 'POST':
        # Создание пользователя
        user_form = UserProfileForm(request.POST)
        if user_form.is_valid():
            cd = user_form.cleaned_data
            if User.objects.filter(username=cd['username']).exists():
                # todo Ошибку в форму
                return HttpResponse('Пользователь с таким имененм уже существует')

            user = User.objects.create_user(username=cd['username'],
                                            email=cd['email'],
                                            password=cd['password'])

            # todo UserProfile с фото
            user = authenticate(request, username=cd['username'], password=cd['password'])
            if user is not None:
                login(request, user)
            return HttpResponseRedirect(reverse('askme:index'))
    else:
        user_form = UserProfileForm()
    return render(request, 'askme/signup.html', {'form': user_form})


@require_http_methods('POST, GET')
def login_view(request):
    if request.method == 'POST':
        login_form = LoginForm(request.POST)
        if login_form.is_valid():
            cd = login_form.cleaned_data
            user = authenticate(request, username=cd['username'], password=cd['password'])
            if user:
                login(request, user)
                return HttpResponseRedirect(reverse('askme:index'))
            else:
                login_form.errors['password'] = ['Incorrect password']
    else:
        login_form = LoginForm()
    return render(request, 'askme/login.html', {
        'form': login_form,
        'user': request.user
    })


def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse('askme:index'))


def answer_vote_up(request, answer_id):
    if request.user.is_authenticated:
        user_id = request.user.pk
        vote = AnswerUserVote.objects.filter(user=user_id, answer=answer_id).first()
        if not vote:
            AnswerUserVote.objects.create(user_id=user_id, answer_id=answer_id, value=1)
        elif vote.value == -1:
            vote.delete()

        # Возвращаем общее кол-во голосов
        answer = Answer.objects.get(pk=answer_id)
        votes = answer.get_sum_votes()
        return HttpResponse(votes)

    return HttpResponseBadRequest()


def answer_vote_down(request, answer_id):
    if request.user.is_authenticated:
        user_id = request.user.pk
        vote = AnswerUserVote.objects.filter(user=user_id, answer=answer_id).first()
        if not vote:
            AnswerUserVote.objects.create(user_id=user_id, answer_id=answer_id, value=-1)
        elif vote.value == 1:
            vote.delete()

        # Возвращаем общее кол-во голосов
        answer = Answer.objects.get(pk=answer_id)
        votes = answer.get_sum_votes()
        return HttpResponse(votes)

    return HttpResponseBadRequest()
