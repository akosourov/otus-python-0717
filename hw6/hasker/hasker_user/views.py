# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.http import HttpResponseRedirect
from django.shortcuts import render, reverse
from django.views.decorators.http import require_http_methods

from .forms import UserProfileForm
from .models import User


@require_http_methods('POST, GET')
def settings(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse('askme:index'))

    # user = User.objects.get(username=request.user.username)
    user = request.user
    if request.method == 'POST':
        user_form = UserProfileForm(request.POST, request.FILES)
        if user_form.is_valid():
            cd = user_form.cleaned_data
            user.email = cd['email']
            user.photo = cd['photo']
            user.save()
            return HttpResponseRedirect(reverse('askme:index'))
    else:
        user_form = UserProfileForm({
            'username': user.username,
            'email': user.email
        })

    return render(request, 'hasker_user/user_settings.html', {
        'form': user_form,
        'path': 'photo/photo.jpg'
    })
