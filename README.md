# ⚡ CodeLearn — Synchronous Group Coding Platform

A minimal, teacher-friendly web application where teachers schedule live coding sessions, students solve tasks in a browser editor, and the system evaluates submissions automatically with a real-time leaderboard.

---

## Table of Contents

1. [Features](#features)
2. [Architecture Overview](#architecture-overview)
3. [Tech Stack](#tech-stack)
4. [Quick Start (Local Dev — No Docker)](#quick-start-local-dev--no-docker)
5. [Full Stack Setup with Docker Compose](#full-stack-setup-with-docker-compose)
6. [Environment Variables](#environment-variables)
7. [Project Structure](#project-structure)
8. [Database Models (ER Summary)](#database-models-er-summary)
9. [Runner Safety & Sandbox](#runner-safety--sandbox)
10. [Running Tests](#running-tests)
11. [Creating a ZIP Package](#creating-a-zip-package)
12. [Demo Credentials](#demo-credentials)

---

## Features

### Teacher
- Create/manage student groups (name + student list)
- Create tasks: title, description, example I/O, multiple hidden test cases, time/memory limits
- Schedule sessions: link a group + task + start time
- Activate/close sessions with one click
- **Live monitor**: see who joined, ran examples, submitted, and their pass/fail status (WebSocket real-time)

### Student
- Join groups and see scheduled/active sessions
- In-browser Python editor (CodeMirror, Dracula theme)
- **Run Code** — runs against example tests instantly (no queue, no Docker in dev mode)
- **Submit** — queues evaluation against all hidden tests via Celery
- View per-test-case results (stdout, stderr, time used)
- Live leaderboard sorted by correctness → submission time

### Evaluation
- Example tests → Run Code (fast, synchronous)
- Hidden tests → Submit (async via Celery + Redis)
- Subprocess runner in dev; Docker sandbox in production
- Leaderboard: correct + earliest submission wins

---

## Architecture Overview

```
Browser (CodeMirror)
        │
        │  HTTP / WebSocket (ASGI / Daphne)
        ▼
  Django Application
  ┌─────────────────────────────────┐
  │  apps/users    – auth & groups  │
  │  apps/tasks    – task CRUD      │
  │  apps/sessions_app – scheduling │
  │  apps/submissions  – results    │
  │  apps/runner   – exec service   │
  └─────────────────────────────────┘
        │ Celery tasks
        ▼
  Redis (broker + channel layer)
        │
        ▼
  Celery Worker ──► Runner Service
                        │
                        ▼
              [subprocess] or [Docker sandbox]
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, Django 4.2 |
| Realtime | Django Channels 4 + channels-redis (WebSockets) |
| Task queue | Celery 5 + Redis 7 |
| Database | SQLite (dev) / PostgreSQL 15 (prod) |
| Frontend | HTML + Tailwind CSS (CDN) |
| Code editor | CodeMirror 5 (Python mode, Dracula theme) |
| Web server | Daphne (ASGI) |
| Sandbox | Subprocess (dev) / Docker (prod) |

---

## Quick Start (Local Dev — No Docker)

This method uses SQLite and the subprocess runner. Safe for development only.

### Prerequisites
- Python 3.11+
- `pip`
- Redis (for WebSockets + Celery): `brew install redis` / `sudo apt install redis-server`

### Steps

```bash
# 1. Clone / unzip the project
cd codelearn

# 2. Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy env file
cp .env.example .env
# Edit .env if needed (defaults work for local dev)

# 5. Run database migrations
python manage.py migrate

# 6. Load demo data (teacher, students, demo task)
python manage.py loaddata fixtures/demo_fixture.json

# 7. (Optional) Create your own superuser
python manage.py createsuperuser

# 8. Start Redis (in a separate terminal)
redis-server

# 9. Start Celery worker (in another separate terminal)
celery -A codelearn worker --loglevel=info

# 10. Start the development server
python manage.py runserver
```

Open http://127.0.0.1:8000 in your browser.

---

## Full Stack Setup with Docker Compose

This uses PostgreSQL, Redis, Daphne, and Celery — everything in containers.

### Prerequisites
- Docker Desktop (or Docker + Docker Compose)

### Steps

```bash
# 1. Copy env file
cp .env.example .env

# 2. Build and start all services
docker-compose up --build

# The web container automatically runs:
#   python manage.py migrate
#   python manage.py collectstatic

# 3. In a second terminal, load demo data
docker-compose exec web python manage.py loaddata fixtures/demo_fixture.json

# 4. (Optional) Create a superuser
docker-compose exec web python manage.py createsuperuser
```

Open http://localhost:8000

### Services started by docker-compose

| Service | Port | Description |
|---|---|---|
| `web` | 8000 | Daphne ASGI server |
| `worker` | — | Celery background worker |
| `db` | 5432 | PostgreSQL 15 |
| `redis` | 6379 | Redis 7 |

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | insecure-dev-key | Django secret key |
| `DEBUG` | `True` | Debug mode |
| `ALLOWED_HOSTS` | `*` | Comma-separated allowed hosts |
| `DATABASE_URL` | SQLite | Postgres URL for prod |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `USE_DOCKER_SANDBOX` | `False` | Use Docker for code execution |
| `SANDBOX_IMAGE` | `codelearn-runner:latest` | Docker image for sandbox |
| `SANDBOX_TIMEOUT` | `10` | Container kill timeout (seconds) |
| `SANDBOX_MEMORY_LIMIT` | `64m` | Container memory limit |

---

## Project Structure

```
codelearn/
├── codelearn/                  # Django project package
│   ├── settings/
│   │   ├── base.py             # Shared settings
│   │   ├── development.py      # Dev overrides (SQLite, no Docker)
│   │   └── production.py       # Prod overrides (Postgres, Docker)
│   ├── urls.py                 # Root URL conf
│   ├── asgi.py                 # ASGI + WebSocket routing
│   ├── celery.py               # Celery app factory
│   └── wsgi.py
│
├── apps/
│   ├── users/                  # Auth, User model, Groups
│   ├── tasks/                  # Task + TestCase models & CRUD
│   ├── sessions_app/           # Session scheduling, monitor, WebSocket
│   ├── submissions/            # Submission model, API (run/submit/status)
│   └── runner/                 # Code execution service + Celery tasks
│
├── templates/                  # Django HTML templates
│   ├── base.html
│   ├── users/
│   ├── tasks/
│   ├── sessions/
│   └── submissions/
│
├── fixtures/
│   └── demo_fixture.json       # Sample teacher, students, task
│
├── tests.py                    # Unit tests
├── manage.py
├── requirements.txt
├── Dockerfile                  # Web + worker image
├── Dockerfile.runner           # Sandbox image
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Database Models (ER Summary)

```
User ──────────────── Group
(role: teacher|student)  name, teacher(FK), students(M2M)
        │
        │ created_by
        ▼
      Task ──────── TestCase
   title, desc     input_data, expected_output, is_example
   time_limit      ─────────────────────────────────────
   memory_limit
        │
        │ task(FK)
        ▼
     Session ─────────────────────────────────────
   group(FK), task(FK), start_time, is_active
        │
        │ session(FK)
        ▼
    Submission
   student(FK), task(FK), session(FK)
   code(Text), status, is_correct
   results(JSON), created_at, evaluated_at
```

### Key relationships
- A **Teacher** owns Groups and Tasks
- A **Session** binds one Group + one Task with a start time
- Students belong to Groups via M2M
- A **Submission** records one student's code attempt for a session
- **TestCase.is_example=True** → used for Run Code
- **TestCase.is_example=False** → used for Submit evaluation

---

## Runner Safety & Sandbox

### Development Mode (`USE_DOCKER_SANDBOX=False`)

Code runs via Python `subprocess` on the **host machine**.

⚠️ **Security warning**: This offers NO isolation. Use only with trusted code or local development. Never expose in production.

Safeguards in dev mode:
- Timeout enforced via `subprocess.TimeoutExpired`
- Code size limited to 64 KB
- Rate limiting: 10 Run/minute, 5 Submit/minute per student

### Production Mode (`USE_DOCKER_SANDBOX=True`)

Each submission spawns a fresh Docker container:

```python
client.containers.run(
    SANDBOX_IMAGE,           # codelearn-runner:latest (minimal Python image)
    network_disabled=True,   # No outbound network
    mem_limit='64m',         # Memory cap
    cpu_period=100000,
    cpu_quota=50000,         # 50% of one CPU
    remove=True,             # Auto-delete after run
    timeout=time_limit + 2,
)
```

The sandbox image (`Dockerfile.runner`):
- Based on `python:3.11-slim`
- pip removed
- Runs as non-root `sandbox` user

To build the sandbox image:
```bash
docker build -f Dockerfile.runner -t codelearn-runner:latest .
```

### Rate Limiting

Implemented via Django cache (per-user per-minute):
- Run Code: max 10/minute
- Submit: max 5/minute

---

## Running Tests

```bash
# Activate virtualenv first
python manage.py test

# Run specific test class
python manage.py test tests.RunnerTest
python manage.py test tests.LeaderboardOrderingTest
```

Test coverage:
- `UserModelTest` — role flags
- `GroupTest` — student membership
- `TaskCreationTest` — teacher creates task via HTTP
- `RunnerTest` — correct code, wrong output, syntax errors, timeouts
- `LeaderboardOrderingTest` — ranking logic

---

## Creating a ZIP Package

```bash
cd ..
zip -r codelearn.zip codelearn/ \
  --exclude "*.pyc" \
  --exclude "*/__pycache__/*" \
  --exclude "*/db.sqlite3" \
  --exclude "*/.env" \
  --exclude "*/staticfiles/*" \
  --exclude "*/.venv/*"
```

---

## Demo Credentials

After loading `demo_fixture.json`:

> ⚠️ The fixture contains pre-hashed passwords that **may not work** with all Django versions.
> Use `python manage.py createsuperuser` or register via the UI instead.

**Recommended**: Register accounts through http://localhost:8000/users/register/

| Role | Action |
|---|---|
| Teacher | Register → select "Teacher" → create groups & tasks → schedule sessions |
| Student | Register → select "Student" → wait for teacher to add you to a group |

### Typical Demo Flow

1. **Teacher** registers, creates a Group, adds student accounts
2. **Teacher** creates a Task with example + hidden test cases
3. **Teacher** schedules a Session (Group + Task + start time)
4. **Teacher** clicks "Start" to activate the session
5. **Students** see the session on their dashboard and click "Enter Session"
6. Students write code in the browser editor
7. Students click **Run Code** → instant feedback on example tests
8. Students click **Submit** → queued evaluation on hidden tests
9. **Teacher** watches the live monitor; everyone watches the leaderboard
10. **Teacher** clicks "Close Session" when done

---

## Developer Notes

### Adding a new language

1. Add a language selector to the task form
2. Store `language` field on `Task` or `Submission`
3. Extend `_run_in_subprocess` / `_run_in_docker` to invoke the correct interpreter
4. Add CodeMirror mode for the language in `session_join.html`

### Polling fallback

If Redis/WebSockets are unavailable, the leaderboard page polls `/api/leaderboard/<pk>/` every 5 seconds and the monitor page auto-reloads every 30 seconds.

### Adding more test cases via Django admin

Go to http://localhost:8000/admin/ → Tasks → TestCases.
Set `is_example=False` for hidden test cases.
