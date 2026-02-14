# Project Structure

## Root Directory Layout

```
.
├── .kiro/                    # Kiro IDE configuration
│   ├── specs/               # Feature specifications
│   │   └── glory-ai-audit-system/
│   └── steering/            # AI assistant guidance documents
├── .snapshots/              # Code snapshots for AI interactions
├── backend/                 # Python backend application
│   └── requirements.txt     # Python dependencies
├── docker/                  # Docker configuration files (expected)
│   └── backend/
│       └── Dockerfile
└── docker-compose.yml       # Multi-container orchestration
```

## Backend Structure (Expected)

Based on the requirements and tech stack, the backend should follow this structure:

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Configuration management
│   ├── database.py          # Database connection and session
│   ├── models/              # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── submission.py    # Submission model
│   │   ├── draft.py         # Draft model
│   │   ├── user.py          # User model
│   │   └── wordpress_site.py
│   ├── schemas/             # Pydantic schemas for API
│   │   ├── __init__.py
│   │   ├── submission.py
│   │   ├── draft.py
│   │   └── auth.py
│   ├── api/                 # API route handlers
│   │   ├── __init__.py
│   │   ├── auth.py          # Authentication endpoints
│   │   ├── submissions.py   # Submission management
│   │   ├── drafts.py        # Draft management
│   │   ├── publish.py       # WordPress publishing
│   │   └── config.py        # System configuration
│   ├── services/            # Business logic layer
│   │   ├── __init__.py
│   │   ├── imap_fetcher.py  # Email fetching service
│   │   ├── ai_transformer.py # AI transformation service
│   │   ├── oss_service.py   # OSS image upload service
│   │   ├── wordpress_service.py # WordPress API client
│   │   └── document_processor.py # DOC/DOCX processing
│   ├── tasks/               # Celery async tasks
│   │   ├── __init__.py
│   │   ├── email_tasks.py   # Email fetching tasks
│   │   ├── transform_tasks.py # AI transformation tasks
│   │   └── cleanup_tasks.py # Data cleanup tasks
│   ├── utils/               # Utility functions
│   │   ├── __init__.py
│   │   ├── auth.py          # JWT utilities
│   │   └── diff.py          # Content diff utilities
│   └── migrations/          # Alembic migrations
│       └── versions/
└── requirements.txt
```

## Key Architectural Patterns

### Layered Architecture

1. **API Layer** (`api/`): FastAPI route handlers, request/response validation
2. **Service Layer** (`services/`): Business logic, external integrations
3. **Data Layer** (`models/`): SQLAlchemy ORM models, database operations
4. **Task Layer** (`tasks/`): Celery async tasks for long-running operations

### Async-First Design

- Use `async/await` for all I/O operations (database, HTTP, file operations)
- SQLAlchemy with `asyncpg` driver for async database access
- `httpx` for async HTTP requests to WordPress API

### Separation of Concerns

- **Models**: Database schema and relationships
- **Schemas**: API request/response validation (Pydantic)
- **Services**: Reusable business logic, external API clients
- **Tasks**: Background job definitions (Celery)

## Configuration Management

- Environment-based configuration using `pydantic-settings`
- Sensitive data (API keys, passwords) stored in environment variables
- Docker Compose manages service-level configuration

## Database Migrations

- Alembic manages schema migrations in `migrations/versions/`
- Auto-generate migrations from SQLAlchemy model changes
- Version-controlled migration scripts

## Naming Conventions

- **Files**: snake_case (e.g., `imap_fetcher.py`)
- **Classes**: PascalCase (e.g., `SubmissionModel`)
- **Functions/Variables**: snake_case (e.g., `fetch_emails`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `MAX_RETRY_COUNT`)
- **API Endpoints**: kebab-case in URLs (e.g., `/api/v1/submissions`)
