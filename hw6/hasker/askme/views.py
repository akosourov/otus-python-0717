# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseBadRequest
from django.urls import reverse
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.views.decorators.http import require_POST, require_safe, require_http_methods
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User

from .forms import QuestionForm, UserProfileForm, LoginForm
from .models import Question, Tag, Answer


@require_safe
def index(request):
    # todo пагинация
    questions_list = Question.objects.all().order_by('-date_pub', '-votes')
    paginator = Paginator(questions_list, 20)

    page = request.GET.get('page')
    try:
        questions = paginator.page(page)
    except PageNotAnInteger:
        questions = paginator.page(1)
    except EmptyPage:
        questions = paginator.page(paginator.num_pages)

    return render(request, 'askme/index.html', {
        'questions': questions
    })


def ask(request):
    if request.method == 'POST':
        form = QuestionForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            quest_params = {
                'title': cd['title'],
                'text': cd['text'],
                'user_id': request.user.pk
            }
            question = Question.objects.create(**quest_params)

            if cd.get('tags'):
                tag_names = cd['tags']
                tags = []
                for tag_name in tag_names:
                    tag, _ = Tag.objects.get_or_create(name=tag_name)
                    tags.append(tag)
                question.tags.add(*tags)
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

    answer_list = question.answer_set.all().order_by('-votes')
    paginator = Paginator(answer_list, 30)

    page = request.GET.get('page')
    try:
        answers = paginator.page(page)
    except PageNotAnInteger:
        answers = paginator.page(1)
    except EmptyPage:
        answers = paginator.page(paginator.num_pages)
    return render(request, 'askme/question.html', {
        'question': question,
        'answers': answers
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


def search_tag(request, tag_name):
    questions = []
    tag = Tag.objects.filter(name=tag_name).first()
    if tag:
        questions = tag.question_set.all()
    return render(request, 'askme/search.html', {
        'questions': questions,
        'head_title': 'Tag results',
        'search_query': 'tag:{}'.format(tag_name)
    })


@require_safe
def search(request):
    query = request.GET.get('q')
    return render(request, 'askme/search.html', {
        'questions': [],
        'head_title': 'Search results'
    })


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


def answer_vote(request, answer_id, to_up):
    if not request.user.is_authenticated:
        return HttpResponseBadRequest()
    answer = Answer.objects.filter(pk=answer_id).first()
    if not answer:
        return HttpResponseBadRequest()

    user_id = request.user.pk
    if to_up:
        answer.vote_up(user_id)
    else:
        answer.vote_down(user_id)

    # Возвращаем общее кол-во голосов
    return HttpResponse(answer.votes)


@require_POST
def answer_vote_up(request, answer_id):
    return answer_vote(request, answer_id, to_up=True)


@require_POST
def answer_vote_down(request, answer_id):
    return answer_vote(request, answer_id, to_up=False)


def question_vote(request, question_id, to_up):
    if not request.user.is_authenticated:
        return HttpResponseBadRequest()
    question = Question.objects.filter(pk=question_id).first()
    if not question:
        return HttpResponseBadRequest()

    user_id = request.user.pk
    if to_up:
        question.vote_up(user_id)
    else:
        question.vote_down(user_id)

    # Возвращаем общее кол-во голосов
    return HttpResponse(question.votes)


@require_POST
def question_vote_up(request, question_id):
    return question_vote(request, question_id, True)


@require_POST
def question_vote_down(request, question_id):
    return question_vote(request, question_id, False)


@require_POST
def set_correct_answer(request, answer_id):
    if not request.user.is_authenticated:
        return HttpResponseBadRequest()

    answer = Answer.objects.filter(pk=answer_id).first()
    if not answer:
        return HttpResponseBadRequest()

    answer.question.correct_answer = answer
    answer.question.save()
    return HttpResponse(answer.question.correct_answer_id)
