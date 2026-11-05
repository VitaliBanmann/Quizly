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

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
copy .env.template .env         # Linux/macOS: cp .env.template .env
```

Edit `.env` and set `SECRET_KEY` and `GEMINI_API_KEY` (optional: `GEMINI_MODEL`, default `gemini-3.5-flash`).

```bash
python manage.py migrate
python manage.py createsuperuser   # optional, for /admin/
python manage.py runserver
```

The API runs at `http://127.0.0.1:8000/api/`. Quizzes and questions can be
edited in the admin panel at `/admin/`.

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
