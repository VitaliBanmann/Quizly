# Quizly Backend

Django REST API for Quizly. A user submits a YouTube URL; the backend downloads
the audio (`yt_dlp`), transcribes it locally (Whisper) and lets Gemini Flash
generate a quiz with 10 questions and 4 options each.

## Requirements

- Python 3.11+
- **FFmpeg must be installed globally** and available on the `PATH`
  (required by Whisper). Check with `ffmpeg -version`.
- A Gemini API key

## Setup

Run all commands from the repository root.

```bash
python -m venv .venv
.venv\Scripts\activate          # Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
copy .env.template .env         # Linux/macOS: cp .env.template .env
```

### Environment variables (`.env`)

The `.env` file holds secrets and environment-specific settings. It is **not**
part of the repository (see `.gitignore`), so you must create it yourself from
the template: `.env.template` -> `.env`. Open it and replace the placeholders.

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | yes | Django secret key. Any long random string, e.g. `python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"` |
| `GEMINI_API_KEY` | yes | API key from [Google AI Studio](https://aistudio.google.com/apikey), used to generate the quizzes |
| `GEMINI_MODELS` | no | Comma-separated Gemini models, tried in order if one is overloaded or rate-limited. Default: `gemini-3.5-flash,gemini-3-flash-preview,gemini-3.1-flash-lite` |
| `DEBUG` | no | `True` for local development, `False` in production |
| `ALLOWED_HOSTS` | no | Comma-separated hosts the API may serve, e.g. `localhost,127.0.0.1` |
| `CORS_ALLOW_CREDENTIALS` | no | Must be `True`, the JWT cookies are sent cross-origin |
| `CORS_ALLOWED_ORIGINS` | no | Comma-separated origins of the frontend that calls this API |
| `CSRF_TRUSTED_ORIGINS` | no | Same origins as `CORS_ALLOWED_ORIGINS` |

Without `GEMINI_API_KEY` no quiz can be generated. Restart the server after
changing the `.env`.

### Run

```bash
python manage.py migrate
python manage.py createsuperuser   # optional, for /admin/
python manage.py runserver
```

The API runs at `http://127.0.0.1:8000/api/`. Quizzes and questions can be
edited in the admin panel at `/admin/`. This repository contains only the
backend; a separate frontend talks to it through the REST API and has to be
listed in `CORS_ALLOWED_ORIGINS`.

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/register/` | no | Register (`username`, `email`, `password`, `confirmed_password`) |
| POST | `/api/login/` | no | Login, sets `access_token` and `refresh_token` HTTP-only cookies |
| POST | `/api/logout/` | yes | Blacklists the refresh token and deletes the cookies |
| POST | `/api/token/refresh/` | cookie | Sets a new `access_token` cookie |
| POST | `/api/quizzes/` | yes | Create a quiz from `{"url": "<YouTube url>"}` |
| GET | `/api/quizzes/` | yes | List own quizzes |
| GET | `/api/quizzes/{id}/` | yes | Quiz details (403 for foreign quizzes) |
| PATCH | `/api/quizzes/{id}/` | yes | Update `title` and/or `description` |
| DELETE | `/api/quizzes/{id}/` | yes | Delete a quiz |

Authentication uses JWT stored in HTTP-only cookies.

## Tests

```bash
python manage.py test
coverage run manage.py test && coverage report   # coverage (target: 95%)
flake8                                           # PEP 8 check
```
