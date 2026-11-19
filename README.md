# BookStore REST API

A lightweight, high-performance asynchronous REST API for managing a bookstore inventory, built with **FastAPI** and **Pydantic**. Data is stored in-memory using a Python dictionary without requiring an external database.

---

## Features

- **Asynchronous CRUD Endpoints**: Create, read, update, and delete books asynchronously.
- **In-Memory Storage**: Fast in-memory Python dictionary data store.
- **Pydantic Validation**: Strict data type and business logic validation (positive prices, non-negative stock, non-empty required fields).
- **Flexible Query Filtering**: Filter books by `title`, `author`, `genre`, and price range (`min_price`, `max_price`).
- **Standard HTTP Status Codes & Error Handling**: Proper status codes (`200`, `201`, `400`, `404`, `422`) with descriptive JSON error messages.
- **Interactive API Documentation**: Auto-generated interactive Swagger UI and OpenAPI JSON specifications.

---

## Project Structure

```text
bookstore-api/
├── app/
│   ├── __init__.py
│   ├── main.py
│   └── schemas.py
├── requirements.txt
└── README.md
```

- **`app/schemas.py`**: Pydantic models (`BookBase`, `BookCreate`, `BookUpdate`, `Book`) defining book schemas, data types, and field validation rules.
- **`app/main.py`**: FastAPI application instance, in-memory dictionary storage, and asynchronous route handlers.
- **`requirements.txt`**: Project dependencies.
- **`README.md`**: Project documentation, setup, execution instructions, and API examples.

---

## Data Schema & Validation Rules

Each book record contains the following attributes:

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | `integer` | Positive (`> 0`), auto-generated or specified on create | Unique identifier for the book |
| `title` | `string` | Required, non-empty, non-whitespace | Title of the book |
| `author` | `string` | Required, non-empty, non-whitespace | Author of the book |
| `price` | `float` | Required, strictly positive (`> 0.0`) | Price of the book |
| `genre` | `string` | Required, non-empty, non-whitespace | Genre / category of the book |
| `stock` | `integer` | Required, non-negative (`>= 0`) | Available quantity in inventory |

---

## Installation & Setup

### Prerequisites

- Python 3.10+ installed
- `pip` package manager

### 1. Set Up Virtual Environment

If using an existing virtual environment:
```bash
source venv/bin/activate
```

Or to create and activate a new virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Execution Instructions

Start the development server using **Uvicorn**:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Alternative execution using Python module syntax:
```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Once running:
- **API Base URL**: `http://127.0.0.1:8000`
- **Interactive Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc UI**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **OpenAPI Schema (JSON)**: [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json)

---

## API Endpoints

| Method | Endpoint | Description | Status Code |
|---|---|---|---|
| `GET` | `/` | API welcome message and documentation links | `200 OK` |
| `POST` | `/books` | Create a new book | `201 Created` |
| `GET` | `/books` | Retrieve all books (with optional query filters) | `200 OK` |
| `GET` | `/books/{book_id}` | Retrieve a specific book by ID | `200 OK` / `404 Not Found` |
| `PUT` | `/books/{book_id}` | Update an existing book by ID | `200 OK` / `404 Not Found` |
| `DELETE` | `/books/{book_id}` | Delete a book by ID | `200 OK` / `404 Not Found` |

---

## Example Requests & Responses

### 1. Create a Book (`POST /books`)

**Request:**
`POST /books`
```json
{
  "title": "Clean Code",
  "author": "Robert C. Martin",
  "price": 29.99,
  "genre": "Software Engineering",
  "stock": 15
}
```

*Note: `id` is optional. If provided, the system uses it (validating uniqueness); otherwise, an incrementing ID is auto-assigned.*

**Response (`201 Created`):**
```json
{
  "id": 1,
  "title": "Clean Code",
  "author": "Robert C. Martin",
  "price": 29.99,
  "genre": "Software Engineering",
  "stock": 15
}
```

---

### 2. Get All Books with Query Filtering (`GET /books`)

Supports optional query parameters:
- `title`: Case-insensitive substring match
- `author`: Case-insensitive substring match
- `genre`: Case-insensitive substring match
- `min_price`: Minimum price filter (`>= min_price`)
- `max_price`: Maximum price filter (`<= max_price`)

**Example Request with Query Parameters:**
`GET /books?genre=Software&min_price=20&max_price=35`

**Response (`200 OK`):**
```json
[
  {
    "id": 1,
    "title": "Clean Code",
    "author": "Robert C. Martin",
    "price": 29.99,
    "genre": "Software Engineering",
    "stock": 15
  }
]
```

---

### 3. Get Book by ID (`GET /books/{book_id}`)

**Request:**
`GET /books/1`

**Response (`200 OK`):**
```json
{
  "id": 1,
  "title": "Clean Code",
  "author": "Robert C. Martin",
  "price": 29.99,
  "genre": "Software Engineering",
  "stock": 15
}
```

**Missing Book Response (`404 Not Found`):**
`GET /books/999`
```json
{
  "detail": "Book with id 999 not found"
}
```

---

### 4. Update a Book (`PUT /books/{book_id}`)

Updates one or more fields of an existing book.

**Request:**
`PUT /books/1`
```json
{
  "price": 24.99,
  "stock": 12
}
```

**Response (`200 OK`):**
```json
{
  "id": 1,
  "title": "Clean Code",
  "author": "Robert C. Martin",
  "price": 24.99,
  "genre": "Software Engineering",
  "stock": 12
}
```

---

### 5. Delete a Book (`DELETE /books/{book_id}`)

**Request:**
`DELETE /books/1`

**Response (`200 OK`):**
```json
{
  "message": "Book deleted successfully",
  "id": 1
}
```

**Missing Book Response (`404 Not Found`):**
`DELETE /books/1`
```json
{
  "detail": "Book with id 1 not found"
}
```

---

### 6. Validation Error Example (`422 Unprocessable Entity`)

If a request fails validation (e.g., negative price or invalid data type):

**Request:**
`POST /books`
```json
{
  "title": "Invalid Book",
  "author": "Author Name",
  "price": -10.0,
  "genre": "Fiction",
  "stock": -5
}
```

**Response (`422 Unprocessable Entity`):**
```json
{
  "detail": [
    {
      "type": "greater_than",
      "loc": ["body", "price"],
      "msg": "Input should be greater than 0",
      "input": -10.0,
      "ctx": {"gt": 0.0}
    },
    {
      "type": "greater_than_equal",
      "loc": ["body", "stock"],
      "msg": "Input should be greater than or equal to 0",
      "input": -5,
      "ctx": {"ge": 0}
    }
  ]
}
```

