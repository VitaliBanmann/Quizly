"""Tests for the quiz endpoints."""
from unittest.mock import patch

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase

from quizzes.models import Question, Quiz

VIDEO_URL = 'https://www.youtube.com/watch?v=abc123'
GENERATED = {
    'title': 'Generated',
    'description': 'About something',
    'questions': [{
        'question_title': f'Question {index}',
        'question_options': ['A', 'B', 'C', 'D'],
        'answer': 'A',
    } for index in range(10)],
}


class QuizTests(APITestCase):
    """Cover create, list, detail, update and delete."""

    def setUp(self):
        self.user = User.objects.create_user('owner', 'o@example.com', 'pw')
        self.other = User.objects.create_user('other', 'x@example.com', 'pw')
        self.quiz = self.make_quiz(self.user)
        self.login('owner')

    def make_quiz(self, user):
        quiz = Quiz.objects.create(
            user=user, title='Quiz', description='Desc', video_url=VIDEO_URL)
        Question.objects.create(
            quiz=quiz, question_title='Q', option1='A', option2='B',
            option3='C', option4='D', answer='A')
        return quiz

    def login(self, username):
        self.client.post(reverse('login'), {
            'username': username, 'password': 'pw'})

    def detail_url(self, quiz=None):
        return reverse('quiz-detail', args=[(quiz or self.quiz).pk])

    @patch('quizzes.api.serializers.generate_quiz_data',
           return_value=GENERATED)
    def test_create_quiz(self, _generate):
        response = self.client.post(
            reverse('quiz-list'), {'url': VIDEO_URL})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(response.data['questions']), 10)
        self.assertEqual(Quiz.objects.filter(user=self.user).count(), 2)

    def test_create_quiz_rejects_foreign_url(self):
        response = self.client.post(
            reverse('quiz-list'), {'url': 'https://example.com/video'})
        self.assertEqual(response.status_code, 400)

    def test_requires_authentication(self):
        self.client.cookies.clear()
        self.assertEqual(self.client.get(reverse('quiz-list')).status_code, 401)

    def test_list_only_own_quizzes(self):
        self.make_quiz(self.other)
        response = self.client.get(reverse('quiz-list'))
        self.assertEqual([item['id'] for item in response.data],
                         [self.quiz.pk])
        self.assertNotIn('created_at', response.data[0]['questions'][0])

    def test_detail_of_foreign_quiz_is_forbidden(self):
        response = self.client.get(self.detail_url(self.make_quiz(self.other)))
        self.assertEqual(response.status_code, 403)

    def test_detail_not_found(self):
        response = self.client.get(reverse('quiz-detail', args=[9999]))
        self.assertEqual(response.status_code, 404)

    def test_patch_updates_title_only(self):
        response = self.client.patch(
            self.detail_url(), {'title': 'New', 'video_url': 'https://x.io'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['title'], 'New')
        self.assertEqual(response.data['video_url'], VIDEO_URL)

    def test_delete_quiz(self):
        response = self.client.delete(self.detail_url())
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Quiz.objects.filter(pk=self.quiz.pk).exists())
