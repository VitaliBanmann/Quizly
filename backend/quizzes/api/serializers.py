"""Serializers for quizzes and questions."""
from rest_framework import serializers

from quizzes.models import Question, Quiz
from quizzes.utils import (QuizGenerationError, generate_quiz_data,
                           is_youtube_url, save_quiz)


class QuestionBriefSerializer(serializers.ModelSerializer):
    """Question without timestamps."""

    question_options = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = ['id', 'question_title', 'question_options', 'answer']

    def get_question_options(self, obj):
        """Return the four options as list."""
        return [obj.option1, obj.option2, obj.option3, obj.option4]


class QuestionSerializer(QuestionBriefSerializer):
    """Question including timestamps."""

    class Meta(QuestionBriefSerializer.Meta):
        fields = QuestionBriefSerializer.Meta.fields + [
            'created_at', 'updated_at']


class QuizListSerializer(serializers.ModelSerializer):
    """Quiz with questions without timestamps (list and detail)."""

    questions = QuestionBriefSerializer(many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = ['id', 'title', 'description', 'created_at', 'updated_at',
                  'video_url', 'questions']


class QuizSerializer(QuizListSerializer):
    """Full quiz; only title and description are writable."""

    questions = QuestionSerializer(many=True, read_only=True)

    class Meta(QuizListSerializer.Meta):
        read_only_fields = ['id', 'created_at', 'updated_at', 'video_url']


class QuizCreateSerializer(serializers.Serializer):
    """Create a quiz from a YouTube url."""

    url = serializers.URLField()

    def validate_url(self, value):
        """Only accept YouTube video urls."""
        if not is_youtube_url(value):
            raise serializers.ValidationError('Not a valid YouTube url.')
        return value

    def create(self, validated_data):
        """Generate the quiz for the requesting user."""
        url = validated_data['url']
        try:
            data = generate_quiz_data(url)
        except QuizGenerationError as error:
            raise serializers.ValidationError({'url': str(error)})
        return save_quiz(self.context['request'].user, url, data)

    def to_representation(self, instance):
        """Return the full quiz representation."""
        return QuizSerializer(instance).data
