# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Stage 1: build the frontend (Vite + React) static assets
# ---------------------------------------------------------------------------
FROM node:22-slim AS frontend-build

WORKDIR /app/frontend

# Install deps first for better layer caching.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# ---------------------------------------------------------------------------
# Stage 2: Python runtime serving the API and the built frontend
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

WORKDIR /app

# Install backend dependencies first for better layer caching.
# NOTE: requirements.txt pins bcrypt==4.0.1 deliberately (passlib 1.7.4 is
# incompatible with bcrypt>=4.1). Do not let pip/uv/anything upgrade it.
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy backend application code.
COPY backend/app ./backend/app

# Copy Alembic migration configuration and migration files.
COPY backend/alembic.ini ./backend/alembic.ini
COPY backend/migrations ./backend/migrations

# Copy the frontend's built static assets from stage 1 into a directory the
# backend serves via FastAPI's StaticFiles (no Nginx/domain/HTTPS yet).
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

WORKDIR /app/backend

# SQLite data directory (mounted as a volume in docker-compose.yml).
RUN mkdir -p /app/backend/data

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
