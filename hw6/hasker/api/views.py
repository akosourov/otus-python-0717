# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from rest_framework import viewsets, status, generics
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.views import APIView
from django.contrib.postgres.search import SearchVector
from django.shortcuts import get_object_or_404


from askme.models import Question
from .serializers import QuestionSerializer, AnswerSerializer
from .permissions import IsOwner


@api_view(['GET'])
def api_root(request):
    return Response({
        'questions': reverse('api:question-list', request=request),
        'trending': reverse('api:trending-list', request=request),
        'search': reverse('api:search-list', request=request),
    })


class QuestionList(generics.ListAPIView):
    queryset = Question.objects.all().order_by('-date_pub', '-votes')
    serializer_class = QuestionSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer)
            return Response(serializer.data, status.HTTP_201_CREATED)
        return Response(serializer.errors, status.HTTP_400_BAD_REQUEST)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class QuestionDetail(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (IsOwner,)
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer


class AnswerList(generics.ListAPIView):
    serializer_class = AnswerSerializer

    def get_queryset(self):
        question = get_object_or_404(Question, pk=self.kwargs.get('pk'))
        return question.answer_set.all()


# trending
class TopQuestionList(APIView):
    def get(self, request):
        queryset = Question.objects.order_by('-votes')[:20]
        serializers = QuestionSerializer(queryset, many=True)
        return Response(serializers.data)


class SearchList(generics.ListAPIView):
    serializer_class = QuestionSerializer

    def get_queryset(self):
        query = self.request.GET.get('q', '')
        if len(query) > 100:
            query = ''
        queryset = Question.objects.annotate(
            search=SearchVector('title', 'text')
        ).filter(search=query).all().order_by('-date_pub', '-votes')
        return queryset


