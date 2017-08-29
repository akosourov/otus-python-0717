# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.forms import ModelForm


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    photo = models.ImageField(upload_to='photo/', null=True, blank=True)


class Tag(models.Model):
    name = models.CharField(max_length=20)


class Question(models.Model):
    title = models.CharField(max_length=200)
    text = models.TextField()
    date_pub = models.DateField(auto_now=True)
    slug = models.SlugField(unique=True)
    user = models.ForeignKey(User)
    tags = models.ManyToManyField(Tag)
    # todo лайки (+/-) от пользователей

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
            # todo решить проблему одинаковых title
        super(Question, self).save(*args, **kwargs)


class Answer(models.Model):
    text = models.TextField()
    date = models.DateField(auto_now=True)
    is_correct = models.BooleanField(default=False)
    question = models.ForeignKey(Question)
    user = models.ForeignKey(User)

    def get_sum_votes(self):
        return sum([v.value for v in self.answeruservote_set.all()])


class AnswerUserVote(models.Model):
    answer = models.ForeignKey(Answer, on_delete=models.CASCADE)
    user = models.ForeignKey(User)
    value = models.IntegerField()  # -1 of 1
    # todo unique answer and user
