# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth import authenticate, login, logout, get_user_model
from django.http import HttpResponseRedirect
from django.shortcuts import render, reverse
from django.views.decorators.http import require_http_methods

from .forms import LoginForm, UserSettingsForm, SignUpForm


User = get_user_model()


@require_http_methods(['POST', 'GET'])
def login_view(request):
    if request.method == 'POST':
        login_form = LoginForm(request.POST)
        if login_form.is_valid():
            cd = login_form.cleaned_data
            user = authenticate(request, username=cd['username'],
                                password=cd['password'])
            if user:
                login(request, user)
                return HttpResponseRedirect(reverse('askme:index'))
            else:
                login_form.errors['password'] = ['Incorrect password']
    else:
        if request.user.is_authenticated:
            logout(request)
        login_form = LoginForm()
    return render(request, 'hasker_user/login.html', {
        'form': login_form,
        'user': request.user
    })


def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse('askme:index'))


@require_http_methods(['POST', 'GET'])
def settings(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse('askme:index'))

    user = request.user
    if request.method == 'POST':
        form = UserSettingsForm(request.POST, request.FILES)
        if form.is_valid():
            cd = form.cleaned_data
            user.email = cd['email']
            if cd['photo']:
                user.photo = cd['photo']
            user.save()
            return HttpResponseRedirect(reverse('askme:index'))
    else:
        form = UserSettingsForm({
            'username': user.username,
            'email': user.email
        })

    return render(request, 'hasker_user/user_settings.html', {
        'form': form,
        'photo_url': user.photo_url()
    })


@require_http_methods(['POST', 'GET'])
def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST, request.FILES)
        if form.is_valid():
            cd = form.cleaned_data
            if User.objects.filter(username=cd['username']).exists():
                form.errors['username'] = ['Username already exists']
            elif User.objects.filter(email=cd['email']).exists():
                form.errors['email'] = ['Email already exists']
            else:
                User.objects.create_user(username=cd['username'],
                                         email=cd['email'],
                                         password=cd['password'],
                                         photo=cd['photo'])
                user = authenticate(request, username=cd['username'],
                                    password=cd['password'])
                if user is not None:
                    login(request, user)
                return HttpResponseRedirect(reverse('askme:index'))
    else:
        form = SignUpForm()
    return render(request, 'hasker_user/signup.html', {'form': form})
