# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

from askme.models import Question


def create_test_user():
    return User.objects.create_user('test', 'test@test.com', 'test')


class VotingTestCase(TestCase):
    """Голосование за вопрос и ответ"""

    def setUp(self):
        self.user = create_test_user()
        self.question = Question.objects.create(title='title', text='text', user=self.user)
        self.answer = self.question.answer_set.create(text='text', user=self.user)

    def test_question_voting(self):
        """Пользоваель голосует за вопрос. Последующее голосование (в плюс)
        не учитывается. Может отменить голос, а также отрицательно проголосовать.
        """
        self.assertEqual(self.question.votes, 0)

        self.question.vote_up(self.user.pk)
        self.assertEqual(self.question.votes, 1)
        self.assertEqual(self.question.uservote_set.count(), 1)
        self.assertEqual(self.question.uservote_set.first().value, 1)

        self.question.vote_up(self.user.pk)
        self.assertEqual(self.question.votes, 1)
        self.assertEqual(self.question.uservote_set.count(), 1)

        self.question.vote_down(self.user.pk)
        self.assertEqual(self.question.votes, 0)
        self.assertEqual(self.question.uservote_set.count(), 0)

        self.question.vote_down(self.user.pk)
        self.assertEqual(self.question.votes, -1)
        self.assertEqual(self.question.uservote_set.count(), 1)
        self.assertEqual(self.question.uservote_set.first().value, -1)

    def test_answer_voting(self):
        self.assertEqual(self.answer.votes, 0)

        self.answer.vote_up(self.user.pk)
        self.assertEqual(self.answer.votes, 1)
        self.assertEqual(self.answer.uservote_set.count(), 1)
        self.assertEqual(self.answer.uservote_set.first().value, 1)

        self.answer.vote_up(self.user.pk)
        self.assertEqual(self.answer.votes, 1)
        self.assertEqual(self.answer.uservote_set.count(), 1)

        self.answer.vote_down(self.user.pk)
        self.assertEqual(self.answer.votes, 0)
        self.assertEqual(self.answer.uservote_set.count(), 0)

        self.answer.vote_down(self.user.pk)
        self.assertEqual(self.answer.votes, -1)
        self.assertEqual(self.answer.uservote_set.count(), 1)
        self.assertEqual(self.answer.uservote_set.first().value, -1)

    def test_answer_and_question_voting(self):
        """Голосование за вопрос и ответ не зависят друг от друга"""
        answer_votes_before = self.answer.votes
        self.question.vote_up(self.user.pk)
        self.assertEqual(answer_votes_before, self.answer.votes)

        question_votes_before = self.question.votes
        self.answer.vote_up(self.user.pk)
        self.assertEqual(question_votes_before, self.question.votes)


class AnswerAndQuestions(TestCase):
    def setUp(self):
        self.question_author = User.objects.create_user('test2', 'test@test.com', 'test')
        self.question = Question.objects.create(title='title', text='text', user=self.question_author)
        self.answer_user = User.objects.create_user('answerer', 'b@t.ru', 'qwe')
        self.answer = self.question.answer_set.create(text='text', user=self.answer_user)
        self.client = Client()

    def test_set_correct_not_login(self):
        # Не авторизованным - BadRequest 400
        response = self.client.post(reverse('askme:set_correct', args=(self.answer.pk,)))
        self.assertEqual(response.status_code, 400)

    def test_set_correct(self):
        self.client.login(username='test2', password='test')
        response = self.client.post(reverse('askme:set_correct', args=(self.answer.pk,)))
        self.assertEqual(response.status_code, 200)

        self.assertEqual(self.question.correct_answer_id, self.answer.pk)

