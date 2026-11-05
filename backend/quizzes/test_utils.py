"""Tests for the quiz pipeline helpers, models and admin."""
import json
from unittest.mock import MagicMock, patch

import yt_dlp
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase

from quizzes import utils
from quizzes.admin import QuizAdmin
from quizzes.models import Question, Quiz

DATA = {
    'title': 'T',
    'description': 'D',
    'questions': [{
        'question_title': 'Q',
        'question_options': ['A', 'B', 'C', 'D'],
        'answer': 'A',
    }],
}


class UrlAndParseTests(TestCase):
    """Validate url detection and quiz json parsing."""

    def test_youtube_urls(self):
        self.assertTrue(utils.is_youtube_url('https://youtu.be/abc'))
        self.assertFalse(utils.is_youtube_url('https://example.com/x'))

    def test_parse_valid(self):
        self.assertEqual(utils.parse_quiz_data(json.dumps(DATA)), DATA)

    def test_parse_invalid_json(self):
        with self.assertRaises(utils.QuizGenerationError):
            utils.parse_quiz_data('not json')

    def test_parse_wrong_option_count(self):
        bad = {'questions': [{'question_options': ['A']}]}
        with self.assertRaises(utils.QuizGenerationError):
            utils.parse_quiz_data(json.dumps(bad))


class PipelineTests(TestCase):
    """Cover download, transcription, Gemini and the full pipeline."""

    @patch('quizzes.utils.yt_dlp.YoutubeDL')
    def test_download_audio(self, downloader_class):
        downloader = downloader_class.return_value.__enter__.return_value
        downloader.prepare_filename.return_value = 'audio.webm'
        self.assertEqual(utils.download_audio('url', '.'), 'audio.webm')

    @patch('quizzes.utils.yt_dlp.YoutubeDL')
    def test_download_audio_error(self, downloader_class):
        downloader = downloader_class.return_value.__enter__.return_value
        downloader.extract_info.side_effect = yt_dlp.utils.DownloadError('x')
        with self.assertRaises(utils.QuizGenerationError):
            utils.download_audio('url', '.')

    @patch('quizzes.utils.whisper.load_model')
    def test_transcribe_audio(self, load_model):
        load_model.return_value.transcribe.return_value = {'text': 'hello'}
        self.assertEqual(utils.transcribe_audio('a.webm'), 'hello')

    @patch('quizzes.utils.genai.Client')
    def test_request_quiz_json(self, client_class):
        client = client_class.return_value
        client.models.generate_content.return_value = MagicMock(text='{}')
        self.assertEqual(utils.request_quiz_json('text'), '{}')

    @patch('quizzes.utils.request_quiz_json')
    @patch('quizzes.utils.transcribe_audio', return_value='text')
    @patch('quizzes.utils.download_audio', return_value='a.webm')
    def test_generate_quiz_data(self, _download, _transcribe, request_json):
        request_json.return_value = json.dumps(DATA)
        self.assertEqual(utils.generate_quiz_data('url'), DATA)


class ModelAndAdminTests(TestCase):
    """Cover string representations and the admin owner assignment."""

    def setUp(self):
        self.user = User.objects.create_user('owner', 'o@example.com', 'pw')

    def test_str_methods(self):
        quiz = utils.save_quiz(self.user, 'https://youtu.be/a', DATA)
        self.assertEqual(str(quiz), 'T')
        self.assertEqual(str(Question.objects.get(quiz=quiz)), 'Q')

    def test_admin_assigns_owner_on_create(self):
        request = RequestFactory().post('/')
        request.user = self.user
        quiz = Quiz(title='T', description='D', video_url='https://x.com')
        QuizAdmin(Quiz, AdminSite()).save_model(request, quiz, None, False)
        self.assertEqual(quiz.user, self.user)
