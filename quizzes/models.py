"""Database models for quizzes and their questions."""
from django.contrib.auth.models import User
from django.db import models


class Quiz(models.Model):
    """A quiz generated from a YouTube video."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    video_url = models.URLField()

    def __str__(self):
        return self.title


class Question(models.Model):
    """A multiple choice question belonging to a quiz."""

    quiz = models.ForeignKey(
        Quiz, related_name='questions', on_delete=models.CASCADE)
    question_title = models.CharField(max_length=255)
    option1 = models.CharField(max_length=255)
    option2 = models.CharField(max_length=255)
    option3 = models.CharField(max_length=255)
    option4 = models.CharField(max_length=255)
    answer = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.question_title
