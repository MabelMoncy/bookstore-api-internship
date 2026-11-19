"""FastAPI application for the BookStore REST API."""

from typing import Optional
from fastapi import FastAPI, HTTPException, Path, Query, status

from app.schemas import Book, BookCreate, BookUpdate

app = FastAPI(
    title="BookStore REST API",
    description="A lightweight, asynchronous in-memory REST API for bookstore management.",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
)

# In-memory database storing books by their unique integer ID
books_db: dict[int, Book] = {}


@app.get(
    "/",
    tags=["Root"],
    summary="Root endpoint",
    description="Welcome message and API documentation links.",
)
async def root():
    return {
        "message": "Welcome to the BookStore REST API",
        "docs": "/docs",
        "openapi": "/openapi.json",
    }


@app.post(
    "/books",
    response_model=Book,
    status_code=status.HTTP_201_CREATED,
    tags=["Books"],
    summary="Create a new book",
    description="Add a new book to the in-memory store. An ID is auto-assigned if not provided.",
)
async def create_book(book_in: BookCreate) -> Book:
    if book_in.id is not None:
        if book_in.id in books_db:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Book with id {book_in.id} already exists",
            )
        book_id = book_in.id
    else:
        book_id = max(books_db.keys(), default=0) + 1

    new_book = Book(
        id=book_id,
        title=book_in.title,
        author=book_in.author,
        price=book_in.price,
        genre=book_in.genre,
        stock=book_in.stock,
    )
    books_db[book_id] = new_book
    return new_book


@app.get(
    "/books",
    response_model=list[Book],
    status_code=status.HTTP_200_OK,
    tags=["Books"],
    summary="Get all books with optional filtering",
    description="Retrieve all books. Supports filtering by title, author, genre, and price range.",
)
async def get_books(
    title: Optional[str] = Query(
        None, description="Filter books by title (case-insensitive substring)"
    ),
    author: Optional[str] = Query(
        None, description="Filter books by author (case-insensitive substring)"
    ),
    genre: Optional[str] = Query(
        None, description="Filter books by genre (case-insensitive substring)"
    ),
    min_price: Optional[float] = Query(
        None, ge=0, description="Minimum price filter (inclusive)"
    ),
    max_price: Optional[float] = Query(
        None, ge=0, description="Maximum price filter (inclusive)"
    ),
) -> list[Book]:
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="min_price cannot be greater than max_price",
        )

    results: list[Book] = []
    for book in books_db.values():
        if title and title.strip().lower() not in book.title.lower():
            continue
        if author and author.strip().lower() not in book.author.lower():
            continue
        if genre and genre.strip().lower() not in book.genre.lower():
            continue
        if min_price is not None and book.price < min_price:
            continue
        if max_price is not None and book.price > max_price:
            continue
        results.append(book)

    return results


@app.get(
    "/books/{book_id}",
    response_model=Book,
    status_code=status.HTTP_200_OK,
    tags=["Books"],
    summary="Get a book by ID",
    description="Retrieve a single book by its unique identifier.",
)
async def get_book(
    book_id: int = Path(..., gt=0, description="The unique ID of the book to retrieve"),
) -> Book:
    if book_id not in books_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book with id {book_id} not found",
        )
    return books_db[book_id]


@app.put(
    "/books/{book_id}",
    response_model=Book,
    status_code=status.HTTP_200_OK,
    tags=["Books"],
    summary="Update a book by ID",
    description="Update an existing book's details. Only provided fields are updated.",
)
async def update_book(
    book_id: int = Path(..., gt=0, description="The unique ID of the book to update"),
    book_update: BookUpdate = ...,
) -> Book:
    if book_id not in books_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book with id {book_id} not found",
        )

    current_book = books_db[book_id]
    update_data = book_update.model_dump(exclude_unset=True)
    update_data.pop("id", None)

    current_dict = current_book.model_dump()
    current_dict.update(update_data)

    updated_book = Book(**current_dict)
    books_db[book_id] = updated_book
    return updated_book


@app.delete(
    "/books/{book_id}",
    status_code=status.HTTP_200_OK,
    tags=["Books"],
    summary="Delete a book by ID",
    description="Remove a book from the store by its unique identifier.",
)
async def delete_book(
    book_id: int = Path(..., gt=0, description="The unique ID of the book to delete"),
):
    if book_id not in books_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book with id {book_id} not found",
        )
    books_db.pop(book_id)
    return {"message": "Book deleted successfully", "id": book_id}

