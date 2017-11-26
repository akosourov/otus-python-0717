# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from askme.models import Question


User = get_user_model()

API_QUESTION_LIST = reverse('api:question-list')
API_TOKEN_AUTH = reverse('api:token-auth')
API_TOKEN_REFRESH = reverse('api:token-refresh')
API_TOKEN_VERIFY = reverse('api:token-verify')
BAD_TOKEN = 'BAD_TOKEN'
USERNAME = 'user'
USER_PASSWORD = 'password'

credentials = {
    'username': USERNAME,
    'password': USER_PASSWORD
}


def create_test_user():
    return User.objects.create_user(USERNAME, 'test@test.com', USER_PASSWORD)


def obtain_token():
    client = APIClient()
    resp = client.post(API_TOKEN_AUTH, credentials, format='json')
    return resp.json()['token']


class JWTAuth(APITestCase):
    def setUp(self):
        self.user = create_test_user()

    def test_obtain_token(self):
        token = obtain_token()
        self.assertTrue(len(token) > 0)

    def test_refresh_token(self):
        token = obtain_token()
        resp = self.client.post(API_TOKEN_REFRESH, {'token': token}, format='json')
        new_token = resp.json()['token']
        self.assertTrue(len(new_token) > 0)
        # self.assertNotEqual(token, new_token)

    def test_verify_token(self):
        token = obtain_token()
        resp = self.client.post(API_TOKEN_VERIFY, {'token': token}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_verify_bad_token(self):
        resp = self.client.post(API_TOKEN_VERIFY, {'token': BAD_TOKEN}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class QuestionsAPI(APITestCase):
    questions_raw = [
        {'title': 'title_1', 'text': 'text_1'},
        {'title': 'title_2', 'text': 'text_2'},
        {'title': 'title_3', 'text': 'text_3'},
    ]

    def setUp(self):
        self.user = create_test_user()
        for q in self.questions_raw:
            Question.objects.create(title=q['title'], text=q['text'], user=self.user)

    def test_unauthorized_401(self):
        resp = self.client.get(API_QUESTION_LIST)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authorized_user_can_get_list(self):
        token = obtain_token()
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + token)
        resp = self.client.get(API_QUESTION_LIST)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        questions_count = resp.json()['count']
        self.assertEqual(questions_count, Question.objects.count())

    def test_create_question(self):
        token = obtain_token()
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + token)
        resp = self.client.post(API_QUESTION_LIST, {'title': 'title_4', 'text': 'text_4'})
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(self.questions_raw) + 1, Question.objects.count())
