"""FastAPI application for BookStore REST API with BackgroundTasks, Rate Limiting, and SQLAlchemy ORM."""

from contextlib import asynccontextmanager
from typing import Optional
import uuid

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    HTTPException,
    Path,
    Query,
    Request,
    status,
)
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

try:
    from app.auth import get_current_user, get_password_hash, require_admin, router as auth_router
    from app.database import AsyncSessionLocal, get_db, init_db
    from app.limiter import limiter
    from app.models import Book as BookModel, Note as NoteModel, User as UserModel
    from app.schemas import (
        Book,
        BookCreate,
        BookOrderRequest,
        BookOrderResponse,
        BookUpdate,
        EmailNotificationRequest,
        NoteCreate,
        NoteResponse,
        NoteWithUserResponse,
        NotificationTaskResponse,
        WebhookDispatchRequest,
    )
    from app.tasks import (
        dispatch_webhook,
        send_email_notification,
        task_execution_log,
    )
except ModuleNotFoundError:
    from auth import get_current_user, get_password_hash, require_admin, router as auth_router
    from database import AsyncSessionLocal, get_db, init_db
    from limiter import limiter
    from models import Book as BookModel, Note as NoteModel, User as UserModel
    from schemas import (
        Book,
        BookCreate,
        BookOrderRequest,
        BookOrderResponse,
        BookUpdate,
        EmailNotificationRequest,
        NoteCreate,
        NoteResponse,
        NoteWithUserResponse,
        NotificationTaskResponse,
        WebhookDispatchRequest,
    )
    from tasks import (
        dispatch_webhook,
        send_email_notification,
        task_execution_log,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager that initializes SQLite database tables on startup."""
    await init_db()
    # Seed default admin user if not already present
    async with AsyncSessionLocal() as db:
        stmt = select(UserModel).where(UserModel.username == "admin")
        result = await db.execute(stmt)
        if result.scalar_one_or_none() is None:
            default_admin = UserModel(
                username="admin",
                hashed_password=get_password_hash("admin123"),
                role="admin",
            )
            db.add(default_admin)
            await db.commit()
    yield


app = FastAPI(
    title="BookStore Microservice API",
    description=(
        "Production-ready asynchronous microservice for bookstore management featuring "
        "SQLAlchemy 2.0 ORM persistence with SQLite, FastAPI BackgroundTasks (async emails & webhooks), "
        "SlowAPI rate limiting, JWT authentication, and RBAC."
    ),
    version="4.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Configure Rate Limiting via SlowAPI
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Include Authentication & User Management router
app.include_router(auth_router)

# In-memory backwards compatibility alias
books_db: dict = {}


# ==========================================
# Root Endpoint
# ==========================================

@app.get(
    "/",
    tags=["Root"],
    summary="Root endpoint",
    description="Welcome message, health status, and API documentation links.",
)
async def root():
    return {
        "message": "Welcome to the BookStore Microservice with BackgroundTasks & Rate Limiting",
        "docs": "/docs",
        "openapi": "/openapi.json",
        "status": "healthy",
    }


# ==========================================
# BookStore Endpoints (Persistent with SQLite)
# ==========================================

@app.post(
    "/books",
    response_model=Book,
    status_code=status.HTTP_201_CREATED,
    tags=["Books"],
    summary="Create a new book (Protected: Authenticated Users)",
    description="Add a new book persisted to SQLite. Associates the book with the authenticated user.",
)
async def create_book(
    book_in: BookCreate,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BookModel:
    if book_in.id is not None:
        stmt = select(BookModel).where(BookModel.id == book_in.id)
        result = await db.execute(stmt)
        if result.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Book with id {book_in.id} already exists",
            )
        new_book = BookModel(
            id=book_in.id,
            title=book_in.title,
            author=book_in.author,
            price=book_in.price,
            genre=book_in.genre,
            stock=book_in.stock,
            user_id=current_user.id,
        )
    else:
        new_book = BookModel(
            title=book_in.title,
            author=book_in.author,
            price=book_in.price,
            genre=book_in.genre,
            stock=book_in.stock,
            user_id=current_user.id,
        )

    db.add(new_book)
    await db.commit()
    await db.refresh(new_book)
    return new_book


@app.get(
    "/books",
    response_model=list[Book],
    status_code=status.HTTP_200_OK,
    tags=["Books"],
    summary="Get all books (Protected: Authenticated Users)",
    description="Retrieve all books from SQLite. Supports query filtering by title, author, genre, and price range.",
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
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[BookModel]:
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="min_price cannot be greater than max_price",
        )

    stmt = select(BookModel)
    if title and title.strip():
        stmt = stmt.where(BookModel.title.ilike(f"%{title.strip()}%"))
    if author and author.strip():
        stmt = stmt.where(BookModel.author.ilike(f"%{author.strip()}%"))
    if genre and genre.strip():
        stmt = stmt.where(BookModel.genre.ilike(f"%{genre.strip()}%"))
    if min_price is not None:
        stmt = stmt.where(BookModel.price >= min_price)
    if max_price is not None:
        stmt = stmt.where(BookModel.price <= max_price)

    stmt = stmt.order_by(BookModel.id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@app.get(
    "/books/{book_id}",
    response_model=Book,
    status_code=status.HTTP_200_OK,
    tags=["Books"],
    summary="Get a book by ID (Protected: Authenticated Users)",
    description="Retrieve a single persistent book record by its unique identifier.",
)
async def get_book(
    book_id: int = Path(..., gt=0, description="The unique ID of the book to retrieve"),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BookModel:
    stmt = select(BookModel).where(BookModel.id == book_id)
    result = await db.execute(stmt)
    book = result.scalar_one_or_none()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book with id {book_id} not found",
        )
    return book


@app.put(
    "/books/{book_id}",
    response_model=Book,
    status_code=status.HTTP_200_OK,
    tags=["Books"],
    summary="Update a book by ID (Protected: Authenticated Users)",
    description="Update an existing book's details in SQLite. Preserves unset fields.",
)
async def update_book(
    book_id: int = Path(..., gt=0, description="The unique ID of the book to update"),
    book_update: BookUpdate = ...,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BookModel:
    stmt = select(BookModel).where(BookModel.id == book_id)
    result = await db.execute(stmt)
    book = result.scalar_one_or_none()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book with id {book_id} not found",
        )

    update_data = book_update.model_dump(exclude_unset=True)
    update_data.pop("id", None)

    for field, value in update_data.items():
        setattr(book, field, value)

    await db.commit()
    await db.refresh(book)
    return book


@app.delete(
    "/books/{book_id}",
    status_code=status.HTTP_200_OK,
    tags=["Books"],
    summary="Delete a book by ID (Protected: Admin Only)",
    description="Remove a book record from SQLite. Restricted to users with the 'admin' role.",
)
async def delete_book(
    book_id: int = Path(..., gt=0, description="The unique ID of the book to delete"),
    admin_user: UserModel = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(BookModel).where(BookModel.id == book_id)
    result = await db.execute(stmt)
    book = result.scalar_one_or_none()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book with id {book_id} not found",
        )

    await db.delete(book)
    await db.commit()
    return {"message": "Book deleted successfully", "id": book_id}


# ==========================================================
# Background Tasks: Orders & Async Notifications (Task 4)
# ==========================================================

@app.post(
    "/books/{book_id}/order",
    response_model=BookOrderResponse,
    status_code=status.HTTP_200_OK,
    tags=["Orders & Background Tasks"],
    summary="Order a book (Triggers Background Email & Webhook)",
    description="Orders a book, decrements stock, and queues asynchronous confirmation emails and webhooks in the background.",
)
async def order_book(
    background_tasks: BackgroundTasks,
    book_id: int = Path(..., gt=0, description="Book ID to purchase"),
    order_in: BookOrderRequest = ...,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BookOrderResponse:
    stmt = select(BookModel).where(BookModel.id == book_id)
    result = await db.execute(stmt)
    book = result.scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=404, detail=f"Book with id {book_id} not found")

    if book.stock < order_in.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient stock. Available: {book.stock}, requested: {order_in.quantity}",
        )

    # Decrement stock
    book.stock -= order_in.quantity
    await db.commit()
    await db.refresh(book)

    task_id = str(uuid.uuid4())
    total_price = round(book.price * order_in.quantity, 2)

    # Queue background email notification
    recipient_email = order_in.buyer_email or f"{current_user.username}@example.com"
    background_tasks.add_task(
        send_email_notification,
        recipient=recipient_email,
        subject=f"Order Confirmation: {book.title}",
        message=(
            f"Hello {current_user.username},\n\n"
            f"Your order for {order_in.quantity} copy/copies of '{book.title}' "
            f"has been confirmed for a total of ${total_price}.\n\nThank you!"
        ),
        task_id=task_id,
    )

    # Queue background webhook if configured
    if order_in.webhook_url:
        background_tasks.add_task(
            dispatch_webhook,
            url=order_in.webhook_url,
            event="book.ordered",
            payload={
                "book_id": book.id,
                "title": book.title,
                "quantity": order_in.quantity,
                "total_price": total_price,
                "buyer": current_user.username,
            },
            task_id=f"wh-{task_id}",
        )

    return BookOrderResponse(
        message="Order processed successfully; confirmation queued in background",
        book_id=book.id,
        quantity=order_in.quantity,
        total_price=total_price,
        remaining_stock=book.stock,
        background_task_id=task_id,
    )


@app.post(
    "/notifications/email",
    response_model=NotificationTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["Orders & Background Tasks"],
    summary="Dispatch async email notification in background",
    description="Queues an asynchronous email notification using FastAPI BackgroundTasks. Rate limited.",
)
@limiter.limit("20/minute")
async def trigger_email_notification(
    request: Request,
    background_tasks: BackgroundTasks,
    payload: EmailNotificationRequest,
    current_user: UserModel = Depends(get_current_user),
) -> NotificationTaskResponse:
    task_id = str(uuid.uuid4())
    background_tasks.add_task(
        send_email_notification,
        recipient=payload.recipient,
        subject=payload.subject,
        message=payload.message,
        task_id=task_id,
    )
    return NotificationTaskResponse(
        message="Email notification queued successfully in background",
        task_id=task_id,
        task_type="email",
        target=payload.recipient,
        status="queued",
    )


@app.post(
    "/notifications/webhook",
    response_model=NotificationTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["Orders & Background Tasks"],
    summary="Dispatch async webhook in background",
    description="Queues an asynchronous webhook HTTP dispatch using FastAPI BackgroundTasks. Rate limited.",
)
@limiter.limit("20/minute")
async def trigger_webhook_dispatch(
    request: Request,
    background_tasks: BackgroundTasks,
    payload: WebhookDispatchRequest,
    current_user: UserModel = Depends(get_current_user),
) -> NotificationTaskResponse:
    task_id = str(uuid.uuid4())
    background_tasks.add_task(
        dispatch_webhook,
        url=payload.url,
        event=payload.event,
        payload=payload.payload,
        task_id=task_id,
    )
    return NotificationTaskResponse(
        message="Webhook dispatch queued successfully in background",
        task_id=task_id,
        task_type="webhook",
        target=payload.url,
        status="queued",
    )


@app.get(
    "/notifications/tasks",
    tags=["Orders & Background Tasks"],
    summary="Get background task execution log",
    description="Retrieve audit log of recently executed background jobs.",
)
async def get_background_task_log(
    current_user: UserModel = Depends(get_current_user),
):
    return {"tasks": task_execution_log}


# ==========================================
# Relational Endpoints (Relational Joins)
# ==========================================

@app.get(
    "/users/{user_id}/books",
    response_model=list[Book],
    status_code=status.HTTP_200_OK,
    tags=["Relational"],
    summary="Get books by user ID (Relational Join)",
    description="Retrieve all books created by a specific user via foreign key relation.",
)
async def get_user_books(
    user_id: int = Path(..., gt=0, description="User ID"),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[BookModel]:
    stmt = select(BookModel).where(BookModel.user_id == user_id).order_by(BookModel.id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@app.post(
    "/notes",
    response_model=NoteResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Notes (Relational)"],
    summary="Create a note (Relational Model: Users -> Notes)",
    description="Create a note associated with the authenticated user via a foreign key.",
)
async def create_note(
    note_in: NoteCreate,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NoteModel:
    new_note = NoteModel(
        title=note_in.title,
        content=note_in.content,
        user_id=current_user.id,
    )
    db.add(new_note)
    await db.commit()
    await db.refresh(new_note)
    return new_note


@app.get(
    "/notes",
    response_model=list[NoteWithUserResponse],
    status_code=status.HTTP_200_OK,
    tags=["Notes (Relational)"],
    summary="Get notes with user relation (Relational Join)",
    description="Retrieve notes performing a relational join (selectinload) to include user data.",
)
async def get_notes(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[NoteModel]:
    stmt = select(NoteModel).options(selectinload(NoteModel.user))
    if current_user.role != "admin":
        stmt = stmt.where(NoteModel.user_id == current_user.id)
    stmt = stmt.order_by(NoteModel.id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@app.get(
    "/notes/{note_id}",
    response_model=NoteWithUserResponse,
    status_code=status.HTTP_200_OK,
    tags=["Notes (Relational)"],
    summary="Get note by ID with user relation",
    description="Retrieve a specific note with joined user details.",
)
async def get_note(
    note_id: int = Path(..., gt=0),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NoteModel:
    stmt = (
        select(NoteModel)
        .options(selectinload(NoteModel.user))
        .where(NoteModel.id == note_id)
    )
    if current_user.role != "admin":
        stmt = stmt.where(NoteModel.user_id == current_user.id)

    result = await db.execute(stmt)
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail=f"Note with id {note_id} not found")
    return note


@app.delete(
    "/notes/{note_id}",
    status_code=status.HTTP_200_OK,
    tags=["Notes (Relational)"],
    summary="Delete a note",
    description="Delete a note by ID.",
)
async def delete_note(
    note_id: int = Path(..., gt=0),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(NoteModel).where(NoteModel.id == note_id)
    if current_user.role != "admin":
        stmt = stmt.where(NoteModel.user_id == current_user.id)

    result = await db.execute(stmt)
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail=f"Note with id {note_id} not found")

    await db.delete(note)
    await db.commit()
    return {"message": "Note deleted successfully", "id": note_id}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
