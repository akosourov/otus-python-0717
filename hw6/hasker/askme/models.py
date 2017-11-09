# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, transaction
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from django.forms import ModelForm


User = get_user_model()


class Tag(models.Model):
    name = models.CharField(max_length=20, unique=True)


class Question(models.Model):
    title = models.CharField(max_length=200)
    text = models.TextField()
    date_pub = models.DateField(auto_now_add=True)
    slug = models.SlugField(unique=True)
    user = models.ForeignKey(User)
    tags = models.ManyToManyField(Tag)
    votes = models.IntegerField(default=0)
    correct_answer = models.ForeignKey('Answer', null=True, blank=True, related_name='correct_answer')

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
            # todo решить проблему одинаковых title
        super(Question, self).save(*args, **kwargs)

    @transaction.atomic
    def vote_up(self, user_id):
        vote = self.uservote_set.filter(user_id=user_id).first()
        if not vote:
            self._add_vote(user_id, 1)
        elif vote and vote.value < 0:
            self._revert_vote(vote, 1)

    @transaction.atomic
    def vote_down(self, user_id):
        vote = self.uservote_set.filter(user_id=user_id).first()
        if not vote:
            self._add_vote(user_id, -1)
        elif vote and vote.value > 0:
            self._revert_vote(vote, -1)

    def _add_vote(self, user_id, value):
        self.uservote_set.create(user_id=user_id, question_id=self.pk, value=value)
        self.votes += value
        self.save()

    def _revert_vote(self, vote, value):
        vote.delete()
        self.votes += value
        self.save()


class Answer(models.Model):
    text = models.TextField()
    date = models.DateField(auto_now_add=True)
    question = models.ForeignKey(Question)
    user = models.ForeignKey(User)
    votes = models.IntegerField(default=0)

    @transaction.atomic
    def vote_up(self, user_id):
        vote = self.uservote_set.filter(user_id=user_id).first()
        if not vote:
            self._add_vote(user_id, 1)
        elif vote and vote.value < 0:
            self._revert_vote(vote, 1)

    @transaction.atomic
    def vote_down(self, user_id):
        vote = self.uservote_set.filter(user_id=user_id).first()
        if not vote:
            self._add_vote(user_id, -1)
        elif vote and vote.value > 0:
            self._revert_vote(vote, -1)

    def _add_vote(self, user_id, value):
        self.uservote_set.create(user_id=user_id, answer_id=self.pk, value=value)
        self.votes += value
        self.save()

    def _revert_vote(self, vote, value):
        vote.delete()
        self.votes += value
        self.save()

    def is_correct(self):
        return self.question.correct_answer.pk == self.pk


class UserVote(models.Model):
    user = models.ForeignKey(User)
    value = models.IntegerField()  # -1 or 1
    answer = models.ForeignKey(Answer, blank=True, null=True, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, blank=True, null=True, on_delete=models.CASCADE)
