# Quizy

This repository contains the Quizly project split into a frontend and a Django backend.

## Project structure

- `frontend/` – static frontend from `Developer-Akademie-Backendkurs/project.Quizly`
- `backend/` – Django REST API from `TobiasMatthies/Quizly-api`
- `docs/` – project reference files including the endpoint documentation and the checklist

## Local setup

### Backend

1. Create and activate a virtual environment:
   ```bash
   cd backend
   python -m venv .venv
   .venv\Scripts\activate
   ```
2. Install dependencies:
   ```bash
   python -m pip install -r requirements.txt
   ```
3. Start the API:
   ```bash
   python manage.py migrate
   python manage.py runserver 0.0.0.0:8000
   ```

Important: FFmpeg must be installed globally on the machine before using Whisper transcription.

### Frontend

Open `frontend/` with a local web server such as VS Code Live Server or:

```bash
cd frontend
npx serve .
```

Then open the generated local address in the browser.

## Reference documents

The endpoint specification and project checklist are stored in `docs/` as PDF files.
