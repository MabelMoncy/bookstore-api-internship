# BookStore Microservice API

A production-ready asynchronous microservice for bookstore inventory and order processing, built with **FastAPI**, **Pydantic**, and **SQLAlchemy 2.0 ORM** with **SQLite** (`aiosqlite`). Containerized with a **multi-stage Dockerfile** and featuring **asynchronous BackgroundTasks**, **SlowAPI Rate Limiting**, **JWT Authentication**, **Role-Based Access Control (RBAC)**, and **Relational Joins**.

---

## Features

- **Asynchronous Background Processing**: Utilizes `FastAPI.BackgroundTasks` to send asynchronous email notifications and dispatch webhooks out-of-band without blocking HTTP request/response lifecycles.
- **Rate Limiting**: Protects sensitive endpoints (e.g. login and notification dispatchers) against brute-force and spam using **SlowAPI** (`429 Too Many Requests`).
- **Production Multi-Stage Docker Container**: Hardened, multi-stage `Dockerfile` creating a lightweight, non-root runner container with integrated health checks.
- **Relational ORM Persistence**: Powered by **SQLAlchemy 2.0** and **aiosqlite** with persistent relational models (`User`, `Book`, `Note`) and foreign-key joins.
- **User Authentication & RBAC**: JWT access tokens, bcrypt password hashing, role enforcement (`user` vs `admin`).
- **Interactive OpenAPI Documentation**: Swagger UI at `/docs` with JWT Bearer **Authorize** support.

---

## Project Structure

```text
bookstore-api/
├── app/
│   ├── __init__.py
│   ├── auth.py          # Authentication, JWT handling, and RBAC dependencies
│   ├── database.py      # Async SQLite engine, sessionmaker, and Base
│   ├── limiter.py       # Global SlowAPI rate limiter configuration
│   ├── main.py          # FastAPI application, route handlers, and lifespan
│   ├── models.py        # SQLAlchemy declarative ORM models (User, Book, Note)
│   ├── schemas.py       # Pydantic validation models and response DTOs
│   └── tasks.py         # Asynchronous background tasks (emails & webhooks)
├── Dockerfile           # Multi-stage production container build
├── .dockerignore        # Docker build exclusion list
├── docker-compose.yml   # Docker compose configuration
├── requirements.txt     # Python project dependencies
└── README.md            # Microservice documentation
```

---

## Configuration

The service is fully configurable via environment variables:

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///./bookstore.db` | SQLAlchemy async SQLite connection string |
| `JWT_SECRET_KEY` | `09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7` | Secret key used to sign JWT tokens |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token lifespan in minutes |

---

## Running with Docker

### 1. Build the Docker Image

The multi-stage `Dockerfile` compiles binary wheels in a builder stage and copies only production artifacts into a secure non-root runner image:

```bash
docker build -t bookstore-api:latest .
```

### 2. Run the Container

```bash
docker run -d -p 8000:8000 --name bookstore-api bookstore-api:latest
```

### 3. Or Run with Docker Compose

```bash
docker compose up --build -d
```

Check logs and health status:
```bash
docker ps
docker logs -f bookstore-api
```

---

## Local Development Execution

```bash
# 1. Activate virtual environment
source venv/bin/activate

# 2. Start Uvicorn
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- **Base URL**: `http://127.0.0.1:8000`
- **Interactive Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **OpenAPI Schema**: [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json)

---

## API Endpoints Reference

### Orders & Background Tasks (Task 4)

| Method | Endpoint | Access Level | Description | Status Code |
|---|---|---|---|---|
| `POST` | `/books/{book_id}/order` | **Authenticated User** | Order a book, decrement stock, and queue background confirmation email/webhook | `200 OK` / `400 Bad Request` |
| `POST` | `/notifications/email` | **Authenticated User** | Queue an async email notification in background (Rate limited) | `202 Accepted` |
| `POST` | `/notifications/webhook` | **Authenticated User** | Queue an async webhook dispatch in background (Rate limited) | `202 Accepted` |
| `GET` | `/notifications/tasks` | **Authenticated User** | Retrieve the audit log of executed background tasks | `200 OK` |

### Authentication & Users

| Method | Endpoint | Access Level | Description | Status Code |
|---|---|---|---|---|
| `POST` | `/auth/register` | **Public** | Register user or admin in SQLite | `201 Created` / `400 Bad Request` |
| `POST` | `/auth/login` | **Public** | Authenticate & get JWT Bearer token (Rate limited) | `200 OK` / `401 Unauthorized` |
| `GET` | `/auth/me` | **Authenticated User** | View user profile with associated books & notes | `200 OK` / `401 Unauthorized` |
| `GET` | `/auth/users` | **Admin Only** | List all registered users | `200 OK` / `403 Forbidden` |

### Books Catalog (Persistent)

| Method | Endpoint | Access Level | Description | Status Code |
|---|---|---|---|---|
| `GET` | `/` | **Public** | Microservice health check & welcome message | `200 OK` |
| `POST` | `/books` | **Authenticated User** | Add a new book (linked to user) | `201 Created` |
| `GET` | `/books` | **Authenticated User** | Retrieve all books (supports query filters) | `200 OK` |
| `GET` | `/books/{book_id}` | **Authenticated User** | Retrieve a specific book by ID | `200 OK` / `404 Not Found` |
| `PUT` | `/books/{book_id}` | **Authenticated User** | Update an existing book's details | `200 OK` / `404 Not Found` |
| `DELETE` | `/books/{book_id}` | **Admin Only** | Delete a book by ID | `200 OK` / `403 Forbidden` / `404 Not Found` |

### Relational Endpoints (Relational Joins)

| Method | Endpoint | Access Level | Description | Status Code |
|---|---|---|---|---|
| `GET` | `/users/{user_id}/books` | **Authenticated User** | Relational query: books by specific user | `200 OK` |
| `POST` | `/notes` | **Authenticated User** | Create note linked to current user | `201 Created` |
| `GET` | `/notes` | **Authenticated User** | Relational join (`selectinload`): notes with user profile | `200 OK` |
| `GET` | `/notes/{note_id}` | **Authenticated User** | Get note by ID with user relation | `200 OK` / `404 Not Found` |
| `DELETE` | `/notes/{note_id}` | **Authenticated User** | Delete note by ID | `200 OK` / `404 Not Found` |

---

## Example Usage with cURL

### 1. Register and Authenticate
```bash
# Register
curl -X POST http://127.0.0.1:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "reader1", "password": "securepassword123", "role": "user"}'

# Login
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "reader1", "password": "securepassword123"}' | jq -r .access_token)
```

### 2. Purchase a Book with Async Background Notification
```bash
curl -X POST http://127.0.0.1:8000/books/1/order \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "quantity": 1,
    "buyer_email": "reader1@example.com",
    "webhook_url": "https://webhook.site/test-endpoint"
  }'
```

### 3. Trigger Async Background Email & Inspect Log
```bash
# Trigger async email
curl -X POST http://127.0.0.1:8000/notifications/email \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "recipient": "customer@example.com",
    "subject": "Monthly Digest",
    "message": "Here are our latest technical books!"
  }'

# Inspect background task execution audit log
curl -X GET http://127.0.0.1:8000/notifications/tasks \
  -H "Authorization: Bearer $TOKEN"
```
