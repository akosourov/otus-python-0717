from rest_framework import serializers

from askme.models import Question, Answer


class QuestionSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.username')
    slug = serializers.ReadOnlyField()
    tags = serializers.SlugRelatedField(slug_field='name', many=True, read_only=True)

    class Meta:
        model = Question
        fields = ('id', 'title', 'text', 'date_pub', 'slug', 'user',
                  'tags',
                  'votes',
                  'correct_answer'
                  )


class AnswerSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.username')

    class Meta:
        model = Answer
        fields = ('text', 'date', 'user', 'votes')
