# Technology Stack

## Backend Framework

- **FastAPI** (0.110.0): Async web framework for REST API
- **Uvicorn**: ASGI server for running FastAPI
- **Python 3.x**: Primary programming language

## Database & Caching

- **PostgreSQL 15**: Primary relational database
- **SQLAlchemy 2.0**: ORM with async support (asyncpg driver)
- **Alembic**: Database migration management
- **Redis**: Task queue broker and caching layer

## Task Queue

- **Celery 5.3**: Distributed task queue for async operations
- **Redis**: Message broker for Celery workers

## Authentication & Security

- **python-jose**: JWT token generation and validation
- **passlib[bcrypt]**: Password hashing

## Document Processing

- **python-docx**: DOCX file parsing and manipulation
- **LibreOffice**: DOC to DOCX conversion (external dependency)
- **BeautifulSoup4 + lxml**: HTML/XML parsing

## External Integrations

- **OpenAI API**: AI semantic transformation (LLM)
- **imap-tools**: Email fetching via IMAP
- **httpx**: Async HTTP client for WordPress REST API
- **oss2**: Alibaba Cloud OSS SDK for image storage

## Containerization

- **Docker Compose**: Multi-container orchestration
- Services: PostgreSQL, Redis, Backend API, Celery Worker

## Common Commands

### Development

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop all services
docker-compose down
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

### Celery Worker

```bash
# Start worker (inside container)
celery -A app.tasks worker --loglevel=info

# Monitor tasks
celery -A app.tasks inspect active
```

### Testing

```bash
# Run tests (when test suite exists)
pytest

# Run with coverage
pytest --cov=app
```

## Environment Variables

Key environment variables (set in docker-compose.yml or .env):

- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `OPENAI_API_KEY`: OpenAI API key for LLM
- `OSS_ACCESS_KEY_ID`: Alibaba Cloud OSS access key
- `OSS_ACCESS_KEY_SECRET`: Alibaba Cloud OSS secret key
- `IMAP_HOST`, `IMAP_USER`, `IMAP_PASSWORD`: Email server credentials
- `JWT_SECRET_KEY`: Secret for JWT token signing

## Build System

The project uses Docker for containerization with multi-stage builds. Python dependencies are managed via `requirements.txt` and installed during Docker image build.
