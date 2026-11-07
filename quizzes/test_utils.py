"""Tests for the quiz pipeline helpers, models and admin."""
import json
from unittest.mock import MagicMock, patch

import yt_dlp
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.conf import settings
from django.test import RequestFactory, TestCase
from google.genai import errors as genai_errors

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


def make_quiz_data(question_count=10):
    """Return valid quiz data with the requested number of questions."""
    return {
        'title': 'T',
        'description': 'D',
        'questions': [{
            'question_title': f'Question {index}',
            'question_options': ['A', 'B', 'C', 'D'],
            'answer': 'A',
        } for index in range(question_count)],
    }


class UrlAndParseTests(TestCase):
    """Validate url detection and quiz json parsing."""

    def test_youtube_urls(self):
        self.assertTrue(utils.is_youtube_url('https://youtu.be/abc'))
        self.assertFalse(utils.is_youtube_url('https://example.com/x'))

    def test_normalize_youtube_url(self):
        expected = 'https://www.youtube.com/watch?v=abc_1-2'
        for url in ['https://youtu.be/abc_1-2?si=x',
                    'https://www.youtube.com/watch?v=abc_1-2&t=5',
                    'https://www.youtube.com/watch?feature=x&v=abc_1-2',
                    'https://www.youtube.com/shorts/abc_1-2',
                    'https://www.youtube.com/embed/abc_1-2']:
            self.assertEqual(utils.normalize_youtube_url(url), expected)

    def test_normalize_rejects_invalid(self):
        self.assertIsNone(utils.normalize_youtube_url('https://example.com'))
        self.assertIsNone(
            utils.normalize_youtube_url('https://www.youtube.com/watch?'))

    def test_parse_valid(self):
        data = make_quiz_data()
        self.assertEqual(utils.parse_quiz_data(json.dumps(data)), data)

    def test_parse_invalid_json(self):
        with self.assertRaises(utils.QuizGenerationError):
            utils.parse_quiz_data('not json')

    def test_parse_rejects_wrong_question_count(self):
        data = make_quiz_data(question_count=9)
        with self.assertRaises(utils.QuizGenerationError):
            utils.parse_quiz_data(json.dumps(data))

    def test_parse_wrong_option_count(self):
        bad = make_quiz_data()
        bad['questions'][0]['question_options'] = ['A', 'B', 'C']
        with self.assertRaises(utils.QuizGenerationError):
            utils.parse_quiz_data(json.dumps(bad))

    def test_parse_rejects_duplicate_options(self):
        bad = make_quiz_data()
        bad['questions'][0]['question_options'] = ['A', 'A', 'C', 'D']
        with self.assertRaises(utils.QuizGenerationError):
            utils.parse_quiz_data(json.dumps(bad))

    def test_parse_rejects_answer_missing_from_options(self):
        bad = make_quiz_data()
        bad['questions'][0]['answer'] = 'E'
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

    @patch('quizzes.utils.whisper.load_model')
    def test_transcribe_audio_error(self, load_model):
        load_model.side_effect = FileNotFoundError('ffmpeg')
        with self.assertRaises(utils.QuizGenerationError):
            utils.transcribe_audio('a.webm')

    @patch('quizzes.utils.genai.Client')
    def test_request_quiz_json(self, client_class):
        client = client_class.return_value
        client.models.generate_content.return_value = MagicMock(text='{}')
        self.assertEqual(utils.request_quiz_json('text'), '{}')

    @patch('quizzes.utils.time.sleep')
    @patch('quizzes.utils.call_gemini')
    def test_request_retries_on_overload(self, call, sleep):
        overload = genai_errors.ServerError(503, {'error': {}})
        call.side_effect = [overload, '{}']
        self.assertEqual(utils.request_quiz_json('text'), '{}')
        sleep.assert_called_once()

    @patch('quizzes.utils.time.sleep')
    @patch('quizzes.utils.call_gemini')
    def test_request_falls_back_to_next_model(self, call, _sleep):
        limit = genai_errors.ClientError(429, {'error': {}})
        call.side_effect = [limit, limit, '{}']
        self.assertEqual(utils.request_quiz_json('text'), '{}')
        self.assertEqual(call.call_args.args[1], settings.GEMINI_MODELS[1])

    @patch('quizzes.utils.time.sleep')
    @patch('quizzes.utils.call_gemini')
    def test_request_fails_when_all_models_fail(self, call, _sleep):
        call.side_effect = genai_errors.ServerError(503, {'error': {}})
        with self.assertRaises(utils.QuizGenerationError):
            utils.request_quiz_json('text')
        expected = utils.GEMINI_ATTEMPTS * len(settings.GEMINI_MODELS)
        self.assertEqual(call.call_count, expected)

    @patch('quizzes.utils.call_gemini')
    def test_client_error_is_not_retried_on_same_model(self, call):
        call.side_effect = genai_errors.ClientError(400, {'error': {}})
        with self.assertRaises(utils.QuizGenerationError):
            utils.request_quiz_json('text')
        self.assertEqual(call.call_count, len(settings.GEMINI_MODELS))

    @patch('quizzes.utils.request_quiz_json')
    @patch('quizzes.utils.transcribe_audio', return_value='text')
    @patch('quizzes.utils.download_audio', return_value='a.webm')
    def test_generate_quiz_data(self, _download, _transcribe, request_json):
        data = make_quiz_data()
        request_json.return_value = json.dumps(data)
        self.assertEqual(utils.generate_quiz_data('url'), data)


class ModelAndAdminTests(TestCase):
    """Cover string representations and the admin owner assignment."""

    def setUp(self):
        self.user = User.objects.create_user('owner', 'o@example.com', 'pw')

    def test_str_methods(self):
        quiz = utils.save_quiz(self.user, 'https://youtu.be/a', DATA)
        self.assertEqual(str(quiz), 'T')
        self.assertEqual(str(Question.objects.get(quiz=quiz)), 'Q')

    def test_options_are_shuffled_and_keep_answer(self):
        quiz = Quiz.objects.create(
            user=self.user, title='T', description='D', video_url='https://x.com')
        item = DATA['questions'][0]
        orders = set()
        for _ in range(30):
            question = utils.build_question(quiz, item)
            options = [question.option1, question.option2,
                       question.option3, question.option4]
            self.assertEqual(sorted(options), ['A', 'B', 'C', 'D'])
            self.assertIn(question.answer, options)
            orders.add(tuple(options))
        self.assertGreater(len(orders), 1)

    def test_admin_assigns_owner_on_create(self):
        request = RequestFactory().post('/')
        request.user = self.user
        quiz = Quiz(title='T', description='D', video_url='https://x.com')
        QuizAdmin(Quiz, AdminSite()).save_model(request, quiz, None, False)
        self.assertEqual(quiz.user, self.user)
