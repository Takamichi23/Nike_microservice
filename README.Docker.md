# Docker Containerization Guide

This project is containerized using Docker for both the FastAPI backend and Django frontend.

## Architecture

- **FastAPI Backend**: Runs on port 8000
- **Django Frontend**: Runs on port 8001
- **Shared Database**: Both services share the same SQLite database (`db.sqlite3`)

## Quick Start

### Using Docker Compose (Recommended)

To run both services together:

```bash
docker-compose up -d
```

This will:
- Build both FastAPI and Django containers
- Start both services
- Set up networking between them
- Mount the shared database

### Access the Services

- **FastAPI API**: http://localhost:8000
- **Django Frontend**: http://localhost:8001
- **FastAPI Health Check**: http://localhost:8000/health

### Stop Services

```bash
docker-compose down
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f fastapi
docker-compose logs -f frontend
```

## Building Individual Services

### FastAPI Only

```bash
cd fastapi_app
docker-compose up -d
```

Or build manually:

```bash
docker build -f fastapi_app/Dockerfile -t nike-fastapi .
docker run -p 8000:8000 -v $(pwd)/db.sqlite3:/app/db.sqlite3:rw nike-fastapi
```

### Django Frontend Only

```bash
docker build -f Dockerfile.frontend -t nike-frontend .
docker run -p 8001:8001 \
  -v $(pwd)/db.sqlite3:/app/db.sqlite3:rw \
  -v $(pwd)/media:/app/media:rw \
  -e FASTAPI_BASE_URL=http://host.docker.internal:8000 \
  nike-frontend
```

## Development Mode

For development with hot-reload, uncomment the volume mounts in `docker-compose.yml`:

```yaml
volumes:
  - ./fastapi_app:/app/fastapi_app:ro  # Uncomment for development
  - .:/app:ro  # Uncomment for development
```

Then rebuild and restart:

```bash
docker-compose up -d --build
```

## Production Considerations

1. **Database**: Consider using PostgreSQL or MySQL instead of SQLite for production
2. **Static Files**: Ensure `collectstatic` runs before starting Django
3. **WSGI Server**: Replace `runserver` with `gunicorn` or `uwsgi` for production
4. **Environment Variables**: Use `.env` files or secrets management
5. **Security**: Update `ALLOWED_HOSTS` and `SECRET_KEY` in Django settings
6. **HTTPS**: Use a reverse proxy (nginx) with SSL certificates

## Troubleshooting

### Database Issues

If you encounter database permission errors:

```bash
# Fix permissions
sudo chmod 666 db.sqlite3
```

### Port Conflicts

If ports 8000 or 8001 are already in use, modify the port mappings in `docker-compose.yml`:

```yaml
ports:
  - "8002:8000"  # Change host port
```

### Rebuild Containers

```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## File Structure

```
.
├── docker-compose.yml          # Main orchestration file
├── Dockerfile.frontend         # Django frontend Dockerfile
├── .dockerignore              # Files to exclude from Docker build
├── requirements.txt           # Django dependencies
├── fastapi_app/
│   ├── Dockerfile            # FastAPI Dockerfile
│   ├── docker-compose.yml    # Standalone FastAPI compose
│   └── requirements.txt      # FastAPI dependencies
└── db.sqlite3                # Shared database (mounted as volume)
```

