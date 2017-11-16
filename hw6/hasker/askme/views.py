# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import transaction
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseBadRequest
from django.urls import reverse
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.views.decorators.http import require_POST, require_safe, require_http_methods
from django.contrib.auth import get_user_model
from django.contrib.postgres.search import SearchVector

from .forms import QuestionForm
from .models import Question, Tag, Answer


User = get_user_model()


@require_safe
def index(request):
    questions_list = Question.objects.all().order_by('-date_pub', '-votes')
    page = request.GET.get('page')
    questions = paginate(questions_list, page)
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
            with transaction.atomic():
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
    page = request.GET.get('page')
    answers = paginate(answer_list, page, 30)
    return render(request, 'askme/question.html', {
        'question': question,
        'answers': answers
    })


def search_tag(request, tag_name):
    tag = Tag.objects.filter(name=tag_name).first()
    if tag:
        questions_list = tag.question_set.all()
    else:
        questions_list = []
    page = request.GET.get('page')
    questions = paginate(questions_list, page)
    return render(request, 'askme/search.html', {
        'questions': questions,
        'head_title': 'Tag results',
        'search_query': 'tag:{}'.format(tag_name)
    })


@require_safe
def search(request):
    query = request.GET.get('q') or ''
    if len(query) > 100:
        # query too long. Return nothing
        questions_list = []
    else:
        questions_list = Question.objects.annotate(
            search=SearchVector('title', 'text')
        ).filter(search=query).all().order_by('-date_pub', '-votes')
    page = request.GET.get('page')
    questions = paginate(questions_list, page)
    return render(request, 'askme/search.html', {
        'questions': questions,
        'head_title': 'Search results'
    })


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

    return HttpResponse(answer.votes)  # total votes


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


def paginate(entity_list, page, per_page=20):
    paginator = Paginator(entity_list, per_page)
    try:
        entities = paginator.page(page)
    except PageNotAnInteger:
        entities = paginator.page(1)
    except EmptyPage:
        entities = paginator.page(paginator.num_pages)
    return entities
