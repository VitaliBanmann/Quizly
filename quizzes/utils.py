"""Pipeline helpers: YouTube audio download, transcription and quiz generation."""
import json
import logging
import random
import re
import tempfile
import time
from pathlib import Path

import whisper
import yt_dlp
from django.conf import settings
from google import genai
from google.genai import errors as genai_errors

from quizzes.models import Question, Quiz

YOUTUBE_URL_PATTERN = re.compile(
    r'^https?://(www\.|m\.)?(youtube\.com/(watch\?|shorts/|embed/)|youtu\.be/)',
)
VIDEO_ID_PATTERN = re.compile(
    r'(?:[?&]v=|youtu\.be/|shorts/|embed/)([\w-]+)',
)

GEMINI_ATTEMPTS = 2
GEMINI_RETRY_DELAY = 3
RETRYABLE_CODES = (429, 500, 503)

logger = logging.getLogger(__name__)

QUIZ_PROMPT = """Based on the following transcript, generate a quiz in valid JSON format.

The quiz must follow this exact structure:

{
  "title": "A concise quiz title based on the topic of the transcript.",
  "description": "Summary of the transcript in at most 150 characters. No questions or answers.",
  "questions": [
    {
      "question_title": "The question goes here.",
      "question_options": ["Option A", "Option B", "Option C", "Option D"],
      "answer": "The correct answer, identical to one of the options"
    }
  ]
}

Requirements:
- Exactly 10 questions.
- Write all texts (title, description, questions, options, answers) in German,
  regardless of the language of the transcript.
- Each question has exactly 4 distinct answer options and exactly one correct answer.
- The output must be valid JSON without any text outside the JSON.

Transcript:
"""


class QuizGenerationError(Exception):
    """Raised when a quiz cannot be generated from the given video."""


def is_youtube_url(url):
    """Return True if the url points to a YouTube video."""
    return bool(YOUTUBE_URL_PATTERN.match(url))


def normalize_youtube_url(url):
    """Return the canonical watch url of a YouTube video or None."""
    match = VIDEO_ID_PATTERN.search(url)
    if not is_youtube_url(url) or not match:
        return None
    return f'https://www.youtube.com/watch?v={match.group(1)}'


def download_audio(url, target_dir):
    """Download the audio track of a YouTube video and return its path."""
    options = {
        'format': 'bestaudio/best',
        'outtmpl': str(Path(target_dir) / '%(id)s.%(ext)s'),
        'quiet': True,
        'noplaylist': True,
    }
    try:
        with yt_dlp.YoutubeDL(options) as downloader:
            info = downloader.extract_info(url, download=True)
            return downloader.prepare_filename(info)
    except Exception as error:
        logger.exception('Audio download failed for %s', url)
        raise QuizGenerationError('Could not download the video audio.') from error


def transcribe_audio(audio_path):
    """Transcribe an audio file locally with Whisper."""
    try:
        model = whisper.load_model('turbo')
        return model.transcribe(audio_path)['text']
    except Exception as error:
        logger.exception('Transcription failed (is ffmpeg installed?)')
        raise QuizGenerationError('Could not transcribe the audio.') from error


def call_gemini(transcript, model):
    """Send the transcript to one Gemini model and return the response text."""
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    response = client.models.generate_content(
        model=model,
        contents=QUIZ_PROMPT + transcript,
        config={'response_mime_type': 'application/json'},
    )
    return response.text


def call_with_retry(transcript, model):
    """Call one model, retrying briefly on overload or rate limits."""
    for attempt in range(GEMINI_ATTEMPTS):
        try:
            return call_gemini(transcript, model)
        except genai_errors.APIError as error:
            last_attempt = attempt == GEMINI_ATTEMPTS - 1
            if error.code not in RETRYABLE_CODES or last_attempt:
                raise
            time.sleep(GEMINI_RETRY_DELAY)


def request_quiz_json(transcript):
    """Ask Gemini for a quiz and fall back to the next model on failure."""
    last_error = None
    for model in settings.GEMINI_MODELS:
        try:
            return call_with_retry(transcript, model)
        except Exception as error:
            last_error = error
            logger.warning('Gemini model %s failed: %s', model, error)
    raise QuizGenerationError(
        'The quiz service is currently unavailable.') from last_error


def parse_quiz_data(raw_json):
    """Parse and validate the quiz JSON returned by Gemini."""
    try:
        data = json.loads(raw_json)
        questions = data['questions']
        if not isinstance(questions, list) or len(questions) != 10:
            raise ValueError('A quiz needs exactly ten questions.')
        for question in questions:
            if not isinstance(question, dict):
                raise ValueError('Each question must be an object.')
            options = question.get('question_options')
            answer = question.get('answer')
            if not isinstance(options, list) or len(options) != 4:
                raise ValueError('Each question needs four options.')
            if not all(isinstance(option, str) and option.strip()
                       for option in options):
                raise ValueError('Each option must be a non-empty string.')
            if len(set(options)) != 4:
                raise ValueError('Each question needs four distinct options.')
            if not isinstance(answer, str) or answer not in options:
                raise ValueError('The answer must match one of the options.')
    except (ValueError, KeyError, TypeError) as error:
        raise QuizGenerationError('Invalid quiz data received.') from error
    return data


def generate_quiz_data(url):
    """Run the full pipeline and return validated quiz data for a video."""
    with tempfile.TemporaryDirectory() as target_dir:
        audio_path = download_audio(url, target_dir)
        transcript = transcribe_audio(audio_path)
    return parse_quiz_data(request_quiz_json(transcript))


def save_quiz(user, url, data):
    """Persist a generated quiz with its questions."""
    quiz = Quiz.objects.create(
        user=user, video_url=url,
        title=data['title'], description=data['description'],
    )
    Question.objects.bulk_create([
        build_question(quiz, item) for item in data['questions']
    ])
    return quiz


def build_question(quiz, item):
    """Create an unsaved Question from generated question data."""
    options = list(item['question_options'])
    random.shuffle(options)
    return Question(
        quiz=quiz, question_title=item['question_title'],
        option1=options[0], option2=options[1],
        option3=options[2], option4=options[3],
        answer=item['answer'],
    )
