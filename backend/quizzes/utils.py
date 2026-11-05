"""Pipeline helpers: YouTube audio download, transcription and quiz generation."""
import json
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

GEMINI_ATTEMPTS = 4
GEMINI_RETRY_DELAY = 5

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
- Each question has exactly 4 distinct answer options and exactly one correct answer.
- The output must be valid JSON without any text outside the JSON.

Transcript:
"""


class QuizGenerationError(Exception):
    """Raised when a quiz cannot be generated from the given video."""


def is_youtube_url(url):
    """Return True if the url points to a YouTube video."""
    return bool(YOUTUBE_URL_PATTERN.match(url))


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
    except yt_dlp.utils.DownloadError as error:
        raise QuizGenerationError('Could not download the video audio.') from error


def transcribe_audio(audio_path):
    """Transcribe an audio file locally with Whisper."""
    model = whisper.load_model('turbo')
    return model.transcribe(audio_path)['text']


def call_gemini(transcript):
    """Send the transcript to Gemini Flash and return the raw response text."""
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=QUIZ_PROMPT + transcript,
        config={'response_mime_type': 'application/json'},
    )
    return response.text


def request_quiz_json(transcript):
    """Ask Gemini for a quiz, retrying while the service is overloaded."""
    last_error = None
    for attempt in range(GEMINI_ATTEMPTS):
        try:
            return call_gemini(transcript)
        except genai_errors.ServerError as error:
            last_error = error
            time.sleep(GEMINI_RETRY_DELAY * (attempt + 1))
        except genai_errors.APIError as error:
            last_error = error
            break
    raise QuizGenerationError(
        'The quiz service is currently unavailable.') from last_error


def parse_quiz_data(raw_json):
    """Parse and validate the quiz JSON returned by Gemini."""
    try:
        data = json.loads(raw_json)
        questions = data['questions']
        for question in questions:
            if len(question['question_options']) != 4:
                raise ValueError('Each question needs four options.')
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
    options = item['question_options']
    return Question(
        quiz=quiz, question_title=item['question_title'],
        option1=options[0], option2=options[1],
        option3=options[2], option4=options[3],
        answer=item['answer'],
    )
